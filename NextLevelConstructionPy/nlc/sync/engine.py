"""Push/pull engine. `Remote` is any object with push(changes) and pull(since, limit); the Supabase client will be
one implementation, tests use an in-memory fake. Conflict rule: last writer wins, ordered by the server's `seq`;
a row with a pending local edit is not overwritten by a pull (the local edit is pushed first and wins)."""
import sqlite3
from typing import Dict, List, Protocol

from . import local

BATCH = 200


class Remote(Protocol):
    def push(self, changes: List[dict]) -> None: ...
    def pull(self, since: int, limit: int) -> List[dict]: ...


def _meta(conn, key, value=None):
    if value is None:
        return conn.execute("SELECT value FROM sync_meta WHERE key=?", (key,)).fetchone()[0]
    conn.execute("UPDATE sync_meta SET value=? WHERE key=?", (str(value), key))


def _key_col(table: str) -> str:
    return {"projects": "id", "project_info": "project_id"}.get(table, "uid")


def _data_cols(conn, table: str) -> List[str]:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    return [c for c in cols if not (local.TABLES[table][0] and c in ("id", "uid"))]


class SyncEngine:
    def __init__(self, conn: sqlite3.Connection, remote: Remote):
        self.conn = conn
        self.remote = remote
        local.install(conn)

    def sync(self) -> Dict[str, int]:
        """Push local edits, then pull everyone else's. Returns {'pushed': n, 'pulled': n}."""
        if _meta(self.conn, "backfilled") == "0":
            local.enqueue_all(self.conn)
            _meta(self.conn, "backfilled", 1)
            self.conn.commit()
        return {"pushed": self._push(), "pulled": self._pull()}

    def _push(self) -> int:
        total = 0
        while True:
            rows = self.conn.execute("SELECT table_name, uid, project_id, op FROM sync_outbox LIMIT ?", (BATCH,)).fetchall()
            if not rows:
                return total
            changes = []
            for table, uid, project_id, op in rows:
                data = self._read(table, uid) if op == "upsert" else None
                changes.append({"table": table, "uid": uid, "project_id": project_id,
                                "data": data or {}, "deleted": data is None})
            self.remote.push(changes)      # raises on failure: the outbox stays, the next sync retries
            with self.conn:
                self.conn.executemany("DELETE FROM sync_outbox WHERE table_name=? AND uid=?", [(r[0], r[1]) for r in rows])
            total += len(rows)

    def _read(self, table: str, uid: str):
        cols = _data_cols(self.conn, table)
        r = self.conn.execute(f"SELECT {', '.join(cols)} FROM {table} WHERE {_key_col(table)}=?", (uid,)).fetchone()
        return dict(zip(cols, r)) if r else None

    def _pull(self) -> int:
        total = 0
        while True:
            since = int(_meta(self.conn, "cursor"))
            changes = self.remote.pull(since, BATCH)
            if not changes:
                return total
            changes.sort(key=lambda c: (local.ORDER.index(c["table"]), c["seq"]))   # parents first
            _meta(self.conn, "applying", 1)
            try:
                with self.conn:
                    for c in changes:
                        self._apply(c)
                    _meta(self.conn, "cursor", max(c["seq"] for c in changes))
            finally:
                _meta(self.conn, "applying", 0)
                self.conn.commit()
            total += len(changes)

    def _apply(self, c: dict) -> None:
        table, uid = c["table"], c["uid"]
        if self.conn.execute("SELECT 1 FROM sync_outbox WHERE table_name=? AND uid=?", (table, uid)).fetchone():
            return                          # pending local edit wins
        key = _key_col(table)
        if c["deleted"]:
            self.conn.execute(f"DELETE FROM {table} WHERE {key}=?", (uid,))
            return
        data = dict(c["data"])
        if table != "projects" and not self.conn.execute(
                "SELECT 1 FROM projects WHERE id=?", (c["project_id"],)).fetchone():
            return                          # job was removed; its rows are gone too
        if self.conn.execute(f"SELECT 1 FROM {table} WHERE {key}=?", (uid,)).fetchone():
            if data:
                sets = ", ".join(f"{k}=?" for k in data)
                self.conn.execute(f"UPDATE {table} SET {sets} WHERE {key}=?", (*data.values(), uid))
        else:
            if key == "uid":
                data["uid"] = uid
            cols = ", ".join(data)
            self.conn.execute(f"INSERT INTO {table}({cols}) VALUES ({', '.join('?' * len(data))})", tuple(data.values()))
