import hashlib
import hmac
import ipaddress
import json
import os
import re
import sqlite3
import ssl
import time
from contextlib import closing
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore
from urllib.parse import parse_qs, urlsplit

from desk import Desk, QUEUE_BATCH
from landau import BASELINE, exponent_record
from zhihu_oauth import BASE as ZHIHU_PATH, ZhihuOAuth

ROOT = Path(__file__).resolve().parent
CREDS = Path(os.environ["CREDENTIALS_DIRECTORY"])
SECRET = (CREDS / "webhook").read_bytes().strip()
DB = Path(os.environ["STATE_DIRECTORY"]) / "verdicts.sqlite3"
oauth_credential = CREDS / "zhihu-oauth"
ZHIHU = ZhihuOAuth(DB.with_name("contributor-links.sqlite3"), json.loads(oauth_credential.read_bytes())
                   if oauth_credential.is_file() else None)
GAPS = json.loads((ROOT / "gaps.json").read_text(encoding="utf-8"))["gaps"]
DESK = Desk(DB, GAPS, SECRET)
PROBLEM_FILE = ROOT / "problems.json"
PROBLEMS = json.loads(PROBLEM_FILE.read_text(encoding="utf-8")) if PROBLEM_FILE.exists() else {}
PUBLIC_SITE = "https://www.movan.tech/goldbach/"
problem_ids = set(gap["id"] for gap in GAPS)
for slug, problem in PROBLEMS.items():
    if slug in {"goldbach", DB.stem} or not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", slug):
        raise ValueError(f"Invalid problem slug: {slug}")
    for gap in problem["gaps"]:
        if gap["id"] in problem_ids or not gap["id"].startswith(f"L-{slug}-"):
            raise ValueError(f"Invalid or duplicate task: {gap['id']}")
        problem_ids.add(gap["id"])
DESKS = {"goldbach": DESK, **{
    slug: Desk(DB.with_name(slug + ".sqlite3"), problem["gaps"], SECRET)
    for slug, problem in PROBLEMS.items()
}}
GAP_DESKS = {
    gap_id: slug for slug, desk in DESKS.items() for gap_id in desk.gaps
}

ASSETS = {
    "/goldbach-icon.svg": "image/svg+xml",
    "/site.css": "text/css",
    "/site.js": "text/javascript",
    "/join.txt": "text/plain",
    "/join-zh.txt": "text/plain",
}


def research_status(desk=DESK):
    db = desk.db_path
    results = []
    latest = {}
    attempts = 0
    extra = {}
    if db.exists():
        with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
            conn.execute("BEGIN")
            if desk is DESKS.get("quadratic-primes"):
                extra["lpf_record"] = exponent_record(desk, conn)
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='verdicts'").fetchone():
                results = [json.loads(body) for (body,) in conn.execute(
                    "SELECT body FROM verdicts ORDER BY run_id DESC, attempt DESC LIMIT 12"
                )]
                rows = conn.execute("""
                    WITH runs AS (
                        SELECT body, run_id, attempt,
                               json_extract(CAST(body AS TEXT), '$.lemma_id') AS lemma,
                               json_extract(CAST(body AS TEXT), '$.verdict') AS verdict
                        FROM verdicts
                    ), ranked AS (
                        SELECT body, lemma,
                               ROW_NUMBER() OVER (
                                   PARTITION BY lemma ORDER BY run_id DESC, attempt DESC
                               ) AS position,
                               MAX(verdict = 'ACCEPTED') OVER (PARTITION BY lemma) AS proved,
                               COUNT(*) OVER (PARTITION BY lemma) AS attempts
                        FROM runs
                    )
                    SELECT lemma, body, proved, attempts FROM ranked WHERE position = 1
                """)
                for lemma, body, proved, count in rows:
                    latest[lemma] = (json.loads(body), bool(proved))
                    attempts += count

    gaps = []
    for gap in desk.gaps.values():
        result, proved = latest.get(gap["id"], (None, False))
        gaps.append({**gap, "latest": result, "proved": proved})
    accepted = sum(gap["proved"] for gap in gaps)
    desk_status = desk.public_status()
    rankings = desk_status["rankings"]
    rows = rankings["all_time"] + rankings["hour"]
    profiles = ZHIHU.public_profiles(sorted({row["handle"].lower() for row in rows}))
    for row in rows:
        profile = profiles.get(row["handle"].lower())
        if profile:
            row["zhihu"] = profile
    return {
        **extra,
        "gaps": gaps,
        "results": results,
        "desk": desk_status,
        "counts": {
            "published": len(gaps),
            "accepted": accepted,
            "open": len(gaps) - accepted,
            "attempts": attempts,
        },
    }

def problem_page(page, slug, lang):
    data = PROBLEMS[slug]
    title, question, description = (escape(data[key][lang]) for key in ("title", "question", "summary"))
    zh = lang == "zh"
    translations = {
        "map": "研究地图" if zh else "Research map",
        "target": "研究起点" if zh else "Starting point",
        "road": "研究路线" if zh else "Research roadmap",
        "foundation": "基础引理" if zh else "Foundations",
        "correlation": "证明工具" if zh else "Proof techniques",
    }
    if slug == "quadratic-primes":
        translations["target"] = "大素因子指数" if zh else "Large prime factor exponent"
    page = page.replace('<body id="top">', f'<body id="top" data-problem="{slug}">')
    page = re.sub(r'<title>[^<]*</title>', f'<title>{title}</title>', page, count=1)
    page = re.sub(r'<meta (?:name|property)="(?:description|og:[^"]+|twitter:[^"]+)"[^>]*>\n?', '', page)
    page = re.sub(r'(<a href="#top" class="brand">.*?</span>)[^<]+', lambda m: m[1] + title, page, count=1)
    page = page.replace('aria-hidden="true">p + q ?</span>', f'aria-hidden="true">{escape(data["formula"])}</span>', 1)
    page = page.replace('href="problems/?', 'href="../?').replace('href="site.css"', 'href="../../site.css"').replace(
        'src="site.js"', 'src="../../site.js"')
    page = page.replace('href="goldbach-icon.svg"', 'href="../../goldbach-icon.svg"')
    page = page.replace('href="auth/zhihu?', 'href="../../auth/zhihu?')
    page = re.sub(r'(<h1 id="page-title">).*?(</h1>)', lambda m: m[1] + title + m[2], page)
    page = re.sub(r'(<p class="hero-question">).*?(</p>)', lambda m: m[1] + question + m[2], page)
    page = re.sub(r'(<p class="hero-description">).*?(</p>)', lambda m: m[1] + description + m[2], page)
    page = page.replace("强猜想 · 尚未解决", "开放研究问题").replace("Strong conjecture · Open", "Open research problem")
    page = re.sub(r'(<h2 id="target-title">).*?(</h2>)',
                  lambda m: m[1] + translations["target"] + m[2], page)
    formula = escape(data["formula"])
    figure = f'<div class="target-figure topic-formula">{formula}</div>'
    if slug == "quadratic-primes":
        current = "当前研究指数" if zh else "Current research exponent"
        target = "目标指数" if zh else "Target exponent"
        condition = ("对无穷多个 n，存在整除 n² + 1 的素数 p，且 p > nᵅ。若能证明 α = 2，则 p 只能等于 n² + 1。" if zh else
                     "For infinitely many n, a prime p divides n² + 1 with p > nᵅ. At α = 2 this forces p = n² + 1.")
        source = ("外部基线证书" if zh else "External baseline certificate") + f' · {BASELINE["exponent"]}'
        status_link = "查看实时数据" if zh else "View live data"
        figure = (
            '<div class="lpf-record" id="lpf-record">'
            f'<dl class="lpf-values"><div><dt>{current} α</dt><dd id="lpf-current">—</dd></div>'
            f'<div><dt>{target}</dt><dd id="lpf-target">2</dd></div></dl>'
            '<p class="lpf-evidence" id="lpf-kind"></p><p id="lpf-verified"></p>'
            f'<p class="lpf-condition">{condition}</p>'
            f'<a href="{escape(BASELINE["source_url"])}">{source}</a>'
            f'<noscript> · <a href="api/status">{status_link}</a></noscript>'
            '<p id="lpf-notice" role="status"></p></div>'
        )
    page = re.sub(r'<div class="target-figure".*?<div class="target-progress">',
                  lambda _: figure + '<div class="target-progress">', page, count=1, flags=re.S)
    page = re.sub(r'(<h2 id="lemma-title">).*?(</h2>)', lambda m: m[1] + title + ' · ' + translations["map"] + m[2], page)
    page = re.sub(r'<aside class="method-note">.*?</aside>',
                  f'<aside class="method-note"><h2>{translations["road"]}</h2><p>{description}</p></aside>', page, count=1, flags=re.S)
    def program_card(match):
        key = match[2]
        if key not in translations:
            return ""
        text = re.sub(r'(<strong class="program-name">).*?(</strong>)',
                      lambda m: m[1] + translations[key] + m[2], match[0])
        return re.sub(r'<span class="program-description">.*?</span>', '', text)
    page = re.sub(r'<button type="button" class="map-program-button" (data-program="([^"]+)").*?</button>',
                  program_card, page, flags=re.S)
    stages = "".join(
        f"<li><h3>{escape(heading)}</h3><p>{escape(body)}</p></li>"
        for heading, body in (step[lang] for step in data.get("roadmap", []))
    )
    page = re.sub(r'<section class="section road-section" id="roadmap".*?</section>',
                  lambda _: f'<section class="section road-section" id="roadmap"><div class="section-heading"><div>'
                  f'<h2>{translations["road"]}</h2></div></div><ol class="roadmap topic-roadmap">{stages}</ol></section>',
                  page, count=1, flags=re.S)
    url = PUBLIC_SITE + "problems/" + slug + "/join" + ("-zh" if zh else "") + ".txt"
    prompt = (f"阅读 {url}，按说明领取一条任务，提交 Lean 证明并跟踪核验。" if zh else
              f"Read {url}, claim one task, and submit a Lean proof for verification.")
    page = re.sub(r'(<p id="agent-prompt"[^>]*>).*?(</p>)', lambda m: m[1] + escape(prompt) + m[2], page)
    return page


def problem_card(slug, data, lang):
    zh = lang == "zh"
    try:
        verified, published, available = DESKS[slug].progress()
    except sqlite3.Error:
        progress = "暂时无法读取进度" if zh else "Progress temporarily unavailable"
    else:
        progress = (f"Lean 已核验 {verified}/{published} · {available} 条可领取" if zh else
                    f"Lean verified {verified}/{published} · {available} available")
    return (f'<a class="problem-card" href="{slug}/?lang={lang}"><span class="problem-formula">{escape(data["formula"])}</span>'
            f'<h2>{escape(data["title"][lang])}</h2><p>{escape(data["question"][lang])}</p>'
            f'<p class="problem-progress">{progress}</p></a>')


def directory_page(lang):
    zh = lang == "zh"
    heading = "更多研究问题" if zh else "Research problems"
    back = "返回强哥德巴赫猜想" if zh else "Back to Strong Goldbach"
    intro = ("选择一道题，查看其研究地图、开放引理和核验证据。" if zh else
             "Select a problem to explore its research map, open lemmas and verification record.")
    cards = "\n".join(problem_card(slug, data, lang) for slug, data in PROBLEMS.items())
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{heading} · Goldbach Research</title><link rel="icon" type="image/svg+xml" sizes="any" href="../goldbach-icon.svg"><link rel="stylesheet" href="../site.css"></head>
<body><header class="masthead"><div class="shell masthead-inner"><a class="brand" href="../?lang={lang}">{back}</a>
<a class="locale" href="?lang={'en' if zh else 'zh'}">{'English' if zh else '简体中文'}</a></div></header>
<main class="shell problem-directory"><h1>{heading}</h1><p>{intro}</p><div class="problem-list">{cards}</div></main></body></html>"""


def queue_pending(raw_body, headers):
    if not DESK.signed(headers.get("X-Goldbach-Signature", ""), raw_body):
        return 401, {"error": "invalid_signature"}
    now = int(time.time())
    desks = tuple(DESKS.values())
    quota = max(1, QUEUE_BATCH // len(desks))
    rows = []
    for desk in desks:
        if len(rows) >= QUEUE_BATCH:
            break
        rows.extend(desk.pending(now, min(quota, QUEUE_BATCH - len(rows)))[1]["pending"])
    for desk in desks:
        if len(rows) >= QUEUE_BATCH:
            break
        rows.extend(desk.pending(now, QUEUE_BATCH - len(rows))[1]["pending"])
    return 200, {"pending": rows}


def china_networks():
    for line in (ROOT / "china-apnic.txt").read_text(encoding="utf-8").splitlines():
        fields = line.split("|")
        if len(fields) < 7 or fields[1] != "CN" or fields[6] not in {"allocated", "assigned"}:
            continue
        _, _, kind, start, size, *_ = fields
        if kind == "ipv4":
            first = ipaddress.IPv4Address(start)
            yield from ipaddress.summarize_address_range(first, first + int(size) - 1)
        if kind == "ipv6":
            yield ipaddress.IPv6Network(f"{start}/{size}")

NETWORKS = tuple(china_networks())

class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        if getattr(self, "path", "").partition("?")[0].startswith(ZHIHU_PATH):
            self.log_message("Zhihu authorization request %s", code)
        else:
            super().log_request(code, size)

    def zhihu_request(self, path, query=""):
        if self.command == "HEAD":
            return self.reply(405, b'{}')
        try:
            if self.command == "POST":
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192 or self.headers.get_content_type() != "application/x-www-form-urlencoded":
                    return self.reply(400, b'{}')
                self.connection.settimeout(8)
                query = self.rfile.read(size).decode("utf-8")
            if len(query) > 12000:
                return self.reply(400, b'{}')
            fields = parse_qs(query, keep_blank_values=True, max_num_fields=12)
            if any(len(vals) != 1 for vals in fields.values()):
                return self.reply(400, b'{}')
            status, headers, body = ZHIHU.handle(self.command, path, {k: v[0] for k, v in fields.items()}, self.headers)
        except (ValueError, OSError, sqlite3.Error):
            return self.reply(400, b'{}')
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://openapi.zhihu.com https://www.zhihu.com; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def reply(self, status, body, content_type="application/json", language=None):
        self.send_response(status)
        if content_type == "application/json" or content_type.startswith("text/"):
            content_type += "; charset=utf-8"
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        if language:
            self.send_header("Content-Language", language)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def client_ip(self):
        peer = ipaddress.ip_address(self.client_address[0])
        peer = getattr(peer, "ipv4_mapped", None) or peer
        if peer.is_loopback:
            forwarded = self.headers.get("X-Goldbach-Client-IP")
            if forwarded:
                try:
                    return ipaddress.ip_address(forwarded)
                except ValueError:
                    pass
        return peer

    def language(self, url):
        lang = parse_qs(url.query).get("lang", [""])[0]
        if lang in {"zh", "en"}:
            return lang
        return "zh" if any(self.client_ip() in net for net in NETWORKS) else "en"

    @staticmethod
    def scope(path):
        match = re.fullmatch(r"/problems/([a-z-]+)(/.*)", path)
        if match:
            return DESKS.get(match[1]) if match[1] in PROBLEMS else None, match[2], match[1]
        return DESK, path, "goldbach"

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == ZHIHU_PATH or url.path.startswith(ZHIHU_PATH + "/"):
            return self.zhihu_request(url.path, url.query)
        if url.path == "/problems" or url.path.removeprefix("/problems/") in PROBLEMS:
            self.send_response(308)
            suffix = "?" + url.query if url.query else ""
            self.send_header("Location", url.path.rsplit("/", 1)[-1] + "/" + suffix)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if url.path == "/problems/":
            lang = self.language(url)
            return self.reply(200, directory_page(lang).encode(), "text/html", lang)
        desk, path, slug = self.scope(url.path)
        if desk is None:
            return self.reply(404, b'{}')
        if path == "/health":
            return self.reply(200, b'{"status":"ok"}')
        if path == "/api/status":
            try:
                body = json.dumps(research_status(desk), ensure_ascii=False, separators=(",", ":")).encode()
            except sqlite3.Error as error:
                self.log_error("Unable to read verdicts: %s", error)
                return self.reply(503, b'{"error":"verdicts unavailable"}')
            return self.reply(200, body)
        if path in ASSETS:
            asset = ROOT / path[1:]
            if not asset.is_file():
                return self.reply(404, b'{}')
            content = asset.read_bytes()
            if slug != "goldbach" and path in {"/join.txt", "/join-zh.txt"}:
                lang = "zh" if path.endswith("-zh.txt") else "en"
                title = PROBLEMS[slug]["title"][lang]
                introduction = (f"请使用自己的 GitHub 账号，领取并提交一条「{title}」的 Lean 4 引理。"
                                "只有通过权威 Lean 核验的引理才会记入研究台。" if lang == "zh" else
                                f"Use your GitHub account to claim and submit one Lean 4 lemma for {title}. "
                                "The desk credits lemmas that pass authoritative Lean verification.")
                if slug == "quadratic-primes":
                    introduction += (
                        "\n研究目标是尽可能提高指数 α。先查看问题页的当前纪录，再领取解析转移、筛法估计或指数挑战。"
                        "1.32301 与 1.324 可并行尝试；其他改进值可在 research/problems.json 提交新任务 PR。"
                        "纪录要求对无穷多个 n 证明存在素因子 p ∣ n²+1 且 p > nᵅ。" if lang == "zh" else
                        "\nAim for the largest provable exponent. Check the current record, then claim an analytic transfer, "
                        "sieve estimate or exponent challenge. Try 1.32301 or 1.324 in parallel, or propose another threshold "
                        "by PR to research/problems.json. A record requires a prime divisor p of n²+1 exceeding nᵅ for infinitely many n."
                    )
                _, _, instructions = asset.read_text(encoding="utf-8").split("\n\n", 2)
                instructions = instructions.replace(
                    "\npython tools/goldbach.py claim\n", f"\npython tools/goldbach.py claim --problem {slug}\n"
                )
                instructions = instructions.replace("https://www.goldbach.tech/#records\n", "").replace(
                    PUBLIC_SITE + "#records", f"{PUBLIC_SITE}problems/{slug}/?lang={lang}#records"
                )
                content = f"{title}\n\n{introduction}\n\n{instructions}".encode()
            return self.reply(200, content, ASSETS[path])
        if path != "/":
            return self.reply(404, b'{}')
        lang = self.language(url)
        page = (ROOT / f"{lang}.html").read_text(encoding="utf-8")
        if slug != "goldbach":
            page = problem_page(page, slug, lang)
        self.reply(200, page.encode(), "text/html", lang)

    do_HEAD = do_GET

    def desk_post(self, desk, path, slug):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 8192:
                return self.reply(413, b'{"error":"request body must be between 1 and 8192 bytes"}')
            self.connection.settimeout(10)
            raw = self.rfile.read(size)
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError()
            if path == "/api/desk/pending" and slug == "goldbach":
                status, result = queue_pending(raw, self.headers)
            else:
                if path == "/api/desk/authorize" and slug == "goldbach":
                    gap = body.get("gap")
                    if isinstance(gap, str):
                        desk = DESKS[GAP_DESKS.get(gap, "goldbach")]
                status, result = desk.dispatch(path, body, self.headers, str(self.client_ip()), raw)
        except (ValueError, OSError):
            return self.reply(400, b'{"error":"invalid request body"}')
        except sqlite3.Error as error:
            self.log_error("Desk unavailable: %s", error)
            return self.reply(503, b'{"error":"task desk temporarily unavailable"}')
        return self.reply(status, json.dumps(result, ensure_ascii=False).encode())

    def do_POST(self):
        if self.path.startswith(ZHIHU_PATH + "/"):
            return self.zhihu_request(urlsplit(self.path).path)
        desk, path, slug = self.scope(self.path)
        if desk is not None and path.startswith("/api/desk/"):
            return self.desk_post(desk, path, slug)
        if slug != "goldbach" or path != "/api/verdict":
            return self.reply(404, b'{}')
        try:
            self.connection.settimeout(10)
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 262144:
                return self.reply(413, b'{}')
            body = self.rfile.read(size)
            signature = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
            supplied = self.headers.get("X-Goldbach-Signature", "").encode()
            if not hmac.compare_digest(signature.encode(), supplied):
                return self.reply(401, b'{}')
            record = json.loads(body)
            lemma = record["lemma_id"]
            verdict = record["verdict"]
            run_id = record["run_id"]
            attempt = record["run_attempt"]
            manifest = record["manifest"]
            if type(run_id) is not int or run_id < 1 or type(attempt) is not int or attempt < 1:
                raise ValueError()
            if isinstance(lemma, str) and lemma in GAP_DESKS:
                desk = DESKS[GAP_DESKS[lemma]]
            elif not isinstance(lemma, str) or not re.fullmatch(r"L-goldbach-[a-z0-9-]+", lemma):
                raise ValueError()
            if verdict not in {"ACCEPTED", "REJECTED"}:
                raise ValueError()
            if verdict == "ACCEPTED":
                if not manifest["rests_on"]:
                    raise ValueError()
                for key in ("rests_on", "defs"):
                    if not isinstance(manifest[key], list):
                        raise ValueError()
                    for entry in manifest[key]:
                        if not isinstance(entry["module"], str) or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
                            raise ValueError()
            elif manifest is not None:
                raise ValueError()
        except (ValueError, KeyError, TypeError, OSError):
            return self.reply(400, b'{}')
        with closing(sqlite3.connect(desk.db_path)) as conn, conn:
            if desk is not DESK and conn.execute(
                "SELECT 1 FROM goldbach_leases WHERE run_id = ? AND gap = ?", (run_id, lemma)
            ).fetchone() is None:
                return self.reply(409, b'{"error":"no matching authorized run"}')
            conn.execute("CREATE TABLE IF NOT EXISTS verdicts (run_id INTEGER, attempt INTEGER, body BLOB, PRIMARY KEY (run_id, attempt))")
            inserted = conn.execute("INSERT OR IGNORE INTO verdicts VALUES (?, ?, ?)", (run_id, attempt, body))
            if inserted.rowcount == 1:
                desk.record_verdict(record, conn)
        self.reply(200, b'{"status":"stored"}')

class Server(ThreadingHTTPServer):
    request_queue_size = 256

    def __init__(self, address, handler):
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.tls.load_cert_chain(CREDS / "fullchain.pem", CREDS / "privkey.pem")
        self.slots = BoundedSemaphore(16)
        super().__init__(address, handler)

    def process_request(self, request, address):
        self.slots.acquire()
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def finish_request(self, request, address):
        request.settimeout(8)
        with self.tls.wrap_socket(request, server_side=True) as connection:
            super().finish_request(connection, address)

if __name__ == "__main__":
    Server(("127.0.0.1", 8443), Handler).serve_forever()
