"""Local change tracking for sync. Adds a global `uid` to every synced row and records each edit in `sync_outbox`
through SQLite triggers, so the DAOs and screens do not change. Applying changes pulled from the cloud sets
sync_meta.applying = 1, which silences the triggers."""
import sqlite3

# table -> (has_uid_column, uid_expr, project_expr), the expressions use the NEW./OLD. prefix
TABLES = {
    "projects":       (False, "{r}.id", "{r}.id"),
    "project_info":   (False, "{r}.project_id", "{r}.project_id"),
    "suppliers":      (True, "{r}.uid", "{r}.project_id"),
    "materials_db":   (True, "{r}.uid", "{r}.project_id"),
    "takeoff_items":  (True, "{r}.uid", "{r}.project_id"),
    "received_log":   (True, "{r}.uid", "{r}.project_id"),
    "audit_log":      (True, "{r}.uid", "{r}.project_id"),
}
ORDER = list(TABLES)   # parents first
_NEW_UID = "lower(hex(randomblob(16)))"

_META = """
CREATE TABLE IF NOT EXISTS sync_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO sync_meta(key, value) VALUES ('applying', '0'), ('cursor', '0'), ('backfilled', '0');
CREATE TABLE IF NOT EXISTS sync_outbox (
    table_name TEXT NOT NULL,
    uid        TEXT NOT NULL,
    project_id TEXT NOT NULL,
    op         TEXT NOT NULL,          -- 'upsert' or 'delete'
    PRIMARY KEY (table_name, uid)
);
"""
_QUIET = "(SELECT value FROM sync_meta WHERE key='applying') = '0'"


def _enqueue(table: str, op: str, row: str, uid_expr: str = None) -> str:
    _, uid, proj = TABLES[table]
    return (f"INSERT OR REPLACE INTO sync_outbox(table_name, uid, project_id, op) "
            f"VALUES ('{table}', {uid_expr or uid.format(r=row)}, {proj.format(r=row)}, '{op}');")


VERSION = "1"    # bump when the triggers change, so every device rebuilds them once


def install(conn: sqlite3.Connection) -> None:
    """Adds uid columns, fills them for existing rows, and (re)creates the triggers. Does nothing when this version
    is already installed, and otherwise works in ONE transaction, so an edit made meanwhile can never miss the outbox."""
    conn.executescript(_META)
    conn.execute("INSERT OR IGNORE INTO sync_meta(key, value) VALUES ('triggers', '')")
    conn.commit()
    if _get(conn, "triggers") == VERSION:
        return
    conn.execute("BEGIN IMMEDIATE")
    for table, (has_uid, _, _) in TABLES.items():
        if has_uid:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            if "uid" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN uid TEXT")
            conn.execute(f"UPDATE {table} SET uid = {_NEW_UID} WHERE uid IS NULL")
            conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_uid ON {table}(uid)")
        conn.execute(f"DROP TRIGGER IF EXISTS sync_{table}_ai")
        conn.execute(f"DROP TRIGGER IF EXISTS sync_{table}_au")
        conn.execute(f"DROP TRIGGER IF EXISTS sync_{table}_ad")
        if has_uid:
            conn.execute(f"""CREATE TRIGGER sync_{table}_ai AFTER INSERT ON {table} WHEN NEW.uid IS NULL AND {_QUIET} BEGIN
                UPDATE {table} SET uid = {_NEW_UID} WHERE id = NEW.id;
                {_enqueue(table, 'upsert', 'NEW', f'(SELECT uid FROM {table} WHERE id = NEW.id)')} END""")
        else:
            conn.execute(f"""CREATE TRIGGER sync_{table}_ai AFTER INSERT ON {table} WHEN {_QUIET} BEGIN
                {_enqueue(table, 'upsert', 'NEW')} END""")
        when_au = f"WHEN {_QUIET}" if not has_uid else f"WHEN NEW.uid IS OLD.uid AND {_QUIET}"
        conn.execute(f"""CREATE TRIGGER sync_{table}_au AFTER UPDATE ON {table} {when_au} BEGIN
            {_enqueue(table, 'upsert', 'NEW')} END""")
        conn.execute(f"""CREATE TRIGGER sync_{table}_ad AFTER DELETE ON {table} WHEN {_QUIET} BEGIN
            {_enqueue(table, 'delete', 'OLD')} END""")
    conn.execute("UPDATE sync_meta SET value=? WHERE key='triggers'", (VERSION,))
    conn.commit()


def _get(conn, key):
    return conn.execute("SELECT value FROM sync_meta WHERE key=?", (key,)).fetchone()[0]


def pending_count(conn: sqlite3.Connection) -> int:
    """Edits waiting to be sent (0 when sync was never installed)."""
    try:
        return conn.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def enqueue_all(conn: sqlite3.Connection) -> None:
    """First sync: queue every existing row so the cloud receives the data that existed before sync was on."""
    for table, (has_uid, uid, proj) in TABLES.items():
        conn.execute(f"INSERT OR REPLACE INTO sync_outbox(table_name, uid, project_id, op) "
                     f"SELECT '{table}', {uid.format(r=table)}, {proj.format(r=table)}, 'upsert' FROM {table}")
    conn.commit()
