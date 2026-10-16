"""SQLite access. One file holds every job; by default the same file the Java app uses:
~/NextLevelConstruction/material_list.db (override with the NLC_DB environment variable or the `path` argument)."""
import os
import sqlite3
from pathlib import Path
from typing import Optional

_SCHEMA = Path(__file__).with_name("schema.sql")


def default_path() -> Path:
    env = os.environ.get("NLC_DB")
    if env:
        return Path(env)
    return Path.home() / "NextLevelConstruction" / "material_list.db"


def connect(path: Optional[os.PathLike] = None) -> sqlite3.Connection:
    """Opens (creating if needed) the database, turns foreign keys on and creates any missing table."""
    p = Path(path) if path is not None else default_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    return conn
