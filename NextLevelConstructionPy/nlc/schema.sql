-- Next Level Construction — Material List
-- SQLite schema. One local file (material_list.db) holds every project.

CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    abbr        TEXT NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_info (
    project_id   TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    name         TEXT DEFAULT '',
    jobsite      TEXT DEFAULT '',
    builder      TEXT DEFAULT '',
    created_by   TEXT DEFAULT '',
    arch_date    TEXT DEFAULT '',
    struct_date  TEXT DEFAULT '',
    total_sf     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS suppliers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    tax         REAL DEFAULT 0,
    delay_days  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS materials_db (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    material            TEXT DEFAULT '',
    length              TEXT DEFAULT '',
    species             TEXT DEFAULT '',
    supply              TEXT DEFAULT 'FACTORY',
    unit_price_out_tax  REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS takeoff_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    section_id   TEXT NOT NULL,
    group_name   TEXT DEFAULT '',
    purpose      TEXT DEFAULT '',
    page_detail  TEXT DEFAULT '',
    material     TEXT DEFAULT '',
    length       TEXT DEFAULT '',
    species      TEXT DEFAULT '',
    lf           REAL,
    sf           REAL,
    sp           TEXT DEFAULT '',
    ea           REAL,
    location     TEXT DEFAULT 'FACTORY',
    status       TEXT DEFAULT 'pending'
);

-- Received: one row per delivery (ticket / invoice / date). Newest rows have the highest id.
CREATE TABLE IF NOT EXISTS received_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    group_name  TEXT DEFAULT '',
    location    TEXT DEFAULT 'FACTORY',
    supply      TEXT DEFAULT '',
    date        TEXT DEFAULT '',
    material    TEXT DEFAULT '',
    length      TEXT DEFAULT '',
    species     TEXT DEFAULT '',
    qty         REAL,
    ticket      TEXT DEFAULT '',
    invoice     TEXT DEFAULT '',
    payment     TEXT DEFAULT ''
);

-- Audit log of quantity changes per ItemKey (like PRICE_AUDIT). Newest rows have the highest id.
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ts          TEXT NOT NULL,
    action      TEXT NOT NULL,
    item_key    TEXT NOT NULL,
    old_qty     INTEGER,
    new_qty     INTEGER NOT NULL
);

-- Last known total QTY per ItemKey: the "before" side of the next comparison.
CREATE TABLE IF NOT EXISTS audit_snapshot (
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    item_key    TEXT NOT NULL,
    qty         INTEGER NOT NULL,
    PRIMARY KEY (project_id, item_key)
);

CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_log(project_id);
CREATE INDEX IF NOT EXISTS idx_received_project ON received_log(project_id);
CREATE INDEX IF NOT EXISTS idx_items_project_section ON takeoff_items(project_id, section_id);
CREATE INDEX IF NOT EXISTS idx_materials_project ON materials_db(project_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_project ON suppliers(project_id);
