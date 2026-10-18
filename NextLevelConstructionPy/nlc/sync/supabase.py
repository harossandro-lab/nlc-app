"""Supabase client for the sync engine (stdlib only). Talks to two services of one project:
GoTrue (`/auth/v1`) for e-mail + password login, and PostgREST (`/rest/v1/sync_rows`) for the data.
Network problems raise ConnectionError, so SyncEngine leaves the outbox untouched and retries later."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

TIMEOUT = 20


class AuthError(Exception):
    """Wrong e-mail/password, expired login that cannot be refreshed, or a role without permission."""


def default_session_path() -> Path:
    return Path(os.environ.get("NLC_SESSION") or Path.home() / "NextLevelConstruction" / "session.json")


class SupabaseRemote:
    def __init__(self, url: str, anon_key: str, session_path: Optional[os.PathLike] = None):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.session_path = Path(session_path) if session_path is not None else default_session_path()
        self.session = self._load_session()

    # ---- login -------------------------------------------------------------------------------------------------
    @property
    def logged_in(self) -> bool:
        return bool(self.session.get("refresh_token"))

    def sign_in(self, email: str, password: str) -> None:
        self._store(self._auth("password", {"email": email, "password": password}))

    def sign_out(self) -> None:
        self.session = {}
        try:
            self.session_path.unlink()
        except FileNotFoundError:
            pass

    def _auth(self, grant: str, body: dict) -> dict:
        req = urllib.request.Request(f"{self.url}/auth/v1/token?grant_type={grant}", data=json.dumps(body).encode(),
                                     headers={"apikey": self.anon_key, "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 422):
                raise AuthError("Invalid e-mail or password" if grant == "password" else "Login expired, sign in again") from None
            raise ConnectionError(f"Supabase auth error {e.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ConnectionError(str(e)) from None

    def _store(self, tok: dict) -> None:
        self.session = {"access_token": tok["access_token"], "refresh_token": tok["refresh_token"],
                        "expires_at": time.time() + int(tok.get("expires_in", 3600)) - 60}
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(json.dumps(self.session), encoding="utf-8")

    def _load_session(self) -> dict:
        try:
            return json.loads(self.session_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _token(self) -> str:
        if not self.logged_in:
            raise AuthError("Not signed in")
        if time.time() >= self.session.get("expires_at", 0):
            self._store(self._auth("refresh_token", {"refresh_token": self.session["refresh_token"]}))
        return self.session["access_token"]

    # ---- data --------------------------------------------------------------------------------------------------
    def _rest(self, method: str, query: str, body=None, headers=None):
        req = urllib.request.Request(f"{self.url}/rest/v1/sync_rows{query}", method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"apikey": self.anon_key, "Authorization": f"Bearer {self._token()}",
                                              "Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AuthError("No permission for this change (check your role) or login expired") from None
            raise ConnectionError(f"Supabase error {e.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ConnectionError(str(e)) from None

    def push(self, changes: List[dict]) -> None:
        rows = [{"table_name": c["table"], "uid": c["uid"], "project_id": c["project_id"],
                 "data": c["data"], "deleted": c["deleted"]} for c in changes]
        self._rest("POST", "?on_conflict=table_name,uid", rows,
                   {"Prefer": "resolution=merge-duplicates,return=minimal"})

    def pull(self, since: int, limit: int) -> List[dict]:
        q = urllib.parse.urlencode({"select": "seq,table_name,uid,project_id,data,deleted", "seq": f"gt.{since}",
                                    "order": "seq.asc", "limit": limit})
        rows = self._rest("GET", "?" + q) or []
        return [{"seq": r["seq"], "table": r["table_name"], "uid": r["uid"], "project_id": r["project_id"],
                 "data": r["data"] or {}, "deleted": r["deleted"]} for r in rows]
