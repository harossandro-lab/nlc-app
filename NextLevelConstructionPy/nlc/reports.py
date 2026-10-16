"""Rows and CSV text of the read-only report screens (Ordered, Audit Log). No Qt, so it is easy to test.

The CSV files are exactly what the web app exports (same header, same row order, same number rounding)."""
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from . import calc
from .calc import OrderedLine
from .formatting import DASH, format_timestamp

ORDERED_COLUMNS = ["Group", "Material · Length · Species", "Qty", "Supply", "Unit $", "Total"]
AUDIT_COLUMNS = ["Timestamp", "Action", "ItemKey", "Old Qty", "New Qty"]


@dataclass
class ReportRow:
    kind: str                       # GROUP | ITEM | SUBTOTAL | GRAND (Ordered) or ITEM (Audit Log)
    cells: List[str]
    tone: Dict[int, str] = field(default_factory=dict)   # column -> good | warn | bad | muted | accent


def describe(line: OrderedLine) -> str:
    """"material · length · species", leaving out empty parts."""
    return " · ".join(p for p in (line.material, line.length, line.species) if p)


def ordered_rows(by_group: Dict[str, Dict[str, OrderedLine]], canonical_groups: Iterable[str]) -> List[ReportRow]:
    """Group header, its items, its subtotal; then GRAND TOTAL. Groups in canonical order first, then any other."""
    rows: List[ReportRow] = []
    grand = 0.0
    for g in calc.group_display_order(by_group.keys(), list(canonical_groups)):
        entries = by_group[g]
        n = len(entries)
        rows.append(ReportRow("GROUP", [f"{g}  ({n} item{'' if n == 1 else 's'})", "", "", "", "", ""]))
        group_total = 0.0
        for line in entries.values():
            total = line.total()
            if total is not None:
                group_total += total
                grand += total
            rows.append(ReportRow("ITEM", [
                "", describe(line), str(line.qty), line.supply if line.supply is not None else DASH,
                DASH if line.unit is None else calc.fixed2(line.unit),
                DASH if total is None else calc.money(total)], tone={2: "accent"}))
        rows.append(ReportRow("SUBTOTAL", [f"Subtotal — {g}", "", "", "", "", calc.money(group_total)]))
    if rows:
        rows.append(ReportRow("GRAND", ["GRAND TOTAL", "", "", "", "", calc.money(grand)]))
    return rows


def _csv_cell(v) -> str:
    v = "" if v is None else str(v)
    if "," in v or '"' in v or "\n" in v:
        return '"' + v.replace('"', '""') + '"'
    return v


def _csv_row(cells) -> str:
    return ",".join(_csv_cell(c) for c in cells) + "\n"


def ordered_csv(by_group: Dict[str, Dict[str, OrderedLine]]) -> str:
    """Groups in first-seen order (like the web export), header Group..Total."""
    out = _csv_row(["Group", "Material", "Length", "Species", "Qty", "Supply", "Unit Price", "Total"])
    for g, entries in by_group.items():
        for e in entries.values():
            total = e.total()
            out += _csv_row([g, e.material, e.length, e.species, e.qty, e.supply or "",
                             "" if e.unit is None else calc.fixed2(e.unit),
                             "" if total is None else calc.fixed2(total)])
    return out


@dataclass
class DeliveryBar:
    group: str
    delivered: float
    ordered: float
    percent: float        # delivered / ordered, 0-100 (0 when nothing was ordered)


def delivered_vs_ordered(by_group: Dict[str, Dict[str, OrderedLine]], received, database, suppliers,
                         canonical_groups: Iterable[str]) -> List[DeliveryBar]:
    """One bar per canonical GROUP that has an order (like the web Received tab; "(sem grupo)" has no bar)."""
    bars: List[DeliveryBar] = []
    for g in canonical_groups:
        lines = by_group.get(g)
        if lines is None:
            continue
        ordered = calc.ordered_total(lines)
        delivered = calc.delivered_total(g, received, database, suppliers)
        bars.append(DeliveryBar(g, delivered, ordered, calc.delivered_percent(delivered, ordered)))
    return bars


_TONE_BY_ACTION ={"ADDED": "good", "REMOVED": "bad", "CHANGED": "warn"}


def audit_rows(entries) -> List[ReportRow]:
    """Newest first (as stored). Old Qty is a dash for ADDED; the action is colored."""
    return [ReportRow("ITEM", [
        format_timestamp(e.ts), e.action, e.item_key, DASH if e.old_qty is None else str(e.old_qty), str(e.new_qty)],
        tone={0: "muted", 1: _TONE_BY_ACTION.get(e.action, "warn"), 3: "muted"}) for e in entries]


def audit_csv(entries) -> str:
    """Raw ISO timestamps and an empty Old Qty for ADDED, like the web export."""
    out = _csv_row(["Timestamp", "Action", "ItemKey", "Old Qty", "New Qty"])
    for e in entries:
        out += _csv_row([e.ts, e.action, e.item_key, "" if e.old_qty is None else e.old_qty, e.new_qty])
    return out
