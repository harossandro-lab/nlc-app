import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from nlc import db
from nlc.dao import ProjectDao
from nlc.sync.engine import SyncEngine
from nlc.sync.supabase import AuthError, SupabaseRemote


class FakeSupabase(BaseHTTPRequestHandler):
    """Just enough of GoTrue + PostgREST: password/refresh login, bulk upsert and 'seq greater than' reads."""
    rows, seq, role = {}, 0, "office"

    def log_message(self, *a):
        pass

    def _send(self, code, body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"null")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/auth/v1/token":
            b = self._body()
            if parse_qs(u.query)["grant_type"][0] == "password" and b["password"] != "right":
                return self._send(400, {"error": "invalid_grant"})
            return self._send(200, {"access_token": "AT", "refresh_token": "RT", "expires_in": 3600})
        if self.headers.get("Authorization") != "Bearer AT" or self.headers.get("apikey") != "ANON":
            return self._send(401)
        if FakeSupabase.role == "none":
            return self._send(403)
        for r in self._body():
            FakeSupabase.seq += 1
            FakeSupabase.rows[(r["table_name"], r["uid"])] = {**r, "seq": FakeSupabase.seq}
        self._send(201)

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        since, limit = int(q["seq"][0][3:]), int(q["limit"][0])
        out = sorted((r for r in FakeSupabase.rows.values() if r["seq"] > since), key=lambda r: r["seq"])[:limit]
        self._send(200, out)


class SupabaseClientTest(unittest.TestCase):
    def setUp(self):
        FakeSupabase.rows, FakeSupabase.seq, FakeSupabase.role = {}, 0, "office"
        self.srv = HTTPServer(("127.0.0.1", 0), FakeSupabase)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"

    def remote(self, name="s.json"):
        return SupabaseRemote(self.url, "ANON", Path(self.tmp.name) / name)

    def test_wrong_password_is_rejected(self):
        with self.assertRaises(AuthError):
            self.remote().sign_in("a@b.c", "wrong")

    def test_login_is_remembered_and_two_devices_sync_through_http(self):
        r1 = self.remote("one.json")
        r1.sign_in("a@b.c", "right")
        self.assertTrue(self.remote("one.json").logged_in)            # a new process finds the saved login
        r2 = self.remote("two.json")
        r2.sign_in("c@d.e", "right")
        a = db.connect(Path(self.tmp.name) / "a.db")
        b = db.connect(Path(self.tmp.name) / "b.db")
        self.addCleanup(b.close)
        self.addCleanup(a.close)
        ProjectDao(a).create("AVN", "Avenel")
        SyncEngine(a, r1).sync()
        SyncEngine(b, r2).sync()
        self.assertEqual([p.abbr for p in ProjectDao(b).find_all()], ["AVN"])

    def test_not_signed_in_and_no_permission(self):
        with self.assertRaises(AuthError):
            self.remote().pull(0, 10)
        r = self.remote()
        r.sign_in("a@b.c", "right")
        FakeSupabase.role = "none"
        with self.assertRaises(AuthError):
            r.push([{"table": "projects", "uid": "p1", "project_id": "p1", "data": {}, "deleted": False}])

    def test_server_down_raises_connection_error_and_sign_out_forgets_login(self):
        r = self.remote()
        r.sign_in("a@b.c", "right")
        self.srv.shutdown()
        self.srv.server_close()
        with self.assertRaises(ConnectionError):
            r.pull(0, 10)
        r.sign_out()
        self.assertFalse(self.remote().logged_in)


if __name__ == "__main__":
    unittest.main()
