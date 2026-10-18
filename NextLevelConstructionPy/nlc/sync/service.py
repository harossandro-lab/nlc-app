"""Glue between the app and the sync engine, free of any UI: where the Supabase settings live, and one `run_sync` call
that a background thread can make. It opens its OWN database connection (sqlite3 connections are per-thread)."""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .. import db
from . import local
from .engine import SyncEngine
from .supabase import AuthError, SupabaseRemote


def config_path() -> Path:
    return Path(os.environ.get("NLC_SYNC") or Path.home() / "NextLevelConstruction" / "sync.json")


def load_config(path: Optional[os.PathLike] = None) -> Optional[dict]:
    """{'url': ..., 'anon_key': ...} or None while team sync is not set up on this computer."""
    try:
        cfg = json.loads(Path(path or config_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return cfg if cfg.get("url") and cfg.get("anon_key") else None


def save_config(url: str, anon_key: str, path: Optional[os.PathLike] = None) -> None:
    p = Path(path or config_path())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"url": url.strip().rstrip("/"), "anon_key": anon_key.strip()}), encoding="utf-8")


@dataclass
class SyncResult:
    status: str          # off | login | offline | ok
    pushed: int = 0
    pulled: int = 0
    pending: int = 0
    message: str = ""


def make_remote(config_file=None, session_file=None) -> Optional[SupabaseRemote]:
    cfg = load_config(config_file)
    return SupabaseRemote(cfg["url"], cfg["anon_key"], session_file) if cfg else None


def run_sync(db_path, remote) -> SyncResult:
    """One round: push, then pull. Never raises; the outcome is in the result. `remote` None = sync not set up."""
    if remote is None:
        return SyncResult("off")
    if not remote.logged_in:
        return SyncResult("login", message="Sign in to sync with the team")
    conn = db.connect(db_path)
    try:
        try:
            counts = SyncEngine(conn, remote).sync()
            return SyncResult("ok", counts["pushed"], counts["pulled"], local.pending_count(conn))
        except AuthError as e:
            return SyncResult("login", pending=local.pending_count(conn), message=str(e))
        except ConnectionError as e:
            return SyncResult("offline", pending=local.pending_count(conn), message=str(e))
    finally:
        conn.close()
