"""Report rows and CSV text (no Qt). The expected CSV lines are the ones the Java SmokeCheck and the web export give."""
import unittest
from datetime import timedelta, timezone

from nlc import calc, reports, seed
from nlc.dao import AuditEntry
from nlc.formatting import DASH, format_timestamp
from nlc.models import MaterialDbEntry, Supplier, TakeoffItem

G1 = "1ST FLOOR - WALL"


def _agg():
    def it(purpose, length, lf, ea, material, species, group=""):
        return TakeoffItem(purpose=purpose, length=length, lf=lf, ea=ea, material=material, species=species, group=group)
    items = [it("Stud", "12'", 24.0, None, "2X4", "DF.No2", G1), it("Stud", "12'", 36.0, None, "2X4", "DF.No2", G1),
             it("Hanger", "", None, 4.0, "HANGER", "HANGERS_CLIPS")]
    db = [MaterialDbEntry(material="2X4", length="12'", species="DF.No2", unit_price_out_tax=10.0, supply="ACME")]
    return calc.aggregate_by_group(items, db, [Supplier(name="ACME", tax=8.25)])


class OrderedRowsTests(unittest.TestCase):
    def test_rows(self):
        rows = reports.ordered_rows(_agg(), seed.GROUPS)
        self.assertEqual([r.kind for r in rows],
                         ["GROUP", "ITEM", "SUBTOTAL", "GROUP", "ITEM", "SUBTOTAL", "GRAND"])
        self.assertEqual(rows[0].cells[0], f"{G1}  (1 item)")
        self.assertEqual(rows[1].cells, ["", "2X4 · 12' · DF.No2", "5", "ACME", "10.82", "$54.13"])
        self.assertEqual(rows[2].cells[0], f"Subtotal — {G1}")
        self.assertEqual(rows[2].cells[5], "$54.13")
        self.assertEqual(rows[3].cells[0], f"{calc.NO_GROUP}  (1 item)")           # no group goes last
        self.assertEqual(rows[4].cells[3:], [DASH, DASH, DASH])                    # not in the Materials DB
        self.assertEqual(rows[5].cells[5], "$0.00")
        self.assertEqual(rows[6].cells[0], "GRAND TOTAL")
        self.assertEqual(rows[6].cells[5], "$54.13")
        self.assertEqual(rows[1].tone, {2: "accent"})

    def test_plural_and_empty(self):
        self.assertEqual(reports.ordered_rows({}, seed.GROUPS), [])
        two = {G1: {"a": calc.OrderedLine("A", "", "", 1), "b": calc.OrderedLine("B", "", "", 1)}}
        self.assertEqual(reports.ordered_rows(two, seed.GROUPS)[0].cells[0], f"{G1}  (2 items)")

    def test_ordered_csv_matches_java_and_web(self):
        lines = reports.ordered_csv(_agg()).split("\n")
        self.assertEqual(lines[0], "Group,Material,Length,Species,Qty,Supply,Unit Price,Total")
        self.assertEqual(lines[1], f"{G1},2X4,12',DF.No2,5,ACME,10.82,54.13")      # same line the Java SmokeCheck checks
        self.assertEqual(lines[2], f"{calc.NO_GROUP},HANGER,,HANGERS_CLIPS,4,,,")

    def test_csv_quotes_commas_and_quotes(self):
        agg = {"G": {"k": calc.OrderedLine('2" x 10\', C CHANNEL', "", "", 1)}}
        self.assertEqual(reports.ordered_csv(agg).split("\n")[1], 'G,"2"" x 10\', C CHANNEL",,,1,,,')


class AuditRowsTests(unittest.TestCase):
    ENTRIES = [AuditEntry(3, "2026-10-16T17:00:00Z", "REMOVED", "gone", 7, 0),
               AuditEntry(2, "2026-10-16T17:00:00Z", "ADDED", "new", None, 4),
               AuditEntry(1, "2026-10-16T16:59:00Z", "CHANGED", "b", 2, 3)]

    def test_rows(self):
        rows = reports.audit_rows(self.ENTRIES)
        self.assertEqual([r.cells[1] for r in rows], ["REMOVED", "ADDED", "CHANGED"])
        self.assertEqual(rows[1].cells[3], DASH)                  # ADDED has no old qty
        self.assertEqual([r.tone[1] for r in rows], ["bad", "good", "warn"])
        self.assertEqual(len(rows[0].cells[0]), 19)               # yyyy-MM-dd HH:mm:ss

    def test_csv_like_the_web(self):
        lines = reports.audit_csv(self.ENTRIES).split("\n")
        self.assertEqual(lines[0], "Timestamp,Action,ItemKey,Old Qty,New Qty")
        self.assertEqual(lines[1], "2026-10-16T17:00:00Z,REMOVED,gone,7,0")
        self.assertEqual(lines[2], "2026-10-16T17:00:00Z,ADDED,new,,4")       # empty old qty

    def test_timestamp_format(self):
        utc = timezone.utc
        self.assertEqual(format_timestamp("2026-10-16T17:36:28.893633100Z", utc), "2026-10-16 17:36:28")
        self.assertEqual(format_timestamp("2026-10-16T17:36:28Z", timezone(timedelta(hours=-3))), "2026-10-16 14:36:28")
        self.assertEqual(format_timestamp("", utc), DASH)
        self.assertEqual(format_timestamp("oops", utc), "oops")


if __name__ == "__main__":
    unittest.main()
