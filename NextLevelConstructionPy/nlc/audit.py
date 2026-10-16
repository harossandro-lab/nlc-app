"""Audit service: baseline when a job is first opened, and a diff after edits (ADDED / CHANGED / REMOVED).

The UI calls run_diff about 1.4 s after the last take-off edit (DELAY_MS, like the web app) and when the Audit Log
screen opens, so the log never looks out of date.
"""
import sqlite3
from typing import List

from . import calc
from .dao import AuditDao, TakeoffItemDao, now_iso
from .section_order import sort_items

DELAY_MS = 1400


def _current_totals(conn: sqlite3.Connection, project_id: str):
    return calc.totals_by_item_key(sort_items(TakeoffItemDao(conn).find_by_project(project_id)))


def ensure_baseline(conn: sqlite3.Connection, project_id: str) -> None:
    """First time a job is opened (no snapshot and no log yet) the current state becomes the baseline, without entries."""
    dao = AuditDao(conn)
    if not dao.get_snapshot(project_id) and dao.count_log(project_id) == 0:
        dao.save_run(project_id, now_iso(), [], _current_totals(conn, project_id))


def run_diff(conn: sqlite3.Connection, project_id: str) -> int:
    """Compares now with the snapshot and records the differences. Returns how many entries were added."""
    dao = AuditDao(conn)
    current = _current_totals(conn, project_id)
    diffs: List[calc.AuditChange] = calc.audit_diff(dao.get_snapshot(project_id), current)
    if not diffs:
        return 0
    dao.save_run(project_id, now_iso(), diffs, current)
    return len(diffs)
