"""Moderated organization logos. All identities come from the Zhihu OAuth session."""
import hmac
import io
import re
import sqlite3
import time
from contextlib import closing
from email import policy
from email.parser import BytesParser
from html import escape

from PIL import Image, UnidentifiedImageError

DESK = "/auth/zhihu/sponsors"
PUBLIC = "/sponsors/logo/"
ORIGIN = "https://www.goldbach.tech"
LIMIT = 192 * 1024


def setup(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS site_admins(subject TEXT PRIMARY KEY, slot TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS sponsor_logos(
            id INTEGER PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, png BLOB,
            state TEXT NOT NULL DEFAULT 'pending', submitted INTEGER NOT NULL,
            reviewer TEXT, reviewed INTEGER);
        CREATE INDEX IF NOT EXISTS sponsor_state ON sponsor_logos(state,id);
        CREATE INDEX IF NOT EXISTS sponsor_owner ON sponsor_logos(owner,submitted);
    """)


def bootstrap(db, profile, registered_profile, uid=None):
    match = profile["subject"] == uid if uid else registered_profile and profile["profile_url"] == registered_profile
    if match:
        db.execute("INSERT OR IGNORE INTO site_admins VALUES (?, 'initial')", (profile["subject"],))


def upload_fields(content_type, raw):
    msg = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii") + b"\r\n\r\n" + raw)
    fields = {}
    for part in msg.iter_parts():
        key = part.get_param("name", header="content-disposition")
        if key not in ("name", "csrf", "logo") or key in fields or part.is_multipart():
            raise ValueError("invalid form")
        value = part.get_payload(decode=True)
        fields[key] = value if key == "logo" else value.decode("utf-8")
    if set(fields) != {"name", "csrf", "logo"}:
        raise ValueError("incomplete form")
    return fields


def logo_png(raw):
    if not isinstance(raw,bytes) or len(raw)>180*1024:
        raise ValueError("image size")
    with Image.open(io.BytesIO(raw), formats=("PNG", "JPEG", "WEBP")) as im:
        if max(im.size) > 2048 or im.width * im.height > 2_000_000 or getattr(im, "n_frames", 1) != 1:
            raise ValueError("image dimensions")
        im.thumbnail((480, 240))
        clean = im.convert("RGBA")
        clean.info.clear()
        out = io.BytesIO()
        clean.save(out, format="PNG")
        return out.getvalue()


def wall(path, lang, prefix):
    with closing(sqlite3.connect(path)) as db:
        rows = db.execute("SELECT id,name FROM sponsor_logos WHERE state='approved' ORDER BY id").fetchall()
    cards = "".join(f'<figure><img loading="lazy" src="{prefix}sponsors/logo/{i}.png" alt=""><figcaption>{escape(n)}</figcaption></figure>' for i,n in rows)
    zh = lang == "zh"
    return (f'<section class="shell sponsor-wall"><h2>{"赞助单位" if zh else "Sponsors"}</h2>'
            f'<div class="sponsor-grid">{cards}</div>'
            f'<a class="text-link" href="{ORIGIN}{DESK}?lang={lang}">'
            + ("提交单位 Logo" if zh else "Submit an organization logo") + ' ↗</a></section>')


def public_logo(path, ident):
    with closing(sqlite3.connect(path)) as db:
        row = db.execute("SELECT png FROM sponsor_logos WHERE id=? AND state='approved'", (ident,)).fetchone()
    return row[0] if row else None


def handle(method, path, params, headers, db, row, lang, page, redirect):
    def tr(zh, en):
        return en if lang == "en" else zh
    title = tr("赞助单位 Logo", "Sponsor logos")
    msg = lambda code, text: page(code, title, f'<p>{text}</p><a href="{DESK}?lang={lang}">{tr("返回","Back")}</a>', lang)
    uid = row["subject"]
    csrf = f'<input type="hidden" name="csrf" value="{row["csrf"]}">'
    if not uid:
        if method == "GET" and path == DESK:
            dest = "home" if params.get("entry")=="home" else "sponsors"
            return page(200, title, f'<p>{tr("使用知乎账号投稿或登录审核。","Sign in with Zhihu to submit or review logos.")}</p>'
                        f'<form action="/auth/zhihu/start" method="post">{csrf}<input type="hidden" name="next" value="{dest}">'
                        f'<button>{tr("使用知乎登录","Sign in with Zhihu")}</button></form>', lang)
        return msg(403, tr("请先登录知乎。","Please sign in with Zhihu."))
    admin = db.execute("SELECT 1 FROM site_admins WHERE subject=?", (uid,)).fetchone()
    if method == "POST":
        if headers.get("Origin") != ORIGIN or not hmac.compare_digest(str(params.get("csrf","")).encode(),row["csrf"].encode()):
            return msg(403, tr("请刷新后重试。","Refresh and try again."))
        if path == DESK+"/logout":
            db.execute("DELETE FROM sessions WHERE sid=?", (row["sid"],))
            return redirect("/?lang="+lang)
        if path == DESK+"/upload":
            name = params.get("name","").strip()
            if not 1 <= len(name) <= 80:
                return msg(400, tr("单位名须为 1–80 字。","Use a name of 1–80 characters."))
            try:
                png = logo_png(params.get("logo",b""))
            except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, TypeError):
                return msg(400, tr("请上传符合大小要求的静态图片。","Choose a static image within the size limits."))
            now = int(time.time())
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT count(*) FROM sponsor_logos WHERE owner=? AND (state='pending' OR submitted>?)",(uid,now-86400)).fetchone()[0]
            if count >= 3:
                return msg(429, tr("待审或近一天的投稿已达三份。","Limit of three pending or recent submissions reached."))
            db.execute("INSERT INTO sponsor_logos(owner,name,png,submitted) VALUES(?,?,?,?)",(uid,name,png,now))
        elif path == DESK+"/review":
            if not admin:
                return msg(403, tr("需要管理员权限。","Administrator access required."))
            decision = params.get("decision")
            if decision not in ("approved","rejected","withdrawn"):
                return msg(400, tr("无效操作。","Invalid action."))
            expected = "approved" if decision == "withdrawn" else "pending"
            changed = db.execute("""UPDATE sponsor_logos SET state=?,reviewer=?,reviewed=?,
                png=CASE WHEN ?='approved' THEN png ELSE NULL END WHERE id=? AND state=?""",
                (decision,uid,int(time.time()),decision,params.get("id"),expected)).rowcount
            if not changed:
                return msg(409, tr("状态已变更，请刷新。","State changed. Refresh the page."))
        else:
            return msg(404, "404")
        return redirect(DESK)
    preview = re.fullmatch(DESK+r"/preview/([1-9][0-9]{0,15})",path)
    if preview:
        image = db.execute("SELECT png FROM sponsor_logos WHERE id=? AND (owner=? OR ?) AND png IS NOT NULL",
                           (preview[1],uid,bool(admin))).fetchone()
        return (200,{"Content-Type":"image/png"},image[0]) if image else msg(404,"404")
    if path != DESK:
        return msg(404, "404")
    body = (f'<form method="post" action="{DESK}/upload" enctype="multipart/form-data">{csrf}'
            f'<label>{tr("单位名称","Organization")} <input name="name" maxlength="80" required></label>'
            '<label>Logo <input type="file" name="logo" accept="image/png,image/jpeg,image/webp" required></label>'
            f'<p>{tr("PNG、JPEG 或 WebP，最大 180 KiB、200 万像素，单边最多 2048 像素。仅上传获授权的标识，审核通过后公开。","PNG, JPEG or WebP, up to 180 KiB, 2 MP and 2048 px per side. Submit authorized artwork for public display after review.")}</p>'
            f'<button>{tr("提交审核","Submit for review")}</button></form>')
    labels = {"pending":tr("待审核","Pending"),"approved":tr("已展示","Approved"),"rejected":tr("已拒绝","Rejected"),"withdrawn":tr("已撤下","Withdrawn")}
    body += '<h2>'+ (tr("管理员审核","Administrator review") if admin else tr("我的投稿","My submissions"))+'</h2>'
    for item in db.execute("SELECT id,name,state FROM sponsor_logos WHERE owner=? OR ? ORDER BY (state='pending') DESC,id DESC",(uid,bool(admin))):
        i,name,state = item
        body += f'<article><strong>{escape(name)}</strong> · {labels[state]}'
        if state in ("pending","approved"):
            body += f'<p><img src="{DESK}/preview/{i}" alt="" style="max-width:100%;max-height:90px"></p>'
            if admin:
                buttons = ("approved","rejected") if state=="pending" else ("withdrawn",)
                actions = {"approved":tr("通过","Approve"),"rejected":tr("拒绝","Reject"),"withdrawn":tr("撤下","Withdraw")}
                body += f'<form method="post" action="{DESK}/review">{csrf}<input type="hidden" name="id" value="{i}">'+''.join(f'<button name="decision" value="{v}">{actions[v]}</button>' for v in buttons)+'</form>'
        body += '</article>'
    account = (f'<p>{tr("知乎账号","Zhihu account")} · {escape(row["subject"])} · '
               f'<a href="/auth/zhihu?lang={lang}">{tr("贡献榜署名","Leaderboard attribution")}</a></p>')
    return page(200,tr("设置","Settings"),account+body+f'<a href="/?lang={lang}">{tr("返回研究台","Research desk")}</a>'
                f'<form method="post" action="{DESK}/logout">{csrf}<button>{tr("退出登录","Sign out")}</button></form>',lang)
