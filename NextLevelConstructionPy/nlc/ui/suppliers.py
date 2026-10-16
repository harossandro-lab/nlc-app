"""Suppliers & Tax: supplier names with their tax % (the tblSupplyTax table of the PRICE sheet) and delay in days.
Final unit price = unit price without tax x (1 + Tax% / 100)."""
import sqlite3

from ..dao import SupplierDao
from ..formatting import number_text
from ..inputs import parse_number, parse_whole_number
from ..models import Project, Supplier
from .editable_table import Column, EditableTablePanel


def _set_name(s: Supplier, text: str) -> bool:
    s.name = text
    return True


def _set_tax(s: Supplier, text: str) -> bool:
    v = parse_number(text)
    if v is None:
        return False
    s.tax = v
    return True


def _set_delay(s: Supplier, text: str) -> bool:
    v = parse_whole_number(text)
    if v is None:
        return False
    s.delay = v
    return True


class SuppliersPanel(EditableTablePanel):
    def __init__(self, conn: sqlite3.Connection, project: Project, parent=None):
        dao = SupplierDao(conn)
        super().__init__(
            title="Suppliers & Tax",
            subtitle="Preço final = Preço sem imposto × (1 + Tax% do fornecedor) — igual à aba PRICE original.",
            add_label="+ Add supplier",
            columns=[
                Column("Supply (name)", lambda s: s.name, _set_name, width=220),
                Column("Tax %", lambda s: number_text(s.tax), _set_tax, right=True, width=120),
                Column("Delay (days)", lambda s: number_text(s.delay), _set_delay, right=True, width=120),
            ],
            rows=dao.find_by_project(project.id),
            persist=dao.update,
            create_row=lambda: dao.insert(project.id, "", 0, 0),
            delete_row=lambda s: dao.delete(s.id),
            parent=parent)
