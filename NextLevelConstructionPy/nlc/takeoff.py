"""Rules of the take-off section screens that do not need Qt: status cycle, filter text, typed numbers, subtitle, CSV."""
from typing import Optional, Tuple

from . import calc, reports
from .formatting import number_text
from .inputs import parse_number
from .models import TakeoffItem
from .seed import DEFAULT_GROUP, SPACINGS

STATUS_ORDER = ["pending", "ordered", "received"]
STATUS_LABEL = {"pending": "Pending", "ordered": "Ordered", "received": "Received"}
# (text color, background) of the status pill, like the Java StatusRenderer
STATUS_COLORS = {"pending": ("#5B6B7A", "#F1F3F5"), "ordered": ("#B9790E", "#FBF0DC"), "received": ("#2F7A4D", "#E7F3EC")}

# the SP drop-down: the workbook spacings plus the ply counts the web app offers
SP_OPTIONS = SPACINGS + ["2 Ply", "3 Ply"]


def next_status(status: Optional[str]) -> str:
    """pending -> ordered -> received -> pending. Anything else counts as pending."""
    idx = STATUS_ORDER.index(status) if status in STATUS_ORDER else 0
    return STATUS_ORDER[(idx + 1) % len(STATUS_ORDER)]


def status_key(status: Optional[str]) -> str:
    return status if status in STATUS_ORDER else "pending"


def search_text(it: TakeoffItem) -> str:
    """What the filter box looks at (the same columns as the web app)."""
    return " ".join([it.group, it.purpose, it.page_detail, it.material, it.length, it.species, it.location])


def parse_takeoff_number(text: str) -> Tuple[bool, Optional[float]]:
    """(accepted, value) for LF / SF / EA. Blank stays empty (None). A decimal comma is accepted (7,5 = 7.5).
    Anything that is not a plain number is rejected so the old value stays."""
    s = (text or "").strip()
    if not s:
        return True, None
    if "," in s and "." not in s and s.count(",") == 1:
        s = s.replace(",", ".")
    v = parse_number(s)
    return (False, None) if v is None else (True, v)


def new_item(project_id: str, section_id: str) -> TakeoffItem:
    """A blank line with the section's default GROUP, location FACTORY and status pending."""
    return TakeoffItem(project_id=project_id, section_id=section_id, group=DEFAULT_GROUP.get(section_id, ""),
                       location="FACTORY", status="pending")


def section_subtitle(count: int, total: float) -> str:
    return f"{count} line item(s) · estimated {calc.money(total)}"


def section_total(items, database, suppliers) -> float:
    return reports.totals_of(items, database, suppliers).total


def section_csv(items, database, suppliers) -> str:
    """The section's lines as the web export does (the "all" export without the Section column)."""
    rows = [reports.ALL_ITEMS_HEADER[1:]] + [reports.item_cells(it, database, suppliers) for it in items]
    return reports.to_csv(rows)


def qty_text(it: TakeoffItem) -> str:
    q = calc.compute_qty(it)
    return "—" if q is None else str(q)


def unit_text(it: TakeoffItem, database, suppliers) -> str:
    db = calc.find_db_entry(it, database)
    unit = None if db is None else calc.unit_price_of(db, suppliers)
    return "—" if unit is None else calc.fixed2(unit)


def total_text(it: TakeoffItem, database, suppliers) -> str:
    t = calc.line_total(it, database, suppliers)
    return "—" if t is None else calc.money(t)


def numeric_cell(v: Optional[float]) -> str:
    return number_text(v)
