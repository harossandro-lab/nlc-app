"""A take-off section (Sub-Floor, 1st-6th Floor Walls, Roof, ...): one editable line per row, with QTY, unit price and
total computed from the workbook formula. One generic screen for all 13 sections.

- SPECIES first, then MATERIAL: the MATERIAL drop-down lists only the materials of the row's species (DATE-BASE).
- Click the Status pill to cycle pending -> ordered -> received. Every edit is saved at once.
- About 1.4 s after the last edit the audit log compares the ItemKey totals (like the Java TakeoffTableModel)."""
import sqlite3

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

from .. import audit, calc, reports, takeoff
from ..dao import MaterialDbDao, SupplierDao, TakeoffItemDao
from ..models import Project, TakeoffItem
from ..seed import GROUPS, LENGTHS, LOCATIONS, SECTIONS, SPECIES, materials_for_species
from . import theme
from .editable_table import Column, ComboDelegate, EditableTablePanel
from .report_table import save_csv


def _text_setter(attr: str):
    def set_text(it: TakeoffItem, text: str) -> bool:
        setattr(it, attr, text)
        return True
    return set_text


def _number_setter(attr: str):
    def set_number(it: TakeoffItem, text: str) -> bool:
        ok, value = takeoff.parse_takeoff_number(text)
        if ok:
            setattr(it, attr, value)
        return ok
    return set_number


def _cycle_status(it: TakeoffItem) -> bool:
    it.status = takeoff.next_status(it.status)
    return True


class TakeoffPanel(EditableTablePanel):
    def __init__(self, conn: sqlite3.Connection, project: Project, section_id: str, parent=None):
        sections = {s["id"]: s for s in SECTIONS}
        if section_id not in sections:
            raise ValueError(f"Unknown section: {section_id}")
        self.section = sections[section_id]
        self.conn = conn
        self.project = project
        items_dao = TakeoffItemDao(conn)
        self.database = MaterialDbDao(conn).find_by_project(project.id)
        self.suppliers = SupplierDao(conn).find_by_project(project.id)
        db, sup = self.database, self.suppliers

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter rows…")
        self.search_box.setFixedWidth(200)
        self.export_button = QPushButton("Export CSV")

        def pill_color(it):
            return takeoff.STATUS_COLORS[takeoff.status_key(it.status)][0]

        def pill_background(it):
            return takeoff.STATUS_COLORS[takeoff.status_key(it.status)][1]

        super().__init__(
            title=self.section["label"],
            subtitle="",
            add_label="+ Add line",
            columns=[
                Column("Group", lambda i: i.group, _text_setter("group"), width=130,
                       delegate=ComboDelegate(GROUPS, editable=False)),
                Column("Purpose", lambda i: i.purpose, _text_setter("purpose"), width=140,
                       delegate=ComboDelegate(self.section["purposes"], editable=True)),
                Column("Page/Detail", lambda i: i.page_detail, _text_setter("page_detail"), width=90),
                Column("Material", lambda i: i.material, _text_setter("material"), width=150,
                       delegate=ComboDelegate(lambda i: materials_for_species(i.species), editable=True)),
                Column("Length", lambda i: i.length, _text_setter("length"), width=70,
                       delegate=ComboDelegate(LENGTHS, editable=True)),
                Column("Species", lambda i: i.species, _text_setter("species"), width=90,
                       delegate=ComboDelegate(SPECIES, editable=True)),
                Column("LF", lambda i: takeoff.numeric_cell(i.lf), _number_setter("lf"), right=True, width=50),
                Column("SF", lambda i: takeoff.numeric_cell(i.sf), _number_setter("sf"), right=True, width=50),
                Column("SP", lambda i: i.sp, _text_setter("sp"), width=70,
                       delegate=ComboDelegate(takeoff.SP_OPTIONS, editable=True)),
                Column("EA", lambda i: takeoff.numeric_cell(i.ea), _number_setter("ea"), right=True, width=50),
                Column("QTY", takeoff.qty_text, None, right=True, width=60, bold=True),
                Column("Location", lambda i: i.location, _text_setter("location"), width=80,
                       delegate=ComboDelegate(LOCATIONS, editable=True)),
                Column("Unit $", lambda i: takeoff.unit_text(i, db, sup), None, right=True, width=65),
                Column("Total", lambda i: takeoff.total_text(i, db, sup), None, right=True, width=90),
                Column("Status", lambda i: takeoff.STATUS_LABEL[takeoff.status_key(i.status)], None, width=90,
                       on_click=_cycle_status, color=pill_color, background=pill_background, bold=True),
            ],
            rows=items_dao.find_by_section(project.id, section_id),
            persist=items_dao.update,
            create_row=lambda: items_dao.insert(takeoff.new_item(project.id, section_id)),
            delete_row=lambda i: items_dao.delete(i.id),
            empty_hint='Nenhuma linha ainda. Clique em "+ Add line" para começar o takeoff desta seção.',
            header_widgets=[self.search_box, self.export_button],
            search_text=takeoff.search_text,
            parent=parent)

        self.total_label = QLabel()
        self.total_label.setStyleSheet(f"font-weight: bold; color: {theme.INK};")
        self.add_footer(self.total_label)

        self.search_box.textChanged.connect(self.set_filter)
        self.export_button.clicked.connect(self.export_csv)

        # the audit comparison runs 1.4 s after the last edit
        self._audit_timer = QTimer(self)
        self._audit_timer.setSingleShot(True)
        self._audit_timer.setInterval(audit.DELAY_MS)
        self._audit_timer.timeout.connect(self.flush)
        for signal in (self.model.dataChanged, self.model.rowsInserted, self.model.rowsRemoved):
            signal.connect(lambda *a: self._changed())
        self.refresh_totals()

    # ---- totals, audit ----
    def refresh_totals(self) -> None:
        rows = self.model.rows
        total = takeoff.section_total(rows, self.database, self.suppliers)
        self.subtitle_label.setText(takeoff.section_subtitle(len(rows), total))
        self.total_label.setText(f"Section total   {calc.money(total)}")

    def _changed(self) -> None:
        self.refresh_totals()
        self._audit_timer.start()

    def flush(self) -> None:
        """Runs the audit comparison now if an edit is waiting for it (also called when leaving the screen)."""
        was_waiting = self._audit_timer.isActive()
        self._audit_timer.stop()
        if was_waiting:
            audit.run_diff(self.conn, self.project.id)

    # ---- actions ----
    def add_row(self) -> None:
        super().add_row()
        last = self.model.index(self.model.rowCount() - 1, 1)     # start typing in Purpose
        self.table.setCurrentIndex(last)
        self.table.edit(last)

    def csv_text(self) -> str:
        return takeoff.section_csv(self.model.rows, self.database, self.suppliers)

    def export_csv(self) -> bool:
        return save_csv(self, f"{self.project.name or 'project'}-{self.section['id']}.csv", self.csv_text())
