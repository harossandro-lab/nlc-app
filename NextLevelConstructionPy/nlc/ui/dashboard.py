"""Dashboard: totals (line items, estimated / ordered / received value), a bar per section and the job's title block."""
import sqlite3
from typing import Callable

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from .. import calc, reports
from ..dao import MaterialDbDao, ProjectDao, SupplierDao, TakeoffItemDao
from ..models import Project
from ..section_order import sort_items
from ..seed import SECTIONS
from . import theme
from .report_table import save_csv

FOOTNOTE = ('O TAKEOFF agora é automático: toda linha lançada em qualquer seção com um GROUP definido já entra somada '
            'na aba "Ordered (auto)", sem precisar consolidar manualmente. QTY, ItemKey e preço seguem a mesma lógica '
            'da planilha original.')

TITLE_FIELDS = [("name", "Project Name"), ("jobsite", "Jobsite Location"), ("builder", "Builder Name"),
                ("created_by", "Created By"), ("arch_date", "Architectural Plan Date"),
                ("struct_date", "Structural Plan Date"), ("total_sf", "Total Square Feet")]


class StackedBar(QWidget):
    """received (green) + ordered-but-not-received (amber) over a gray track, as percentages of the section total."""

    def __init__(self, received_pct: float, ordered_pct: float, parent=None):
        super().__init__(parent)
        self.received_pct = max(0.0, min(100.0, received_pct))
        self.ordered_only_pct = max(0.0, min(100.0 - self.received_pct, ordered_pct - received_pct))
        self.setFixedHeight(10)
        self.setMinimumWidth(200)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EEF2F6"))
        p.drawRoundedRect(QRectF(0, 0, w, h), 4, 4)
        x = 0.0
        for pct, color in ((self.received_pct, theme.GREEN), (self.ordered_only_pct, theme.AMBER)):
            if pct > 0:
                p.setBrush(QColor(color))
                p.drawRect(QRectF(x, 0, w * pct / 100.0, h))
                x += w * pct / 100.0
        p.end()


def _kpi(label: str, value: str, sub: str, accent: str) -> QFrame:
    card = QFrame()
    card.setObjectName("kpi")
    card.setStyleSheet(f"QFrame#kpi {{ border: 1px solid {theme.LINE}; border-left: 4px solid {accent}; background: {theme.WHITE}; }}"
                       f"QFrame#kpi QLabel {{ border: none; }}")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(4)
    lab = QLabel(label.upper())
    lab.setStyleSheet(f"color: {theme.GRAY}; font-size: 10.5px;")
    val = QLabel(value)
    val.setStyleSheet("font-family: Consolas, monospace; font-size: 22px; font-weight: bold;")
    lay.addWidget(lab)
    lay.addWidget(val)
    if sub:
        s = QLabel(sub)
        s.setStyleSheet(f"color: {theme.GRAY}; font-size: 11px;")
        lay.addWidget(s)
    card.value_label = val
    return card


class DashboardPanel(QWidget):
    def __init__(self, conn: sqlite3.Connection, project: Project, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.conn = conn
        self.project = project
        self.project_dao = ProjectDao(conn)
        self.items = sort_items(TakeoffItemDao(conn).find_by_project(project.id))
        self.database = MaterialDbDao(conn).find_by_project(project.id)
        self.suppliers = SupplierDao(conn).find_by_project(project.id)
        self.per_section, self.grand = reports.section_totals(self.items, self.database, self.suppliers, SECTIONS)
        self.info = self.project_dao.get_info(project.id)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)
        page = QWidget()
        page.setObjectName("page")
        scroll.setWidget(page)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 22, 26, 26)
        lay.setSpacing(18)

        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        heading = QLabel("Dashboard")
        heading.setObjectName("heading")
        sub = QLabel("Live overview")
        sub.setObjectName("subtitle")
        titles.addWidget(heading)
        titles.addWidget(sub)
        top.addLayout(titles, 1)
        self.export_button = QPushButton("Export all (CSV)")
        self.export_button.clicked.connect(self.export_all)
        top.addWidget(self.export_button, 0, Qt.AlignTop)
        lay.addLayout(top)

        lay.addLayout(self._kpi_row())
        lay.addWidget(self._section_bars())
        lay.addWidget(self._title_block())
        note = QLabel(FOOTNOTE)
        note.setWordWrap(True)
        note.setObjectName("hint")
        lay.addWidget(note)
        lay.addStretch(1)

    # ---- pieces ----
    def _kpi_row(self) -> QHBoxLayout:
        g = self.grand
        pct_ordered = reports.percent_rounded(g.ordered, g.total)
        pct_received = reports.percent_rounded(g.received, g.total)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.kpis = {
            "items": _kpi("Line items", str(g.count), "", theme.INK),
            "total": _kpi("Estimated total", calc.money(g.total), "", theme.ORANGE),
            "ordered": _kpi("Ordered value", calc.money(g.ordered), f"{pct_ordered}% of total", theme.AMBER),
            "received": _kpi("Received value", calc.money(g.received), f"{pct_received}% of total", theme.GREEN),
        }
        for card in self.kpis.values():
            row.addWidget(card, 1)
        return row

    def _section_bars(self) -> QWidget:
        box = QWidget()
        box.setObjectName("page")
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        title = QLabel("BY SECTION")
        title.setStyleSheet(f"color: {theme.GRAY}; font-weight: bold; font-size: 12px;")
        grid.addWidget(title, 0, 0, 1, 3)
        self.section_rows = []
        for i, (sec, t) in enumerate(self.per_section, start=1):
            pct_ord = t.ordered / t.total * 100 if t.total else 0.0
            pct_rec = t.received / t.total * 100 if t.total else 0.0
            name = QLabel(f"{sec['label']}  ({t.count})")
            amount = QLabel(calc.money(t.total))
            amount.setStyleSheet("font-family: Consolas, monospace;")
            amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(name, i, 0)
            grid.addWidget(StackedBar(pct_rec, pct_ord), i, 1)
            grid.addWidget(amount, i, 2)
            self.section_rows.append((sec["id"], t))
        legend = QLabel(f'<span style="color:{theme.GREEN}">■</span> Received &nbsp; '
                        f'<span style="color:{theme.AMBER}">■</span> Ordered &nbsp; '
                        f'<span style="color:#C7D2DB">■</span> Pending')
        legend.setStyleSheet(f"color: {theme.GRAY}; font-size: 11px;")
        grid.addWidget(legend, len(self.per_section) + 1, 0, 1, 3)
        return box

    def _title_block(self) -> QWidget:
        box = QFrame()
        box.setObjectName("titleblock")
        box.setStyleSheet(f"QFrame#titleblock {{ border: 1px solid {theme.LINE}; }} QFrame#titleblock QLabel {{ border: none; }}")
        grid = QGridLayout(box)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(14)
        self.fields = {}
        for i, (attr, label) in enumerate(TITLE_FIELDS):
            cell = QVBoxLayout()
            cell.setSpacing(4)
            lab = QLabel(label.upper())
            lab.setStyleSheet(f"color: {theme.GRAY}; font-size: 10px;")
            edit = QLineEdit(getattr(self.info, attr) or "")
            edit.setPlaceholderText("—")
            edit.textEdited.connect(self._saver(attr))
            cell.addWidget(lab)
            cell.addWidget(edit)
            grid.addLayout(cell, i // 2, i % 2)
            self.fields[attr] = edit
        return box

    def _saver(self, attr: str) -> Callable[[str], None]:
        def save(text: str) -> None:
            setattr(self.info, attr, text)
            self.project_dao.save_info(self.project.id, self.info)
        return save

    # ---- actions ----
    def csv_text(self) -> str:
        return reports.all_items_csv(self.items, self.database, self.suppliers, SECTIONS)

    def export_all(self) -> bool:
        return save_csv(self, f"{self.project.name or 'project'}-material-list-full.csv", self.csv_text())
