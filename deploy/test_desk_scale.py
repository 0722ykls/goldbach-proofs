"""Run with python -m unittest deploy.test_desk_scale -v (Python 3.11+ and OpenSSL)."""

import hashlib
import hmac
import json
import os
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.client import HTTPSConnection
from pathlib import Path

from deploy.desk import QUEUE_BATCH, fleet_pass


ROOT = Path(__file__).resolve().parents[1]
SESSIONS = 128


class DeskScaleTest(unittest.TestCase):
    def setUp(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.secret = secrets.token_hex(32).encode()
        (folder / "webhook").write_bytes(self.secret)
        (folder / "china-apnic.txt").write_bytes(b"")
        for source in ("deploy/server.py", "deploy/desk.py", "research/gaps.json"):
            shutil.copy(ROOT / source, folder)
        openssl = os.environ.get("OPENSSL") or shutil.which("openssl")
        if not openssl and shutil.which("git"):
            git_openssl = Path(shutil.which("git")).parents[1] / "usr/bin/openssl.exe"
            if git_openssl.is_file():
                openssl = str(git_openssl)
        if not openssl:
            self.fail("Install OpenSSL or set OPENSSL to its executable to run the HTTPS scale test")
        subprocess.run([
            openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
            "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1",
            "-keyout", "privkey.pem", "-out", "fullchain.pem",
        ], cwd=folder, check=True, capture_output=True)
        self.context = ssl.create_default_context(cafile=str(folder / "fullchain.pem"))

        # Use the production TLS/thread/SQLite handlers with a random loopback port and test-only state.
        launcher = (
            "from server import Server, Handler\n"
            "Handler.log_request = lambda *args: None\n"
            "with Server(('127.0.0.1', 0), Handler) as server:\n"
            "    print(server.server_port, flush=True)\n"
            "    server.serve_forever()\n"
        )
        self.server = subprocess.Popen(
            [sys.executable, "-B", "-c", launcher], cwd=folder,
            env={**os.environ, "CREDENTIALS_DIRECTORY": str(folder), "STATE_DIRECTORY": str(folder)},
            stdout=subprocess.PIPE, text=True,
        )
        self.addCleanup(self.stop_server)
        self.port = int(self.server.stdout.readline())

    def stop_server(self):
        self.server.terminate()
        self.server.wait(timeout=10)
        self.server.stdout.close()

    def request(self, path, body=None, *, token=None, signed=False, ip=None, ticket=None, expected=200):
        raw = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if signed:
            headers["X-Goldbach-Signature"] = "sha256=" + hmac.new(self.secret, raw, hashlib.sha256).hexdigest()
        if ip:
            # The production proxy supplies this header to the loopback upstream.
            headers["X-Goldbach-Client-IP"] = ip
        if ticket:
            headers["X-Goldbach-Fleet"] = ticket
        with closing(HTTPSConnection("127.0.0.1", self.port, timeout=45, context=self.context)) as conn:
            conn.request("POST" if raw is not None else "GET", path, body=raw, headers=headers)
            response = conn.getresponse()
            result = json.load(response)
            self.assertEqual(response.status, expected, (path, result.get("error")))
            return result

    def wave(self, pool, mode, label, action, size=SESSIONS):
        ready = threading.Barrier(size, timeout=30)

        def client(i):
            ready.wait()
            return action(i)

        start = time.monotonic()
        results = list(pool.map(client, range(size)))
        print(f"{mode}: {size} {label} in {time.monotonic() - start:.2f}s", flush=True)
        return results

    def test_128_concurrent_public_and_fleet_sessions(self):
        api = "/api/desk/"
        with ThreadPoolExecutor(max_workers=SESSIONS) as pool:
            for mode in ("public", "fleet"):
                with self.subTest(mode=mode):
                    ticket = None
                    if mode == "fleet":
                        ticket = fleet_pass(self.secret, "lab", int(time.time()) + 3600)

                    def claim(i):
                        handle = "lab" if ticket else f"researcher-{i}"
                        ip = "192.0.2.200" if ticket else f"192.0.2.{i + 1}"
                        return self.request(api + "claim", {"handle": handle}, ticket=ticket, ip=ip, expected=201)

                    claims = self.wave(pool, mode, "claims", claim)
                    tokens = [item["lease"]["token"] for item in claims]
                    gaps = {item["gap"]["id"] for item in claims}
                    catalogue = json.loads((ROOT / "research/gaps.json").read_text(encoding="utf-8"))["gaps"]
                    self.assertEqual(gaps, {entry["id"] for entry in catalogue})
                    for entry in catalogue:
                        count = sum(item["gap"]["id"] == entry["id"] for item in claims)
                        if not entry.get("parallel"):
                            self.assertEqual(count, 1)
                    self.assertGreater(SESSIONS, len(gaps))
                    self.assertEqual(len(set(tokens)), SESSIONS)
                    status = self.request("/api/status")["desk"]
                    self.assertEqual(set(status["assignments"]), gaps)
                    self.assertEqual(status["active"], SESSIONS)
                    if ticket:
                        self.request(api + "claim", {"handle": "lab"}, ticket=ticket, expected=429)
                        self.request(api + "claim", {"handle": "outsider"}, ticket=ticket, expected=401)
                    self.wave(pool, mode, "renewals", lambda i: self.request(api + "beat", {}, token=tokens[i]))
                    self.wave(pool, mode, "submissions", lambda i: self.request(
                        api + "submit", {"pr": i + 1, "head": f"{i + 1:040x}"}, token=tokens[i],
                    ))
                    pending = []
                    for _ in range(0, SESSIONS, QUEUE_BATCH):
                        page = self.request(api + "pending", {}, signed=True)["pending"]
                        self.assertTrue(0 < len(page) <= QUEUE_BATCH)
                        pending.extend(page)
                    self.assertEqual(len(pending), SESSIONS)
                    self.assertEqual({row["gap"] for row in pending}, gaps)
                    self.assertEqual({row["pr"] for row in pending}, set(range(1, SESSIONS + 1)))
                    self.assertEqual(self.request(api + "pending", {}, signed=True)["pending"], [])
                    self.wave(pool, mode, "returns", lambda i: self.request(
                        api + "release", {"reason": "abandoned"}, token=tokens[i],
                    ))
                    self.assertEqual(self.request("/api/status")["desk"]["active"], 0)


if __name__ == "__main__":
    unittest.main()
