"""Report rows and CSV text (no Qt). The expected CSV lines are the ones the Java SmokeCheck and the web export give."""
import unittest
from datetime import timedelta, timezone

from nlc import calc, reports, seed
from nlc.dao import AuditEntry
from nlc.formatting import DASH, format_timestamp
from nlc.models import MaterialDbEntry, ReceivedEntry, Supplier, TakeoffItem

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
        lines = reports.ordered_csv(_agg()).split("\r\n")
        self.assertFalse(reports.ordered_csv(_agg()).endswith("\n"))                # no trailing newline, like the web
        self.assertEqual(lines[0], "Group,Material,Length,Species,Qty,Supply,Unit Price,Total")
        self.assertEqual(lines[1], f"{G1},2X4,12',DF.No2,5,ACME,10.82,54.13")      # same line the Java SmokeCheck checks
        self.assertEqual(lines[2], f"{calc.NO_GROUP},HANGER,,HANGERS_CLIPS,4,,,")

    def test_csv_quotes_commas_and_quotes(self):
        agg = {"G": {"k": calc.OrderedLine('2" x 10\', C CHANNEL', "", "", 1)}}
        self.assertEqual(reports.ordered_csv(agg).split("\r\n")[1], 'G,"2"" x 10\', C CHANNEL",,,1,,,')


class DeliveryBarsTests(unittest.TestCase):
    def test_bars(self):
        db = [MaterialDbEntry(material="2X4", length="12'", species="DF.No2", unit_price_out_tax=10.0, supply="ACME")]
        sup = [Supplier(name="ACME", tax=8.25)]
        recv = [ReceivedEntry(group=G1, material="2x4", length="12'", species="df.no2", qty=2.0),
                ReceivedEntry(group="ROOF", material="2X4", length="12'", species="DF.No2", qty=1.0)]
        bars = reports.delivered_vs_ordered(_agg(), recv, db, sup, seed.GROUPS)
        self.assertEqual([b.group for b in bars], [G1])                    # "(sem grupo)" has no bar
        self.assertAlmostEqual(bars[0].ordered, 54.125, places=9)
        self.assertAlmostEqual(bars[0].delivered, 21.65, places=9)
        self.assertEqual(round(bars[0].percent), 40)

    def test_no_orders_no_bars(self):
        self.assertEqual(reports.delivered_vs_ordered({}, [], [], [], seed.GROUPS), [])


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
        lines = reports.audit_csv(self.ENTRIES).split("\r\n")
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


class DashboardMathTests(unittest.TestCase):
    DB = [MaterialDbEntry(material="2X4", length="12'", species="DF.No2", unit_price_out_tax=10.0, supply="ACME")]
    SUP = [Supplier(name="ACME", tax=10.0)]          # unit price 11.00

    @staticmethod
    def _it(section, lf, status, **kw):
        return TakeoffItem(section_id=section, purpose="Stud", length="12'", lf=lf, material="2X4", species="DF.No2",
                           status=status, **kw)

    def test_percent_rounded_like_javascript(self):
        self.assertEqual(reports.percent_rounded(1, 3), 33)
        self.assertEqual(reports.percent_rounded(1, 8), 13)       # 12.5 -> 13 (Math.round goes up; Python round() would give 12)
        self.assertEqual(reports.percent_rounded(5, 0), 0)

    def test_totals_by_status(self):
        items = [self._it("roof", 24.0, "pending"), self._it("roof", 24.0, "ordered"), self._it("roof", 24.0, "received"),
                 TakeoffItem(section_id="roof", purpose="note")]              # no price and no QTY: counted, not valued
        t = reports.totals_of(items, self.DB, self.SUP)
        self.assertEqual(t.count, 4)
        self.assertAlmostEqual(t.total, 66.0, places=9)                       # 3 priced lines x 2 x 11.00
        self.assertAlmostEqual(t.ordered, 22.0, places=9)
        self.assertAlmostEqual(t.received, 22.0, places=9)

    def test_section_totals_follow_the_workbook_order_and_sum_to_the_grand_total(self):
        items = [self._it("windows", 12.0, "pending"), self._it("roof", 24.0, "ordered"),
                 self._it("not-a-section", 12.0, "pending")]                  # ignored, like the web
        per, grand = reports.section_totals(items, self.DB, self.SUP, seed.SECTIONS)
        self.assertEqual([s["id"] for s, _ in per], [s["id"] for s in seed.SECTIONS])
        by_id = {s["id"]: t for s, t in per}
        self.assertEqual((by_id["roof"].count, by_id["windows"].count), (1, 1))
        self.assertAlmostEqual(grand.total, 33.0, places=9)
        self.assertEqual(grand.count, 2)

    def test_all_items_csv_like_the_web(self):
        a = self._it("windows", 12.0, "received", id=2, group="WINDOWS", page_detail="A-1")
        b = TakeoffItem(section_id="roof", id=1, purpose='Fascia, 2" x 6"', material="2X4", species="DF.No2",
                        length="12'", ea=3.5, location="FIELD")
        rows = reports.all_items_csv([b, a, self._it("zzz", 1.0, "pending")], self.DB, self.SUP, seed.SECTIONS).split("\r\n")
        self.assertEqual(rows[0], "Section,Group,Purpose,Page/Detail,Material,Length,Species,LF,SF,SP,EA,QTY,Location,"
                                  "ItemKey,Unit Price,Total,Status")
        self.assertEqual(len(rows), 3)                                          # header + 2 lines (unknown section left out)
        self.assertEqual(rows[1], 'Roof,,"Fascia, 2"" x 6""",,2X4,12\',DF.No2,,,,3.5,4,FIELD,2X4|12\'|DF.No2,11.00,44.00,pending')
        self.assertEqual(rows[2], "Windows & Doors,WINDOWS,Stud,A-1,2X4,12',DF.No2,12,,,,1,FACTORY,2X4|12'|DF.No2,11.00,11.00,received")
