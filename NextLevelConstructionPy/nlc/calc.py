"""All business logic, ported 1:1 from the Java CalcEngine (itself a port of the workbook's LET() QTY formula and VBA).

Keep this identical to CalcEngine.java and to computeQty/buildItemKey/aggregateByGroup in web/index.html.
"""
import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Iterable, List, Optional

JAVA_INT_MAX = 2147483647
NO_GROUP = "(sem grupo)"

# ---------------------------------------------------------------------------
# LENGTH parsing: VALUE(SUBSTITUTE(... "'" , '"' , "SF" ...)), plus mixed fractions like 104 5/8"
# ---------------------------------------------------------------------------
_MIXED_FRACTION = re.compile(r"^(\d+(?:\.\d+)?)\s+(\d+)/(\d+)$", re.ASCII)
_PLAIN_FRACTION = re.compile(r"^(\d+)/(\d+)$", re.ASCII)


def _div(a: float, b: float) -> float:
    """Division the way Java doubles behave: x/0 is +-infinity, 0/0 is NaN (no exception)."""
    if b != 0:
        return a / b
    if a == 0 or math.isnan(a):
        return math.nan
    return math.copysign(math.inf, a) * math.copysign(1.0, b)


def _parse_double(s: str) -> Optional[float]:
    try:
        v = float(s)
    except ValueError:
        return None
    if "_" in s or math.isnan(v) or math.isinf(v):
        return None
    return v


def parse_length(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    s = raw.strip()
    if not s or s.lower() == "n/a":
        return None
    s = s.replace("'", "").replace('"', "")
    s = re.sub(r"(?i)SF", "", s).strip()
    if not s:
        return None
    m = _MIXED_FRACTION.match(s)
    if m:
        return float(m.group(1)) + _div(float(m.group(2)), float(m.group(3)))
    m = _PLAIN_FRACTION.match(s)
    if m:
        return _div(float(m.group(1)), float(m.group(2)))
    return _parse_double(s)


# ---------------------------------------------------------------------------
# SP (spacing) column: either a spacing in inches or a ply count, never both
# ---------------------------------------------------------------------------
_PLY = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*ply", re.ASCII)
_FEET = re.compile(r"(\d+(?:\.\d+)?)\s*'", re.ASCII)
_FEET_WORD = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*ft", re.ASCII)
_INCHES = re.compile(r'(\d+(?:\.\d+)?)\s*"', re.ASCII)
_INCHES_WORD = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*in", re.ASCII)
_NUMERIC = re.compile(r"^\d+(\.\d+)?$", re.ASCII)


@dataclass
class SpacingPly:
    spacing: Optional[float] = None   # inches
    ply: Optional[float] = None


def parse_spacing_and_ply(sp_raw: Optional[str]) -> SpacingPly:
    out = SpacingPly()
    if sp_raw is None or not sp_raw.strip():
        return out
    text = sp_raw.strip()
    if _NUMERIC.match(text):
        out.spacing = float(text)
        return out
    m = _PLY.search(text)
    if m:
        out.ply = float(m.group(1))
        return out
    m = _FEET.search(text)
    if m:
        out.spacing = float(m.group(1)) * 12.0
        return out
    m = _FEET_WORD.search(text)
    if m:
        out.spacing = float(m.group(1)) * 12.0
        return out
    m = _INCHES.search(text)
    if m:
        out.spacing = float(m.group(1))
        return out
    m = _INCHES_WORD.search(text)
    if m:
        out.spacing = float(m.group(1))
        return out
    return out


def _java_int_ceil(x: float) -> int:
    """(int) Math.ceil(x) in Java: NaN -> 0, +-infinity and huge values saturate at the int range."""
    if math.isnan(x):
        return 0
    if x >= JAVA_INT_MAX:
        return JAVA_INT_MAX
    if x <= -JAVA_INT_MAX - 1:
        return -JAVA_INT_MAX - 1
    return int(math.ceil(x))


def compute_qty(it) -> Optional[int]:
    """The workbook's LET() QTY formula. First matching rule wins, then waste and rounding up. None = not enough data.

    1. PURPOSE contains "end stud"            -> LF*2/12
    2. spacing present and LF>0                -> LF*12/spacing (x EA when EA>0)
    3. SP has "N Ply"                          -> N*LF/length (needs LF and length), else N*EA
    4. otherwise                               -> LF/length, else SF/length, else EA
    5. x1.05 when PURPOSE has both "sheathing" and "roof", rounded UP to a whole piece
    """
    length = parse_length(it.length)
    lf = it.lf if it.lf is not None else 0.0
    sf = it.sf if it.sf is not None else 0.0
    ea = it.ea if it.ea is not None else 0.0
    desc = (it.purpose or "").lower()
    sap = parse_spacing_and_ply(it.sp)
    spacing, ply = sap.spacing, sap.ply
    spacing_count = _div(lf * 12.0, spacing) if (spacing is not None and spacing > 0 and lf > 0) else None

    raw_qty: Optional[float] = None
    if "end stud" in desc:
        raw_qty = (lf * 2.0 / 12.0) if lf > 0 else None
    elif spacing_count is not None and spacing_count > 0 and ea > 0:
        raw_qty = spacing_count * ea
    elif spacing_count is not None and spacing_count > 0:
        raw_qty = spacing_count
    elif ply is not None and ply > 0 and lf > 0 and length is not None:
        raw_qty = _div(ply * lf, length)
    elif ply is not None and ply > 0 and ea > 0:
        raw_qty = ply * ea
    elif lf > 0 and length is not None:
        raw_qty = _div(lf, length)
    elif sf > 0 and length is not None:
        raw_qty = _div(sf, length)
    elif ea > 0:
        raw_qty = ea
    if raw_qty is None:
        return None
    add_waste = 1.05 if ("sheathing" in desc and "roof" in desc) else 1.0
    return _java_int_ceil(raw_qty * add_waste)


# ---------------------------------------------------------------------------
# ItemKey = MATERIAL|LENGTH|SPECIES, empty parts and an N/A length dropped (BuildItemKey in the VBA)
# ---------------------------------------------------------------------------
def _clean_key_part(v: Optional[str]) -> str:
    return "" if v is None else v.strip()


def build_item_key(material, length, species) -> str:
    p0, p1, p2 = _clean_key_part(material), _clean_key_part(length), _clean_key_part(species)
    if p1.lower() == "n/a":
        p1 = ""
    return "|".join(p for p in (p0, p1, p2) if p)


def item_key_of(it) -> str:
    return build_item_key(it.material, it.length, it.species).lower()


def db_key_of(d) -> str:
    return build_item_key(d.material, d.length, d.species).lower()


# ---------------------------------------------------------------------------
# Pricing: unit = out-tax price * (1 + supplier tax% / 100)
# ---------------------------------------------------------------------------
def tax_for_supply(suppliers, supply_name: Optional[str]) -> float:
    if supply_name is None:
        return 0.0
    wanted = supply_name.strip().lower()
    for s in suppliers:
        if s.name is not None and s.name.strip().lower() == wanted:
            return s.tax
    return 0.0


def find_db_entry(it, database):
    """Materials DB row whose key matches the item's (ignoring case). `it` only needs material/length/species."""
    k = item_key_of(it)
    if not k:
        return None
    for d in database:
        if db_key_of(d) == k:
            return d
    return None


def unit_price_of(d, suppliers) -> Optional[float]:
    if d is None:
        return None
    return d.unit_price_out_tax * (1 + tax_for_supply(suppliers, d.supply) / 100.0)


def line_total(it, database, suppliers) -> Optional[float]:
    db = find_db_entry(it, database)
    if db is None:
        return None
    qty = compute_qty(it)
    if qty is None:
        return None
    unit = unit_price_of(db, suppliers)
    return None if unit is None else unit * qty


# ---------------------------------------------------------------------------
# Ordered (auto): sum of QTY by GROUP -> ItemKey across all sections
# ---------------------------------------------------------------------------
@dataclass
class OrderedLine:
    material: str
    length: str
    species: str
    qty: int = 0
    unit: Optional[float] = None       # unit price with tax; None when the key is not in the Materials DB
    supply: Optional[str] = None

    def total(self) -> Optional[float]:
        return None if self.unit is None else self.unit * self.qty


def aggregate_by_group(items: Iterable, database, suppliers) -> Dict[str, Dict[str, OrderedLine]]:
    """group -> (lower-case ItemKey -> line), both in first-seen order. Pass the items in workbook section order."""
    by_group: Dict[str, Dict[str, OrderedLine]] = {}
    for it in items:
        g = it.group if it.group else NO_GROUP
        k = item_key_of(it)
        if not k:
            continue
        qty = compute_qty(it)
        if not qty:
            continue
        db = find_db_entry(it, database)
        lines = by_group.setdefault(g, {})
        line = lines.get(k)
        if line is None:
            line = OrderedLine(it.material, it.length, it.species,
                               unit=None if db is None else unit_price_of(db, suppliers),
                               supply=None if db is None else db.supply)
            lines[k] = line
        line.qty += qty
    return by_group


def group_display_order(present: Iterable[str], canonical: List[str]) -> List[str]:
    present = list(present)
    return [g for g in canonical if g in present] + [g for g in present if g not in canonical]


# ---------------------------------------------------------------------------
# Audit log: diff of ItemKey totals before/after an edit
# ---------------------------------------------------------------------------
@dataclass
class AuditChange:
    action: str                 # ADDED | CHANGED | REMOVED
    item_key: str
    old_qty: Optional[int]
    new_qty: int


def totals_by_item_key(items: Iterable) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for it in items:
        k = item_key_of(it)
        if not k:
            continue
        qty = compute_qty(it)
        if not qty:
            continue
        totals[k] = totals.get(k, 0) + qty
    return totals


def audit_diff(prev: Dict[str, int], current: Dict[str, int]) -> List[AuditChange]:
    """ADDED / CHANGED in the order of `current`, then REMOVED in the order of `prev`."""
    diffs: List[AuditChange] = []
    for k, v in current.items():
        before = prev.get(k)
        if before is None:
            diffs.append(AuditChange("ADDED", k, None, v))
        elif before != v:
            diffs.append(AuditChange("CHANGED", k, before, v))
    for k, v in prev.items():
        if k not in current:
            diffs.append(AuditChange("REMOVED", k, v, 0))
    return diffs


# ---------------------------------------------------------------------------
# Received: delivery log compared with Ordered by GROUP
# ---------------------------------------------------------------------------
def received_line_total(r, database, suppliers) -> Optional[float]:
    db = find_db_entry(r, database)
    unit = None if db is None else unit_price_of(db, suppliers)
    qty = r.qty if r.qty is not None else 0.0
    return None if unit is None else unit * qty


def ordered_total(lines: Dict[str, OrderedLine]) -> float:
    return sum(l.unit * l.qty for l in lines.values() if l.unit is not None)


def delivered_total(group: str, received: Iterable, database, suppliers) -> float:
    total = 0.0
    for r in received:
        if r.group != group:
            continue
        t = received_line_total(r, database, suppliers)
        if t is not None:
            total += t
    return total


def delivered_percent(delivered: float, ordered: float) -> float:
    return min(100.0, delivered / ordered * 100) if ordered != 0 else 0.0


# ---------------------------------------------------------------------------
# Number formatting that matches the web app (JavaScript toFixed / toLocaleString)
# ---------------------------------------------------------------------------
def fixed2(v: float) -> str:
    """Two decimals rounded from the exact binary value (half up), like JS toFixed(2): 10.825 -> "10.82"."""
    return str(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def money(v: float) -> str:
    """"$1,234.50" like the web app's money()."""
    return "$" + format(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ",.2f")
