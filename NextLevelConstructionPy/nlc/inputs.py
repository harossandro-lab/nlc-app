"""Reading what the user types into number cells (no Qt)."""
import math
import re
from datetime import date
from typing import Optional, Tuple


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


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)


def parse_date(text: str) -> Optional[str]:
    """A date typed as yyyy-MM-dd (what the web date input stores). Blank is allowed and means "no date";
    anything that is not a real calendar date returns None so the edit is ignored."""
    s = (text or "").strip()
    if not s:
        return ""
    if not _DATE.match(s):
        return None
    try:
        date.fromisoformat(s)
    except ValueError:
        return None
    return s


def parse_optional_number(text: str) -> Tuple[bool, Optional[float]]:
    """(accepted, value) for a number that may stay empty (Received qty): blank gives (True, None)."""
    if not (text or "").strip():
        return True, None
    v = parse_number(text)
    return (False, None) if v is None else (True, v)


def parse_whole_number(text: str) -> Optional[int]:
    """Whole number (days). A decimal such as 1.5 is cut to 1; None for text that is not a number."""
    v = parse_number(text)
    return None if v is None else int(v)
