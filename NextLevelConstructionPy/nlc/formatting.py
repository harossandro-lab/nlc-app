"""Display formatting shared by the screens (no Qt)."""
import re
from datetime import datetime, timezone, tzinfo
from typing import Optional

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_FRACTION = re.compile(r"(\.\d{6})\d+")
DASH = "—"


def format_created(iso: Optional[str], zone: Optional[tzinfo] = None) -> str:
    """"Oct 16, 2026" like the web app's fmtDate. Blank gives a dash; text that is not a date is shown as is.

    Accepts the timestamps both apps write (Java Instant.toString has up to 9 fraction digits, JavaScript 3, Python 6).
    `zone` defaults to the computer's local time zone.
    """
    if not iso:
        return DASH
    try:
        dt = datetime.fromisoformat(_FRACTION.sub(r"\1", iso.strip()).replace("Z", "+00:00"))
    except ValueError:
        return iso
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(zone) if zone is not None else dt.astimezone()
    return f"{_MONTHS[dt.month - 1]} {dt.day}, {dt.year}"
