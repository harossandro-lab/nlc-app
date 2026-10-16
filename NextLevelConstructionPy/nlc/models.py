"""Plain data classes, one per table. Field names mirror the Java model classes and the workbook columns."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    id: str
    abbr: str
    name: str
    created_at: str


@dataclass
class ProjectInfo:
    name: str = ""
    jobsite: str = ""
    builder: str = ""
    created_by: str = ""
    arch_date: str = ""
    struct_date: str = ""
    total_sf: str = ""


@dataclass
class Supplier:
    name: str = ""
    tax: float = 0.0          # percent
    delay: int = 0            # days
    id: Optional[int] = None
    project_id: Optional[str] = None


@dataclass
class MaterialDbEntry:
    material: str = ""
    length: str = ""
    species: str = ""
    supply: str = "FACTORY"
    unit_price_out_tax: float = 0.0
    id: Optional[int] = None
    project_id: Optional[str] = None


@dataclass
class TakeoffItem:
    """One take-off line (PURPOSE, PAGE/DETAIL, MATERIAL, LENGTH, SPECIES, LF, SF, SP, EA, LOCATION) plus GROUP and STATUS."""
    purpose: str = ""
    page_detail: str = ""
    material: str = ""
    length: str = ""
    species: str = ""
    lf: Optional[float] = None
    sf: Optional[float] = None
    sp: str = ""
    ea: Optional[float] = None
    group: str = ""
    location: str = "FACTORY"
    status: str = "pending"   # pending | ordered | received
    id: Optional[int] = None
    project_id: Optional[str] = None
    section_id: Optional[str] = None


@dataclass
class ReceivedEntry:
    group: str = ""
    location: str = "FACTORY"
    supply: str = ""
    date: str = ""            # yyyy-MM-dd
    material: str = ""
    length: str = ""
    species: str = ""
    qty: Optional[float] = None
    ticket: str = ""
    invoice: str = ""
    payment: str = ""
    id: Optional[int] = None
    project_id: Optional[str] = None
