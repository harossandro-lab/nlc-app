"""Ordered (auto): sum of QTY by GROUP -> ItemKey across every take-off section. Replaces the manual TAKEOFF sheet
and the Update_ORDERED_All macro of the workbook. Read-only, rebuilt each time it is opened."""
import sqlite3

from .. import calc, reports
from ..dao import MaterialDbDao, SupplierDao, TakeoffItemDao
from ..models import Project
from ..section_order import sort_items
from ..seed import GROUPS
from .report_table import ReportPanel


class OrderedPanel(ReportPanel):
    def __init__(self, conn: sqlite3.Connection, project: Project, parent=None):
        items = sort_items(TakeoffItemDao(conn).find_by_project(project.id))
        self.by_group = calc.aggregate_by_group(items, MaterialDbDao(conn).find_by_project(project.id),
                                                SupplierDao(conn).find_by_project(project.id))
        super().__init__(
            title="Ordered (auto)",
            subtitle="Somado automaticamente de todas as seções, por GROUP → ItemKey — substitui o passo manual do TAKEOFF original.",
            columns=reports.ORDERED_COLUMNS,
            rows=reports.ordered_rows(self.by_group, GROUPS),
            right_cols=(2, 3, 4, 5),
            widths=(300, 300, 70, 100, 90, 110),
            csv_text=lambda: reports.ordered_csv(self.by_group),
            csv_name=f"{project.name or 'project'}-ordered.csv",
            empty_hint="Nenhum item com GROUP definido ainda. Escolha um Group em cada linha das seções de takeoff "
                       "para aparecer aqui automaticamente.",
            parent=parent)
