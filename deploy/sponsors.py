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
STYLE = "/sponsor-settings.css"
PUBLIC = "/sponsors/logo/"
ORIGIN = "https://www.goldbach.tech"
FILE_LIMIT = 4 * 1024 * 1024
LIMIT = FILE_LIMIT + 16 * 1024


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
    if not isinstance(raw, bytes) or len(raw) > FILE_LIMIT:
        raise ValueError("image size")
    with Image.open(io.BytesIO(raw), formats=("PNG", "JPEG", "WEBP")) as im:
        if max(im.size) > 4096 or im.width * im.height > 8_000_000 or getattr(im, "n_frames", 1) != 1:
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


def settings_page(status, lang, title, content):
    back = "返回研究台" if lang == "zh" else "Research desk"
    html = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {back}</title><link rel="stylesheet" href="{STYLE}">
<link rel="icon" href="/goldbach-icon.svg"></head><body>
<header><div class="shell masthead"><a href="/?lang={lang}">
<img src="/goldbach-icon.svg" width="40" height="40" alt=""><span>{back}</span></a></div></header>
<main class="shell"><h1>{title}</h1>{content}</main></body></html>"""
    return status, {"Content-Type": "text/html; charset=utf-8"}, html.encode()


def upload_error(lang, busy=False):
    zh = lang == "zh"
    title = ("上传繁忙" if zh else "Upload busy") if busy else ("Logo 文件过大" if zh else "Logo file is too large")
    hint = ("请稍后重试。" if zh else "Try again shortly.") if busy else (
        "请选择不超过 4 MiB 的 PNG、JPEG 或 WebP 图片。" if zh else "Choose a PNG, JPEG or WebP file up to 4 MiB.")
    back = "返回投稿" if zh else "Back to submission"
    return settings_page(503 if busy else 413, lang, title,
                         f'<section class="card"><p>{hint}</p><a href="{DESK}?lang={lang}">{back}</a></section>')


def handle(method, path, params, headers, db, row, lang, redirect):
    def tr(zh, en):
        return en if lang == "en" else zh
    title = tr("赞助单位 Logo", "Sponsor logos")
    def msg(code, text):
        return settings_page(code, lang, title,
                             f'<section class="card"><p>{text}</p><a href="{DESK}?lang={lang}">{tr("返回设置","Back to settings")}</a></section>')
    uid = row["subject"]
    csrf = f'<input type="hidden" name="csrf" value="{row["csrf"]}">'
    if not uid:
        if method == "GET" and path == DESK:
            dest = "home" if params.get("entry")=="home" else "sponsors"
            return settings_page(200, lang, title, f'<section class="card signin"><p>{tr("使用知乎账号投稿或登录审核。","Sign in with Zhihu to submit or review logos.")}</p>'
                        f'<form action="/auth/zhihu/start" method="post">{csrf}<input type="hidden" name="next" value="{dest}">'
                        f'<button class="primary">{tr("使用知乎登录","Sign in with Zhihu")}</button></form></section>')
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
            if len(params.get("logo", b"")) > FILE_LIMIT:
                return upload_error(lang)
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
    upload = (f'<section class="card upload"><h2>{tr("提交单位 Logo","Submit a logo")}</h2>'
            f'<form method="post" action="{DESK}/upload?lang={lang}" enctype="multipart/form-data">{csrf}'
            f'<label>{tr("单位名称","Organization")} <input name="name" maxlength="80" required></label>'
            '<label>Logo <input type="file" name="logo" accept="image/png,image/jpeg,image/webp" required></label>'
            f'<p class="hint">{tr("PNG、JPEG 或 WebP，最大 4 MiB、800 万像素，单边最多 4096 像素。仅上传获授权的标识，审核通过后公开。","PNG, JPEG or WebP, up to 4 MiB, 8 MP and 4096 px per side. Submit authorized artwork for public display after review.")}</p>'
            f'<button class="primary">{tr("提交审核","Submit for review")}</button></form></section>')
    labels = {"pending":tr("待审核","Pending"),"approved":tr("已展示","Approved"),"rejected":tr("已拒绝","Rejected"),"withdrawn":tr("已撤下","Withdrawn")}
    items = db.execute("SELECT id,name,state FROM sponsor_logos WHERE owner=? OR ? ORDER BY (state='pending') DESC,id DESC",
                       (uid,bool(admin))).fetchall()
    selected = params.get("view")
    filters = {"all": tr("全部","All"), **labels}
    if selected not in filters:
        selected = "all"
    counts = {key: 0 for key in labels}
    for _, _, state in items:
        counts[state] += 1
    counts["all"] = len(items)
    tabs = "".join(f'<a href="{DESK}?view={key}"{(" aria-current=page" if selected == key else "")}>'
                   f'{label} <span>{counts[key]}</span></a>' for key, label in filters.items())
    heading = tr("管理员审核","Administrator review") if admin else tr("我的投稿","My submissions")
    queue = [f'<section class="card queue"><h2>{heading}</h2><nav class="filters" aria-label="{heading}">{tabs}</nav>']
    if not counts[selected]:
        queue.append(f'<p class="empty">{tr("暂无符合条件的投稿。","No submissions in this view.")}</p>')
    actions = {"approved":tr("通过","Approve"),"rejected":tr("拒绝","Reject"),"withdrawn":tr("撤下","Withdraw")}
    for i, name, state in items:
        if selected not in ("all", state):
            continue
        queue.append('<article class="submission">')
        if state in ("pending","approved"):
            queue.append(f'<div class="preview"><img loading="lazy" src="{DESK}/preview/{i}" alt=""></div>')
        queue.append(f'<div class="submission-info"><strong>{escape(name)}</strong>'
                     f'<span class="status {state}">{labels[state]}</span></div>')
        if admin and state in ("pending","approved"):
            buttons = ("approved","rejected") if state == "pending" else ("withdrawn",)
            queue.append(f'<form class="review" method="post" action="{DESK}/review">{csrf}'
                         f'<input type="hidden" name="id" value="{i}">')
            for value in buttons:
                style = "primary" if value == "approved" else "danger"
                queue.append(f'<button class="{style}" name="decision" value="{value}">{actions[value]}</button>')
            queue.append('</form>')
        queue.append('</article>')
    queue.append('</section>')
    account = (f'<section class="card account"><h2>{tr("知乎账号","Zhihu account")}</h2>'
               f'<p class="hint">UID {escape(row["subject"])}</p>'
               f'<a href="/auth/zhihu?lang={lang}">{tr("贡献榜署名","Leaderboard attribution")}</a>'
               f'<form method="post" action="{DESK}/logout">{csrf}<button>{tr("退出登录","Sign out")}</button></form></section>')
    return settings_page(200, lang, tr("设置","Settings"),
                         '<div class="layout">'+''.join(queue)+'<aside>'+upload+account+'</aside></div>')
