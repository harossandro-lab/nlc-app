"""Reading what the user types into number cells (no Qt)."""
import math
from typing import Optional


def parse_number(text: str) -> Optional[float]:
    """Number typed in a cell. Blank means 0 (the web app's `parseFloat(value) || 0`); text that is not a plain
    number returns None so the caller can ignore the edit instead of storing garbage."""
    s = (text or "").strip()
    if not s:
        return 0.0
    try:
        v = float(s)
    except ValueError:
        return None
    if "_" in s or math.isnan(v) or math.isinf(v):
        return None
    return v


def parse_whole_number(text: str) -> Optional[int]:
    """Whole number (days). A decimal such as 1.5 is cut to 1; None for text that is not a number."""
    v = parse_number(text)
    return None if v is None else int(v)
