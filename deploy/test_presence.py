import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deploy.desk import Desk
from deploy.presence import SitePresence


class PresenceTests(unittest.TestCase):
    def test_visits_are_deduplicated_and_expire_after_the_last_visible_ping(self):
        counts = SitePresence([])
        with patch("deploy.presence.time.monotonic") as clock:
            clock.return_value = 100
            self.assertEqual(counts.snapshot()["visitors"], 0)
            self.assertEqual(counts.snapshot("first")["visitors"], 1)
            self.assertEqual(counts.snapshot("second")["visitors"], 2)
            clock.return_value = 140
            self.assertEqual(counts.snapshot("first")["visitors"], 2)
            clock.return_value = 190
            self.assertEqual(counts.snapshot()["visitors"], 1)
            clock.return_value = 230
            self.assertEqual(counts.snapshot()["visitors"], 0)

    def test_agent_seats_count_only_unfinished_unsubmitted_live_leases_across_desks(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        desks = [Desk(folder / f"{i}.sqlite3", [], b"test") for i in range(2)]
        counts = SitePresence(desks)
        for desk in desks:
            with desk.transaction(write=True) as conn:
                rows = [
                    ("working", None, None, None, 201),
                    ("expired", None, None, None, 200),
                    ("submitted", 150, None, None, 300),
                    ("released", None, 160, None, 300),
                    ("finished", None, None, 170, 300),
                ]
                conn.executemany("""
                    INSERT INTO goldbach_leases
                      (gap, statement_sha256, handle, ip_key, claimed_at, absolute_expires_at,
                       token_hash, submitted_at, released_at, finished_at, expires_at)
                    VALUES ('test', 'test', 'user', 'local', 100, 500, ?, ?, ?, ?, ?)
                """, rows)
        with patch("deploy.presence.time.time", return_value=200), patch("deploy.presence.time.monotonic", return_value=50):
            self.assertEqual(counts.snapshot()["agents"], 2)
        with patch("deploy.presence.time.time", return_value=210), patch("deploy.presence.time.monotonic", return_value=60):
            self.assertEqual(counts.snapshot()["agents"], 0)
