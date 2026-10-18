import json
import tempfile
import unittest
from pathlib import Path

from nlc import db
from nlc.dao import ProjectDao
from nlc.sync import service
from nlc.sync.supabase import AuthError


class FakeRemote:
    logged_in = True

    def __init__(self, error=None):
        self.error, self.rows = error, []

    def push(self, changes):
        if self.error:
            raise self.error
        self.rows += changes

    def pull(self, since, limit):
        if self.error:
            raise self.error
        return []


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "m.db"
        conn = db.connect(self.db)
        ProjectDao(conn).create("AVN", "Avenel")
        conn.close()

    def test_config_round_trip_and_missing(self):
        p = Path(self.tmp.name) / "sync.json"
        self.assertIsNone(service.load_config(p))
        service.save_config(" https://x.supabase.co/ ", " KEY ", p)
        self.assertEqual(service.load_config(p), {"url": "https://x.supabase.co", "anon_key": "KEY"})
        p.write_text(json.dumps({"url": "", "anon_key": "K"}), encoding="utf-8")
        self.assertIsNone(service.load_config(p))

    def test_off_without_config(self):
        self.assertIsNone(service.make_remote(Path(self.tmp.name) / "none.json"))
        self.assertEqual(service.run_sync(self.db, None).status, "off")

    def test_ok_pushes_and_reports(self):
        r = FakeRemote()
        res = service.run_sync(self.db, r)
        self.assertEqual((res.status, res.pending), ("ok", 0))
        self.assertGreater(res.pushed, 0)

    def test_offline_keeps_pending_and_login_error_asks_for_login(self):
        res = service.run_sync(self.db, FakeRemote(ConnectionError("down")))
        self.assertEqual(res.status, "offline")
        self.assertGreater(res.pending, 0)
        self.assertEqual(service.run_sync(self.db, FakeRemote(AuthError("no role"))).status, "login")

    def test_not_signed_in(self):
        r = FakeRemote()
        r.logged_in = False
        self.assertEqual(service.run_sync(self.db, r).status, "login")


if __name__ == "__main__":
    unittest.main()
