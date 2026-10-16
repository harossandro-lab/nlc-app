"""The circles of the project menu, in spreadsheet order (same list and abbreviations as the Java ProjectMenuPanel
and the web app's TAB_CIRCLES). No Qt here, so it can be tested without a display."""
from typing import List, Tuple

from .seed import SECTIONS

TILES: List[Tuple[str, str]] = (
    [("dashboard", "Dashboard")]
    + [(s["id"], s["label"]) for s in SECTIONS]
    + [("ordered", "Ordered (auto)"), ("received", "Received"), ("audit", "Audit Log"),
       ("database", "Materials DB"), ("suppliers", "Suppliers & Tax")]
)

ABBREVIATIONS = {
    "Dashboard": "DASH", "Sub-Floor": "SF",
    "1st Floor Walls": "1W", "2nd Floor Walls": "2W", "3rd Floor Walls": "3W",
    "4th Floor Walls": "4W", "5th Floor Walls": "5W", "6th Floor Walls": "6W",
    "Roof": "RF", "Flush Beam": "FB", "Shaft Wall": "SW", "Stair Tower": "ST", "Balcony": "BAL",
    "Windows & Doors": "WIN", "Ordered (auto)": "ORD", "Received": "RCV", "Audit Log": "AUD",
    "Materials DB": "DB", "Suppliers & Tax": "TAX",
}

SECTION_IDS = [s["id"] for s in SECTIONS]


def abbreviate(label: str) -> str:
    """Circle text for a tile; unknown labels fall back to the initials of their words."""
    if label in ABBREVIATIONS:
        return ABBREVIATIONS[label]
    initials = "".join(w[0].upper() for w in label.split(" ") if w)
    return initials or label
