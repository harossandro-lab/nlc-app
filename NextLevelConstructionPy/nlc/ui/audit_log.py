"""Audit Log: automatic history of quantity changes per ItemKey (ADDED / CHANGED / REMOVED), like the original
PRICE_AUDIT sheet. Read-only. Opening it first records any edit whose comparison has not run yet."""
import sqlite3

from .. import audit, reports
from ..dao import AuditDao
from ..models import Project
from .report_table import ReportPanel


class AuditPanel(ReportPanel):
    def __init__(self, conn: sqlite3.Connection, project: Project, parent=None):
        audit.run_diff(conn, project.id)        # catch up with edits that were not compared yet
        self.entries = AuditDao(conn).find_log(project.id)
        super().__init__(
            title="Audit Log",
            subtitle="Histórico automático de alterações de quantidade por ItemKey — como a aba PRICE_AUDIT original.",
            columns=reports.AUDIT_COLUMNS,
            rows=reports.audit_rows(self.entries),
            right_cols=(3, 4),
            widths=(170, 90, 380, 80, 80),
            csv_text=lambda: reports.audit_csv(self.entries),
            csv_name=f"{project.name or 'project'}-audit-log.csv",
            empty_hint="Nenhuma mudança registrada ainda. O log é gerado automaticamente ao adicionar, editar ou "
                       "remover linhas de takeoff.",
            parent=parent)
