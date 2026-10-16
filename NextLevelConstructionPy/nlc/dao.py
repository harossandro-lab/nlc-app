"""Data access for every table. Each DAO takes an open sqlite3 connection (see nlc.db.connect) and writes at once."""
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .calc import AuditChange
from .models import (MaterialDbEntry, Project, ProjectInfo, ReceivedEntry, Supplier, TakeoffItem)

MAX_AUDIT_ENTRIES = 400   # the web app keeps only the last 400


def _ns(s) -> str:
    return "" if s is None else s


def now_iso() -> str:
    """UTC timestamp like JavaScript's toISOString / Java's Instant.toString."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


class ProjectDao:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_all(self) -> List[Project]:
        rows = self.conn.execute("SELECT id, abbr, name, created_at FROM projects ORDER BY created_at").fetchall()
        return [Project(*r) for r in rows]

    def create(self, abbr: Optional[str], name: Optional[str]) -> Project:
        """New job plus its project_info and the default suppliers FACTORY / FIELD (0% tax)."""
        pid = "p" + uuid.uuid4().hex[:10]
        created = now_iso()
        clean_abbr = "JOB" if (abbr is None or not abbr.strip()) else abbr.strip().upper()[:5]
        clean_name = clean_abbr if (name is None or not name.strip()) else name.strip()
        with self.conn:
            self.conn.execute("INSERT INTO projects(id, abbr, name, created_at) VALUES (?,?,?,?)",
                              (pid, clean_abbr, clean_name, created))
            self.conn.execute("INSERT INTO project_info(project_id, name) VALUES (?,?)", (pid, clean_name))
            for supply in ("FACTORY", "FIELD"):
                self.conn.execute("INSERT INTO suppliers(project_id, name, tax, delay_days) VALUES (?,?,0,0)", (pid, supply))
        return Project(pid, clean_abbr, clean_name, created)

    def rename(self, project_id: str, abbr: str, name: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE projects SET abbr=?, name=? WHERE id=?", (abbr, name, project_id))

    def delete(self, project_id: str) -> None:
        """Hard delete: ON DELETE CASCADE also removes info, suppliers, materials, items, deliveries and audit."""
        with self.conn:
            self.conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def get_info(self, project_id: str) -> ProjectInfo:
        r = self.conn.execute("SELECT name, jobsite, builder, created_by, arch_date, struct_date, total_sf "
                              "FROM project_info WHERE project_id=?", (project_id,)).fetchone()
        return ProjectInfo(*[_ns(x) for x in r]) if r else ProjectInfo()

    def save_info(self, project_id: str, info: ProjectInfo) -> None:
        with self.conn:
            self.conn.execute("UPDATE project_info SET name=?, jobsite=?, builder=?, created_by=?, arch_date=?, "
                              "struct_date=?, total_sf=? WHERE project_id=?",
                              (info.name, info.jobsite, info.builder, info.created_by, info.arch_date,
                               info.struct_date, info.total_sf, project_id))


class SupplierDao:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_by_project(self, project_id: str) -> List[Supplier]:
        rows = self.conn.execute("SELECT id, name, tax, delay_days FROM suppliers WHERE project_id=? ORDER BY id",
                                 (project_id,)).fetchall()
        return [Supplier(name=_ns(r[1]), tax=r[2] or 0.0, delay=r[3] or 0, id=r[0], project_id=project_id) for r in rows]

    def insert(self, project_id: str, name: str, tax: float, delay: int) -> Supplier:
        with self.conn:
            cur = self.conn.execute("INSERT INTO suppliers(project_id, name, tax, delay_days) VALUES (?,?,?,?)",
                                    (project_id, name, tax, delay))
        return Supplier(name=name, tax=tax, delay=delay, id=cur.lastrowid, project_id=project_id)

    def update(self, s: Supplier) -> None:
        with self.conn:
            self.conn.execute("UPDATE suppliers SET name=?, tax=?, delay_days=? WHERE id=?", (s.name, s.tax, s.delay, s.id))

    def delete(self, supplier_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))


class MaterialDbDao:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_by_project(self, project_id: str) -> List[MaterialDbEntry]:
        rows = self.conn.execute("SELECT id, material, length, species, supply, unit_price_out_tax "
                                 "FROM materials_db WHERE project_id=? ORDER BY id", (project_id,)).fetchall()
        return [MaterialDbEntry(material=_ns(r[1]), length=_ns(r[2]), species=_ns(r[3]), supply=_ns(r[4]),
                                unit_price_out_tax=r[5] or 0.0, id=r[0], project_id=project_id) for r in rows]

    def insert(self, d: MaterialDbEntry) -> MaterialDbEntry:
        with self.conn:
            cur = self.conn.execute("INSERT INTO materials_db(project_id, material, length, species, supply, unit_price_out_tax) "
                                    "VALUES (?,?,?,?,?,?)",
                                    (d.project_id, d.material, d.length, d.species, d.supply, d.unit_price_out_tax))
        d.id = cur.lastrowid
        return d

    def update(self, d: MaterialDbEntry) -> None:
        with self.conn:
            self.conn.execute("UPDATE materials_db SET material=?, length=?, species=?, supply=?, unit_price_out_tax=? WHERE id=?",
                              (d.material, d.length, d.species, d.supply, d.unit_price_out_tax, d.id))

    def delete(self, material_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM materials_db WHERE id=?", (material_id,))


class TakeoffItemDao:
    _COLS = "id, section_id, group_name, purpose, page_detail, material, length, species, lf, sf, sp, ea, location, status"

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(r, project_id: str) -> TakeoffItem:
        return TakeoffItem(id=r[0], project_id=project_id, section_id=r[1], group=_ns(r[2]), purpose=_ns(r[3]),
                           page_detail=_ns(r[4]), material=_ns(r[5]), length=_ns(r[6]), species=_ns(r[7]),
                           lf=r[8], sf=r[9], sp=_ns(r[10]), ea=r[11], location=_ns(r[12]), status=_ns(r[13]))

    def find_by_section(self, project_id: str, section_id: str) -> List[TakeoffItem]:
        rows = self.conn.execute(f"SELECT {self._COLS} FROM takeoff_items WHERE project_id=? AND section_id=? ORDER BY id",
                                 (project_id, section_id)).fetchall()
        return [self._map(r, project_id) for r in rows]

    def find_by_project(self, project_id: str) -> List[TakeoffItem]:
        rows = self.conn.execute(f"SELECT {self._COLS} FROM takeoff_items WHERE project_id=? ORDER BY section_id, id",
                                 (project_id,)).fetchall()
        return [self._map(r, project_id) for r in rows]

    def insert(self, t: TakeoffItem) -> TakeoffItem:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO takeoff_items(project_id, section_id, group_name, purpose, page_detail, material, length, "
                "species, lf, sf, sp, ea, location, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (t.project_id, t.section_id, t.group, t.purpose, t.page_detail, t.material, t.length, t.species,
                 t.lf, t.sf, t.sp, t.ea, t.location, t.status))
        t.id = cur.lastrowid
        return t

    def update(self, t: TakeoffItem) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE takeoff_items SET group_name=?, purpose=?, page_detail=?, material=?, length=?, species=?, "
                "lf=?, sf=?, sp=?, ea=?, location=?, status=? WHERE id=?",
                (t.group, t.purpose, t.page_detail, t.material, t.length, t.species, t.lf, t.sf, t.sp, t.ea,
                 t.location, t.status, t.id))

    def delete(self, item_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM takeoff_items WHERE id=?", (item_id,))


class ReceivedDao:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_by_project(self, project_id: str) -> List[ReceivedEntry]:
        """Newest delivery first (the web app adds new rows at the top)."""
        rows = self.conn.execute("SELECT id, group_name, location, supply, date, material, length, species, qty, "
                                 "ticket, invoice, payment FROM received_log WHERE project_id=? ORDER BY id DESC",
                                 (project_id,)).fetchall()
        return [ReceivedEntry(id=r[0], project_id=project_id, group=_ns(r[1]), location=_ns(r[2]), supply=_ns(r[3]),
                              date=_ns(r[4]), material=_ns(r[5]), length=_ns(r[6]), species=_ns(r[7]), qty=r[8],
                              ticket=_ns(r[9]), invoice=_ns(r[10]), payment=_ns(r[11])) for r in rows]

    def insert(self, r: ReceivedEntry) -> ReceivedEntry:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO received_log(project_id, group_name, location, supply, date, material, length, species, "
                "qty, ticket, invoice, payment) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (r.project_id, r.group, r.location, r.supply, r.date, r.material, r.length, r.species, r.qty,
                 r.ticket, r.invoice, r.payment))
        r.id = cur.lastrowid
        return r

    def update(self, r: ReceivedEntry) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE received_log SET group_name=?, location=?, supply=?, date=?, material=?, length=?, species=?, "
                "qty=?, ticket=?, invoice=?, payment=? WHERE id=?",
                (r.group, r.location, r.supply, r.date, r.material, r.length, r.species, r.qty, r.ticket,
                 r.invoice, r.payment, r.id))

    def delete(self, received_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM received_log WHERE id=?", (received_id,))


@dataclass
class AuditEntry:
    id: int
    ts: str
    action: str
    item_key: str
    old_qty: Optional[int]
    new_qty: int


class AuditDao:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_log(self, project_id: str) -> List[AuditEntry]:
        """Newest entry first."""
        rows = self.conn.execute("SELECT id, ts, action, item_key, old_qty, new_qty FROM audit_log "
                                 "WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
        return [AuditEntry(*r) for r in rows]

    def count_log(self, project_id: str) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM audit_log WHERE project_id=?", (project_id,)).fetchone()[0]

    def get_snapshot(self, project_id: str) -> Dict[str, int]:
        rows = self.conn.execute("SELECT item_key, qty FROM audit_snapshot WHERE project_id=? ORDER BY rowid",
                                 (project_id,)).fetchall()
        return {k: q for k, q in rows}

    def save_run(self, project_id: str, ts: str, changes: List[AuditChange], new_snapshot: Dict[str, int]) -> None:
        """One transaction: stores the changes (the first change ends up on top), trims the log to the last 400
        entries and replaces the snapshot. `changes` may be empty (baseline only)."""
        with self.conn:
            for ch in reversed(changes):   # reverse: the first change gets the highest id
                self.conn.execute("INSERT INTO audit_log(project_id, ts, action, item_key, old_qty, new_qty) VALUES (?,?,?,?,?,?)",
                                  (project_id, ts, ch.action, ch.item_key, ch.old_qty, ch.new_qty))
            self.conn.execute("DELETE FROM audit_log WHERE project_id=? AND id NOT IN "
                              "(SELECT id FROM audit_log WHERE project_id=? ORDER BY id DESC LIMIT ?)",
                              (project_id, project_id, MAX_AUDIT_ENTRIES))
            self.conn.execute("DELETE FROM audit_snapshot WHERE project_id=?", (project_id,))
            self.conn.executemany("INSERT INTO audit_snapshot(project_id, item_key, qty) VALUES (?,?,?)",
                                  [(project_id, k, q) for k, q in new_snapshot.items()])
