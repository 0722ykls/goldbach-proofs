import hashlib
import hmac
import ipaddress
import re
import secrets
import sqlite3
import time
from contextlib import closing, contextmanager

LEASE_SECONDS = 45 * 60
MAX_RESEARCH_SECONDS = 6 * 60 * 60
SUBMISSION_SECONDS = 12 * 60 * 60
CHECK_SECONDS = 3 * 60 * 60
NETWORK_ACTIVE_LIMIT = 3
NETWORK_HOURLY_LIMIT = 12
FLEET_ACTIVE_LIMIT = 128
QUEUE_BATCH = 16
QUEUE_RETRY_SECONDS = 15 * 60
HANDLE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.ASCII)
HEAD = re.compile(r"[0-9a-f]{40}", re.ASCII)
TOKEN = re.compile(r"Bearer ([A-Za-z0-9_-]{43})", re.ASCII)
RELEASE_REASONS = {
    "abandoned",
    "does_not_elaborate",
    "exhausted",
    "hypothesis_too_weak",
    "missing_lemma",
    "not_a_fit",
    "other",
    "out_of_time",
    "statement_seems_false",
    "superseded",
}


def canonical_handle(value):
    if isinstance(value, str) and value.isascii() and len(value) <= 39 and HANDLE.fullmatch(value.lower()):
        return value.lower()
    return None


def positive_id(value, maximum=(1 << 63) - 1):
    return type(value) is int and 0 < value <= maximum


def fleet_pass(secret, handle, expires):
    message = f"goldbach/fleet/v1/{handle}/{expires}".encode("ascii")
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return f"v1.{expires}.{signature}"


def error(status, code):
    return status, {"error": code}


class Desk:
    def __init__(self, db_path, gaps, secret):
        self.db_path = db_path
        self.gaps = {gap["id"]: gap for gap in gaps}
        self.statement_hashes = {
            gap_id: hashlib.sha256(gap["statement"].encode("utf-8")).hexdigest()
            for gap_id, gap in self.gaps.items()
        }
        self.secret = secret
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS goldbach_leases (
                    token_hash TEXT PRIMARY KEY,
                    gap TEXT NOT NULL,
                    statement_sha256 TEXT NOT NULL,
                    handle TEXT NOT NULL,
                    ip_key TEXT NOT NULL,
                    claimed_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    absolute_expires_at INTEGER NOT NULL,
                    pr INTEGER,
                    head TEXT,
                    submitted_at INTEGER,
                    run_id INTEGER UNIQUE,
                    checking_at INTEGER,
                    released_at INTEGER,
                    release_reason TEXT,
                    finished_at INTEGER,
                    verdict TEXT CHECK(verdict IN ('ACCEPTED', 'REJECTED'))
                );
                CREATE INDEX IF NOT EXISTS goldbach_leases_ip_time
                    ON goldbach_leases(ip_key, claimed_at);
                CREATE UNIQUE INDEX IF NOT EXISTS goldbach_leases_authorized_head
                    ON goldbach_leases(pr, head) WHERE run_id IS NOT NULL;
            """)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(goldbach_leases)")}
            if "last_polled_at" not in columns:
                conn.execute("ALTER TABLE goldbach_leases ADD COLUMN last_polled_at INTEGER")

    @contextmanager
    def transaction(self, write=False):
        with closing(sqlite3.connect(self.db_path, timeout=15)) as conn, conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn

    def network_key(self, client_ip):
        try:
            addr = ipaddress.ip_address(client_ip)
        except ValueError:
            return None
        addr = getattr(addr, "ipv4_mapped", None) or addr
        network = str(addr) if addr.version == 4 else str(ipaddress.IPv6Network((addr, 64), strict=False))
        return hmac.new(self.secret, b"desk network:" + network.encode("ascii"), hashlib.sha256).hexdigest()

    @staticmethod
    def proved_gaps(conn):
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='verdicts'").fetchone():
            return set()
        return {
            row[0] for row in conn.execute("""
                SELECT DISTINCT json_extract(CAST(body AS TEXT), '$.lemma_id')
                FROM verdicts
                WHERE json_extract(CAST(body AS TEXT), '$.verdict') = 'ACCEPTED'
            """)
        }

    @staticmethod
    def lease_times(lease):
        return {key: lease[key] for key in ("expires_at", "absolute_expires_at")}

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def claim(self, body, client_ip, now, fleet=None):
        handle = canonical_handle(body.get("handle"))
        ip_key = self.network_key(client_ip)
        requested_gap = body.get("gap")
        if not handle or not ip_key or (requested_gap is not None and not isinstance(requested_gap, str)):
            return error(400, "invalid_claim")
        if requested_gap is not None and requested_gap not in self.gaps:
            return error(404, "unknown_gap")
        if fleet is not None:
            match = re.fullmatch(r"v1\.([0-9]{1,12})\.[a-f0-9]{64}", fleet)
            if (not match or int(match[1]) <= now
                    or not hmac.compare_digest(fleet, fleet_pass(self.secret, handle, int(match[1])))):
                return error(401, "invalid_fleet_pass")
            # A registered fleet has its own bucket, including behind a shared university NAT.
            ip_key = "fleet:" + handle
        with self.transaction(write=True) as conn:
            active = conn.execute("""
                SELECT gap, handle, ip_key FROM goldbach_leases
                WHERE expires_at > ? AND released_at IS NULL AND finished_at IS NULL
            """, (now,)).fetchall()
            handle_count = sum(lease["handle"] == handle for lease in active)
            if fleet is None and handle_count:
                return error(409, "handle_already_active")
            if fleet is not None and handle_count >= FLEET_ACTIVE_LIMIT:
                return error(429, "fleet_active_limit")
            if fleet is None and sum(lease["ip_key"] == ip_key for lease in active) >= NETWORK_ACTIVE_LIMIT:
                return error(429, "network_active_limit")
            if conn.execute("""
                SELECT COUNT(*) FROM goldbach_leases WHERE ip_key = ? AND claimed_at > ?
            """, (ip_key, now - 3600)).fetchone()[0] >= (4 * FLEET_ACTIVE_LIMIT if fleet else NETWORK_HOURLY_LIMIT):
                return error(429, "network_claim_limit")

            occupied = {lease["gap"] for lease in active}
            unavailable = occupied | self.proved_gaps(conn)
            candidates = self.gaps if requested_gap is None else (requested_gap,)
            selected = next((gap_id for gap_id in candidates if gap_id not in unavailable), None)
            if selected is None:
                return error(409, "no_available_gap")

            token = secrets.token_urlsafe(32)
            expires = now + LEASE_SECONDS
            absolute = now + MAX_RESEARCH_SECONDS
            conn.execute("""
                INSERT INTO goldbach_leases
                    (token_hash, gap, statement_sha256, handle, ip_key, claimed_at, expires_at, absolute_expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.token_hash(token), selected, self.statement_hashes[selected],
                  handle, ip_key, now, expires, absolute))
            return 201, {
                "gap": self.gaps[selected],
                "lease": {"token": token, "expires_at": expires, "absolute_expires_at": absolute},
            }

    def update_lease(self, action, body, authorization, now):
        token = TOKEN.fullmatch(authorization)
        if token is None:
            return error(401, "invalid_lease")
        digest = self.token_hash(token[1])
        with self.transaction(write=True) as conn:
            lease = conn.execute("SELECT * FROM goldbach_leases WHERE token_hash = ?", (digest,)).fetchone()
            if lease is None:
                return error(401, "invalid_lease")
            if lease["released_at"] is not None:
                return (200, {"released": True}) if action == "release" else error(410, "lease_released")
            if lease["finished_at"] is not None:
                return error(410, "lease_completed")
            if lease["expires_at"] <= now:
                return error(410, "lease_expired")

            if action == "beat":
                times = self.lease_times(lease)
                if lease["pr"] is None:
                    times["expires_at"] = min(now + LEASE_SECONDS, lease["absolute_expires_at"])
                    conn.execute("UPDATE goldbach_leases SET expires_at = ? WHERE token_hash = ?",
                                 (times["expires_at"], digest))
                return 200, times
            if action == "release":
                if lease["run_id"] is not None:
                    return error(409, "check_already_started")
                reason = body.get("reason", "abandoned")
                if not isinstance(reason, str) or reason not in RELEASE_REASONS:
                    return error(400, "invalid_release_reason")
                conn.execute("""
                    UPDATE goldbach_leases SET released_at = ?, release_reason = ? WHERE token_hash = ?
                """, (now, reason, digest))
                return 200, {"released": True}

            pr, head = body.get("pr"), body.get("head")
            if not positive_id(pr, 9_999_999) or not isinstance(head, str) or not HEAD.fullmatch(head):
                return error(400, "invalid_pull_request")
            if lease["pr"] is not None:
                if lease["pr"] == pr and lease["head"] == head:
                    return 200, {"submitted": True, **self.lease_times(lease)}
                return error(409, "lease_already_submitted")

            # A submitted proof waits for a hosted runner independently of its authoring lease.
            expires = now + SUBMISSION_SECONDS
            conn.execute("""
                UPDATE goldbach_leases SET pr = ?, head = ?, submitted_at = ?, expires_at = ?
                WHERE token_hash = ?
            """, (pr, head, now, expires, digest))
            return 200, {"submitted": True, "expires_at": expires,
                         "absolute_expires_at": lease["absolute_expires_at"]}

    def signed(self, supplied, raw_body):
        expected = "sha256=" + hmac.new(self.secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.encode("ascii"), supplied.encode("utf-8"))

    def pending(self, now):
        with self.transaction(write=True) as conn:
            rows = conn.execute("""
                SELECT token_hash, pr, head, handle, gap FROM goldbach_leases
                WHERE pr IS NOT NULL AND run_id IS NULL AND released_at IS NULL AND expires_at > ?
                  AND (last_polled_at IS NULL OR last_polled_at <= ?)
                ORDER BY last_polled_at IS NOT NULL, last_polled_at, submitted_at, rowid LIMIT ?
            """, (now, now - QUEUE_RETRY_SECONDS, QUEUE_BATCH)).fetchall()
            conn.executemany("UPDATE goldbach_leases SET last_polled_at = ? WHERE token_hash = ?",
                             [(now, row["token_hash"]) for row in rows])
            return 200, {"pending": [{key: row[key] for key in ("pr", "head", "handle", "gap")} for row in rows]}

    def authorize(self, body, supplied, raw_body, now):
        if not self.signed(supplied, raw_body):
            return error(401, "invalid_signature")

        pr, head, run_id = body.get("pr"), body.get("head"), body.get("run_id")
        handle, gap = canonical_handle(body.get("handle")), body.get("gap")
        statement_hash = body.get("statement_sha256")
        if (not positive_id(pr, 9_999_999) or not positive_id(run_id)
                or not isinstance(head, str) or not HEAD.fullmatch(head)
                or not handle or not isinstance(gap, str)
                or not isinstance(statement_hash, str)):
            return error(400, "invalid_authorization")
        with self.transaction(write=True) as conn:
            lease = conn.execute("""
                SELECT * FROM goldbach_leases WHERE pr = ? AND head = ? AND handle = ? AND gap = ?
                ORDER BY (run_id = ?) DESC, claimed_at DESC, rowid DESC LIMIT 1
            """, (pr, head, handle, gap, run_id)).fetchone()
            if (lease is None or lease["released_at"] is not None
                    or lease["statement_sha256"] != statement_hash
                    or self.statement_hashes.get(gap) != statement_hash):
                return error(409, "no_matching_submission")
            if lease["run_id"] == run_id and lease["expires_at"] > now and lease["finished_at"] is None:
                return 200, {"authorized": True}
            if lease["run_id"] is not None or lease["expires_at"] <= now:
                return error(409, "submission_unavailable")
            if gap in self.proved_gaps(conn):
                return error(409, "gap_already_proved")
            if conn.execute("SELECT 1 FROM goldbach_leases WHERE run_id = ?", (run_id,)).fetchone():
                return error(409, "run_already_authorized")
            if conn.execute("""
                SELECT 1 FROM goldbach_leases WHERE pr = ? AND head = ? AND run_id IS NOT NULL
            """, (pr, head)).fetchone():
                return error(409, "head_already_authorized")

            conn.execute("""
                UPDATE goldbach_leases SET run_id = ?, checking_at = ?, expires_at = ?
                WHERE token_hash = ?
            """, (run_id, now, now + CHECK_SECONDS, lease["token_hash"]))
            return 200, {"authorized": True}

    def dispatch(self, path, body, headers, client_ip, raw_body):
        if not isinstance(body, dict):
            return error(400, "invalid_json")
        now = int(time.time())
        if path == "/api/desk/claim":
            return self.claim(body, client_ip, now, headers.get("X-Goldbach-Fleet"))
        if path == "/api/desk/pending":
            if not self.signed(headers.get("X-Goldbach-Signature", ""), raw_body):
                return error(401, "invalid_signature")
            return self.pending(now)
        if path == "/api/desk/authorize":
            return self.authorize(body, headers.get("X-Goldbach-Signature", ""), raw_body, now)
        if path in {"/api/desk/beat", "/api/desk/release", "/api/desk/submit"}:
            return self.update_lease(path.rsplit("/", 1)[1], body, headers.get("Authorization", ""), now)
        return error(404, "unknown_endpoint")

    @staticmethod
    def record_verdict(record, conn):
        # An accepted rerun supersedes a rejection, while a failed rerun cannot erase credit.
        verdict = record["verdict"]
        conn.execute("""
            UPDATE goldbach_leases SET finished_at = ?, verdict = ?
            WHERE run_id = ? AND gap = ?
              AND (verdict IS NULL OR (verdict = 'REJECTED' AND ? = 'ACCEPTED'))
        """, (int(time.time()), verdict, record["run_id"], record["lemma_id"], verdict))

    def public_status(self):
        now = int(time.time())
        with self.transaction() as conn:
            sessions, active = conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(expires_at > ? AND released_at IS NULL AND finished_at IS NULL), 0)
                FROM goldbach_leases
            """, (now,)).fetchone()
            assignments = dict(conn.execute("""
                SELECT gap, CASE WHEN run_id IS NOT NULL THEN 'checking'
                                 WHEN submitted_at IS NOT NULL THEN 'submitted'
                                 ELSE 'working' END
                FROM goldbach_leases
                WHERE expires_at > ? AND released_at IS NULL AND finished_at IS NULL
            """, (now,)))
            activities = [
                {key: value for key, value in dict(row).items() if value is not None}
                for row in conn.execute("""
                    WITH events AS (
                        SELECT claimed_at AS at, 'claimed' AS kind, gap AS lemma_id,
                               NULL AS handle, NULL AS pr, NULL AS run_id, NULL AS reason, 0 AS stage
                        FROM goldbach_leases
                        UNION ALL
                        SELECT submitted_at, 'submitted', gap, NULL, NULL, NULL, NULL, 1
                        FROM goldbach_leases WHERE submitted_at IS NOT NULL
                        UNION ALL
                        SELECT checking_at, 'checking', gap, handle, pr, run_id, NULL, 2
                        FROM goldbach_leases WHERE checking_at IS NOT NULL
                        UNION ALL
                        SELECT released_at, 'released', gap, NULL, NULL, NULL, release_reason, 3
                        FROM goldbach_leases WHERE released_at IS NOT NULL
                        UNION ALL
                        SELECT finished_at, lower(verdict), gap, handle, pr, run_id, NULL, 3
                        FROM goldbach_leases WHERE finished_at IS NOT NULL
                        UNION ALL
                        SELECT expires_at, 'expired', gap,
                               CASE WHEN run_id IS NOT NULL THEN handle END,
                               CASE WHEN run_id IS NOT NULL THEN pr END, run_id, NULL, 3
                        FROM goldbach_leases
                        WHERE expires_at <= ? AND released_at IS NULL AND finished_at IS NULL
                    )
                    SELECT at, kind, lemma_id, handle, pr, run_id, reason FROM events
                    ORDER BY at DESC, stage DESC, lemma_id LIMIT 30
                """, (now,))
            ]
            leaderboard = [
                dict(row) for row in conn.execute("""
                    SELECT handle, COUNT(DISTINCT gap) AS accepted FROM goldbach_leases
                    WHERE verdict = 'ACCEPTED' GROUP BY handle ORDER BY accepted DESC, handle LIMIT 20
                """)
            ]
        return {
            "active": active, "sessions": sessions, "assignments": assignments,
            "activities": activities, "leaderboard": leaderboard,
        }
