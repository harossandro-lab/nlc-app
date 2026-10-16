"""Received: the delivery log (group, location, supply, date, material, length, species, qty, ticket, invoice,
payment) with each line priced from the Materials DB, plus "Delivered vs Ordered" by group. Every edit is saved at once."""
import sqlite3
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QProgressBar, QWidget

from .. import calc, reports
from ..dao import MaterialDbDao, ReceivedDao, SupplierDao, TakeoffItemDao
from ..formatting import DASH, number_text
from ..inputs import parse_date, parse_optional_number
from ..models import Project, ReceivedEntry
from ..section_order import sort_items
from ..seed import GROUPS, LENGTHS, LOCATIONS, SPECIES
from . import theme
from .editable_table import Column, ComboDelegate, EditableTablePanel


def _text_setter(attr: str):
    def set_text(r: ReceivedEntry, text: str) -> bool:
        setattr(r, attr, text)
        return True
    return set_text


def _set_date(r: ReceivedEntry, text: str) -> bool:
    d = parse_date(text)
    if d is None:
        return False
    r.date = d
    return True


def _set_qty(r: ReceivedEntry, text: str) -> bool:
    ok, value = parse_optional_number(text)
    if ok:
        r.qty = value
    return ok


class DeliverySummary(QWidget):
    """One bar per GROUP that has an order: delivered value / ordered value."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 8, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(6)
        self._grid.setColumnStretch(2, 1)
        self.bars: List[reports.DeliveryBar] = []

    def set_bars(self, bars: List[reports.DeliveryBar]) -> None:
        self.bars = bars
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        title = QLabel("DELIVERED VS ORDERED — BY GROUP")
        title.setStyleSheet(f"color: {theme.GRAY}; font-weight: bold; font-size: 12px;")
        self._grid.addWidget(title, 0, 0, 1, 3)
        if not bars:
            hint = QLabel("Sem dados de pedido ainda.")
            hint.setObjectName("hint")
            self._grid.addWidget(hint, 1, 0, 1, 3)
            return
        for i, b in enumerate(bars, start=1):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(round(b.percent)))
            bar.setTextVisible(False)
            bar.setFixedSize(260, 10)
            bar.setStyleSheet(f"QProgressBar {{ background: #EEF2F6; border: none; border-radius: 4px; }}"
                              f"QProgressBar::chunk {{ background: {theme.GREEN}; border-radius: 4px; }}")
            amount = QLabel(f"{calc.money(b.delivered)} / {calc.money(b.ordered)}")
            amount.setStyleSheet("font-family: Consolas, monospace;")
            self._grid.addWidget(QLabel(b.group), i, 0)
            self._grid.addWidget(bar, i, 1)
            self._grid.addWidget(amount, i, 2, Qt.AlignLeft)


class ReceivedPanel(EditableTablePanel):
    def __init__(self, conn: sqlite3.Connection, project: Project, parent=None):
        dao = ReceivedDao(conn)
        self.database = MaterialDbDao(conn).find_by_project(project.id)
        self.suppliers = SupplierDao(conn).find_by_project(project.id)
        self.by_group = calc.aggregate_by_group(
            sort_items(TakeoffItemDao(conn).find_by_project(project.id)), self.database, self.suppliers)
        supplier_names = [s.name for s in self.suppliers if s.name]

        def total_text(r: ReceivedEntry) -> str:
            t = calc.received_line_total(r, self.database, self.suppliers)
            return DASH if t is None else calc.money(t)

        super().__init__(
            title="Received",
            subtitle="Registro de entregas — ticket, nota fiscal e data, comparado ao pedido (Ordered).",
            add_label="+ Add delivery",
            columns=[
                Column("Group", lambda r: r.group, _text_setter("group"), width=170,
                       delegate=ComboDelegate(GROUPS, editable=False)),
                Column("Location", lambda r: r.location, _text_setter("location"), width=80,
                       delegate=ComboDelegate(LOCATIONS, editable=True)),
                Column("Supply", lambda r: r.supply, _text_setter("supply"), width=90,
                       delegate=ComboDelegate(supplier_names, editable=True)),
                Column("Date", lambda r: r.date, _set_date, width=95),
                Column("Material", lambda r: r.material, _text_setter("material"), width=130),
                Column("Length", lambda r: r.length, _text_setter("length"), width=70,
                       delegate=ComboDelegate(LENGTHS, editable=True)),
                Column("Species", lambda r: r.species, _text_setter("species"), width=90,
                       delegate=ComboDelegate(SPECIES, editable=True)),
                Column("Qty", lambda r: number_text(r.qty), _set_qty, right=True, width=60),
                Column("Ticket #", lambda r: r.ticket, _text_setter("ticket"), width=80),
                Column("Invoice #", lambda r: r.invoice, _text_setter("invoice"), width=80),
                Column("Payment", lambda r: r.payment, _text_setter("payment"), width=80),
                Column("Total", total_text, None, right=True, width=90),
            ],
            rows=dao.find_by_project(project.id),            # newest first
            persist=dao.update,
            create_row=lambda: dao.insert(ReceivedEntry(project_id=project.id)),
            delete_row=lambda r: dao.delete(r.id),
            empty_hint="Nenhuma entrega registrada ainda.",
            new_rows_on_top=True,                             # like the web app
            parent=parent)

        self.summary = DeliverySummary()
        self.add_footer(self.summary)
        self.model.dataChanged.connect(lambda *a: self.refresh_summary())
        self.model.rowsInserted.connect(lambda *a: self.refresh_summary())
        self.model.rowsRemoved.connect(lambda *a: self.refresh_summary())
        self.refresh_summary()

    def refresh_summary(self) -> None:
        self.summary.set_bars(reports.delivered_vs_ordered(
            self.by_group, self.model.rows, self.database, self.suppliers, GROUPS))
