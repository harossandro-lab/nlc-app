"""Materials Database: the pricing catalog keyed by Material | Length | Species (ItemKey), with supplier and base price.
The Tax % and the final unit price are computed from the supplier."""
import sqlite3

from .. import calc
from ..dao import MaterialDbDao, SupplierDao
from ..formatting import DASH, number_text
from ..inputs import parse_number
from ..models import MaterialDbEntry, Project
from ..seed import LENGTHS, SPECIES
from .editable_table import Column, ComboDelegate, EditableTablePanel


def _text_setter(attr: str):
    def set_text(d: MaterialDbEntry, text: str) -> bool:
        setattr(d, attr, text)
        return True
    return set_text


def _set_price(d: MaterialDbEntry, text: str) -> bool:
    v = parse_number(text)
    if v is None:
        return False
    d.unit_price_out_tax = v
    return True


class MaterialsDbPanel(EditableTablePanel):
    def __init__(self, conn: sqlite3.Connection, project: Project, parent=None):
        dao = MaterialDbDao(conn)
        self.suppliers = SupplierDao(conn).find_by_project(project.id)
        supplier_names = [s.name for s in self.suppliers if s.name]

        def tax_text(d: MaterialDbEntry) -> str:
            return calc.fixed2(calc.tax_for_supply(self.suppliers, d.supply))

        def final_text(d: MaterialDbEntry) -> str:
            unit = calc.unit_price_of(d, self.suppliers)
            return DASH if unit is None else calc.fixed2(unit)

        super().__init__(
            title="Materials Database",
            subtitle="Catálogo Material · Comprimento · Espécie (ItemKey) com preço-base e fornecedor.",
            add_label="+ Add material",
            columns=[
                Column("Material", lambda d: d.material, _text_setter("material"), width=200),
                Column("Length", lambda d: d.length, _text_setter("length"), width=100,
                       delegate=ComboDelegate(LENGTHS, editable=True)),
                Column("Species", lambda d: d.species, _text_setter("species"), width=130,
                       delegate=ComboDelegate(SPECIES, editable=True)),
                Column("Supply", lambda d: d.supply, _text_setter("supply"), width=110,
                       delegate=ComboDelegate(supplier_names, editable=True)),
                Column("Unit $ (no tax)", lambda d: number_text(d.unit_price_out_tax), _set_price, right=True, width=120),
                Column("Tax%", tax_text, None, right=True, width=70),
                Column("Unit $ (final)", final_text, None, right=True, width=110),
            ],
            rows=dao.find_by_project(project.id),
            persist=dao.update,
            create_row=lambda: dao.insert(MaterialDbEntry(project_id=project.id, supply="FACTORY")),
            delete_row=lambda d: dao.delete(d.id),
            empty_hint="No materials yet.",
            parent=parent)
