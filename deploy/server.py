import hashlib
import hmac
import ipaddress
import json
import os
import re
import sqlite3
import ssl
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
CREDS = Path(os.environ["CREDENTIALS_DIRECTORY"])
SECRET = (CREDS / "webhook").read_bytes().strip()
DB = Path(os.environ["STATE_DIRECTORY"]) / "verdicts.sqlite3"
GAPS = json.loads((ROOT / "gaps.json").read_text(encoding="utf-8"))["gaps"]
ASSETS = {
    "/site.css": "text/css",
    "/site.js": "text/javascript",
}


def research_status():
    results = []
    latest = {}
    attempts = 0
    if DB.exists():
        with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as conn:
            conn.execute("BEGIN")
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
    for gap in GAPS:
        result, proved = latest.get(gap["id"], (None, False))
        gaps.append({**gap, "latest": result, "proved": proved})
    accepted = sum(gap["proved"] for gap in gaps)
    return {
        "gaps": gaps,
        "results": results,
        "counts": {
            "published": len(gaps),
            "accepted": accepted,
            "open": len(gaps) - accepted,
            "attempts": attempts,
        },
    }

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
    def reply(self, status, body, content_type="application/json", language=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        if language:
            self.send_header("Content-Language", language)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/health":
            return self.reply(200, b'{"status":"ok"}')
        if url.path == "/api/status":
            try:
                body = json.dumps(research_status(), ensure_ascii=False, separators=(",", ":")).encode()
            except sqlite3.Error as error:
                self.log_error("Unable to read verdicts: %s", error)
                return self.reply(503, b'{"error":"verdicts unavailable"}')
            return self.reply(200, body)
        if url.path in ASSETS:
            asset = ROOT / url.path[1:]
            if not asset.is_file():
                return self.reply(404, b'{}')
            return self.reply(200, asset.read_bytes(), ASSETS[url.path])
        if url.path != "/":
            return self.reply(404, b'{}')
        lang = parse_qs(url.query).get("lang", [""])[0]
        if lang not in {"zh", "en"}:
            peer = ipaddress.ip_address(self.client_address[0])
            peer = getattr(peer, "ipv4_mapped", None) or peer
            if peer.is_loopback:
                forwarded = self.headers.get("X-Goldbach-Client-IP")
                if forwarded:
                    try:
                        peer = ipaddress.ip_address(forwarded)
                    except ValueError:
                        pass
            lang = "zh" if any(peer in net for net in NETWORKS) else "en"
        self.reply(200, (ROOT / f"{lang}.html").read_bytes(), "text/html", lang)

    do_HEAD = do_GET

    def do_POST(self):
        if self.path != "/api/verdict":
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
            if not re.fullmatch(r"L-goldbach-[a-z0-9-]+", lemma) or verdict not in {"ACCEPTED", "REJECTED"}:
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
        with closing(sqlite3.connect(DB)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS verdicts (run_id INTEGER, attempt INTEGER, body BLOB, PRIMARY KEY (run_id, attempt))")
            conn.execute("INSERT OR IGNORE INTO verdicts VALUES (?, ?, ?)", (run_id, attempt, body))
        self.reply(200, b'{"status":"stored"}')

class Server(HTTPServer):
    def get_request(self):
        sock, address = super().get_request()
        sock.settimeout(5)
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            cert = CREDS
            context.load_cert_chain(cert / "fullchain.pem", cert / "privkey.pem")
            return context.wrap_socket(sock, server_side=True), address
        except (OSError, ssl.SSLError):
            sock.close()
            raise

if __name__ == "__main__":
    Server(("127.0.0.1", 8443), Handler).serve_forever()
