"""Workbook section order for take-off lines (the web app walks the sections in this order)."""
from typing import Iterable, List

from .models import TakeoffItem
from .seed import SECTIONS

_ORDER = [s["id"] for s in SECTIONS]


def sort_items(items: Iterable[TakeoffItem]) -> List[TakeoffItem]:
    """Items sorted by section in workbook order, then by row id (unknown sections go first, like Java's indexOf = -1)."""
    def key(t: TakeoffItem):
        idx = _ORDER.index(t.section_id) if t.section_id in _ORDER else -1
        return (idx, t.id or 0)
    return sorted(items, key=key)
