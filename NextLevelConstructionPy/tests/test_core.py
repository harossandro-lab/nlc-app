"""Core regression tests, mirroring the Java SmokeCheck (same inputs, same expected values).

Run from NextLevelConstructionPy/:  python -m unittest discover -s tests -v
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from nlc import audit, calc, db, seed
from nlc.dao import (AuditDao, MaterialDbDao, ProjectDao, ReceivedDao, SupplierDao, TakeoffItemDao)
from nlc.models import MaterialDbEntry, ReceivedEntry, Supplier, TakeoffItem
from nlc.section_order import sort_items


def it(purpose, length, lf, sf, sp, ea, material="", species="", group="", section_id=None):
    return TakeoffItem(purpose=purpose, length=length, lf=lf, sf=sf, sp=sp, ea=ea,
                       material=material, species=species, group=group, section_id=section_id)


class SeedTests(unittest.TestCase):
    def test_lists(self):
        self.assertEqual(len(seed.GROUPS), 43)
        self.assertIn("SUB-LOOR - WALL", seed.GROUPS)               # original workbook typo is kept
        self.assertIn("BALCONY - FRONT  ELEVATION", seed.GROUPS)    # double space is kept
        self.assertEqual(len(seed.SECTIONS), 13)
        self.assertEqual(len(seed.SPECIES), 25)
        self.assertEqual(seed.LOCATIONS, ["FACTORY", "FIELD"])
        self.assertEqual(seed.SPACINGS, ["10'", '12"', '16"', '24"', '32"', "4'", "6'", "8'", '8"'])
        self.assertEqual(len(seed.materials_for_species("DF.No2")), 7)
        self.assertEqual(len(seed.materials_for_species("LVL")), 90)
        self.assertEqual(seed.materials_for_species("lvl"), seed.materials_for_species("LVL"))
        self.assertEqual(seed.materials_for_species(None), [])

    def test_default_group(self):
        self.assertEqual(seed.DEFAULT_GROUP["sub-floor"], "SUB-LOOR - WALL")
        self.assertEqual(seed.DEFAULT_GROUP["balcony"], "BALCONY - FRONT  ELEVATION")
        self.assertEqual(seed.DEFAULT_GROUP["flush-beam"], "")


class QtyTests(unittest.TestCase):
    def test_rules(self):
        q = calc.compute_qty
        self.assertEqual(q(it("Stud", "8'", 100.0, None, "", None)), 13)            # 100/8 = 12.5 -> 13
        self.assertEqual(q(it("Stud", "8'", 100.0, None, '16"', None)), 75)          # 100*12/16
        self.assertEqual(q(it("Stud", "8'", 10.0, None, '16"', 2.0)), 15)            # 7.5 * 2
        self.assertEqual(q(it("End Studs", "8'", 100.0, None, "", None)), 17)        # 100*2/12 = 16.7
        self.assertEqual(q(it("Header", "16'", 30.0, None, "2 Ply", None)), 4)       # 2*30/16 = 3.75
        self.assertEqual(q(it("Header", "", None, None, "3 Ply", 3.0)), 9)
        self.assertEqual(q(it("Floor Sheathing", "32SF", None, 650.0, "", None)), 21)
        self.assertEqual(q(it("Roof Sheathing", "32SF", None, 650.0, "", None)), 22)  # 20.3125 * 1.05
        self.assertEqual(q(it("Hanger", "", None, None, "", 7.0)), 7)
        self.assertIsNone(q(it("Stud", "N/A", 10.0, None, "", None)))

    def test_java_like_edge_cases(self):
        # length 0: Java divides by zero without an error and (int) Math.ceil(Infinity) saturates
        self.assertEqual(calc.compute_qty(it("Stud", "0'", 10.0, None, "", None)), calc.JAVA_INT_MAX)
        self.assertEqual(calc.compute_qty(it("Stud", "0'", 0.0, None, "", 5.0)), 5)

    def test_parse_length(self):
        self.assertEqual(calc.parse_length('104 5/8"'), 104.625)
        self.assertIsNone(calc.parse_length("N/A"))
        self.assertEqual(calc.parse_length("32SF"), 32.0)
        self.assertEqual(calc.parse_length("10'"), 10.0)
        self.assertIsNone(calc.parse_length(""))
        self.assertIsNone(calc.parse_length(None))
        self.assertIsNone(calc.parse_length("abc"))

    def test_parse_spacing_and_ply(self):
        p = calc.parse_spacing_and_ply
        self.assertEqual(p("16").spacing, 16.0)
        self.assertEqual(p('16"').spacing, 16.0)
        self.assertEqual(p("4'").spacing, 48.0)
        self.assertEqual(p("2 Ply").ply, 2.0)
        self.assertIsNone(p("2 Ply").spacing)

    def test_item_key(self):
        self.assertEqual(calc.build_item_key("2X4", "12'", "DF.No2"), "2X4|12'|DF.No2")
        self.assertEqual(calc.build_item_key("HANGER", "N/A", "HANGERS_CLIPS"), "HANGER|HANGERS_CLIPS")
        self.assertEqual(calc.item_key_of(it("x", "12'", None, None, "", None, material="2X4", species="DF.No2")), "2x4|12'|df.no2")

    def test_price(self):
        d = MaterialDbEntry(unit_price_out_tax=10.0, supply="ACME")
        s = Supplier(name="acme", tax=8.25)
        self.assertAlmostEqual(calc.unit_price_of(d, [s]), 10.825, places=9)
        self.assertEqual(calc.tax_for_supply([s], None), 0.0)


class FormatTests(unittest.TestCase):
    def test_matches_javascript(self):
        # reference values taken from Node: (10.825).toFixed(2) etc.
        self.assertEqual(calc.fixed2(10.825), "10.82")
        self.assertEqual(calc.fixed2(10.825 * 5), "54.13")
        self.assertEqual(calc.fixed2(54.125), "54.13")
        self.assertEqual(calc.fixed2(0.005), "0.01")
        self.assertEqual(calc.fixed2(1.005), "1.00")
        self.assertEqual(calc.money(1234.5), "$1,234.50")
        self.assertEqual(calc.money(0), "$0.00")


G1 = "1ST FLOOR - WALL"


def _ordered_fixture():
    o1 = it("Stud", "12'", 24.0, None, "", None, material="2X4", species="DF.No2", group=G1)    # 2
    o2 = it("Stud", "12'", 36.0, None, "", None, material="2X4", species="DF.No2", group=G1)    # 3
    o3 = it("Hanger", "", None, None, "", 4.0, material="HANGER", species="HANGERS_CLIPS")       # no group, not in DB
    o4 = it("Stud", "12'", None, None, "", None, material="2X6", species="DF.No2", group=G1)    # no QTY
    o5 = it("Note", "", None, None, "", 3.0, group=G1)                                          # empty ItemKey
    od = MaterialDbEntry(material="2X4", length="12'", species="DF.No2", unit_price_out_tax=10.0, supply="ACME")
    os_ = Supplier(name="ACME", tax=8.25)
    return [o1, o2, o3, o4, o5], [od], [os_]


class OrderedTests(unittest.TestCase):
    def test_aggregate(self):
        items, database, suppliers = _ordered_fixture()
        agg = calc.aggregate_by_group(items, database, suppliers)
        line = agg[G1]["2x4|12'|df.no2"]
        self.assertEqual(line.qty, 5)
        self.assertAlmostEqual(line.unit, 10.825, places=9)
        self.assertAlmostEqual(line.total(), 54.125, places=9)
        self.assertEqual(line.supply, "ACME")
        self.assertIn(calc.NO_GROUP, agg)
        self.assertIsNone(agg[calc.NO_GROUP]["hanger|hangers_clips"].unit)
        self.assertEqual(len(agg[G1]), 1)
        self.assertEqual(calc.group_display_order([calc.NO_GROUP, G1], seed.GROUPS), [G1, calc.NO_GROUP])


class ReceivedMathTests(unittest.TestCase):
    def test_delivered_vs_ordered(self):
        items, database, suppliers = _ordered_fixture()
        agg = calc.aggregate_by_group(items, database, suppliers)
        r1 = ReceivedEntry(group=G1, material="2x4", length="12'", species="df.no2", qty=2.0)   # key ignores case
        r2 = ReceivedEntry(group=G1, material="2X6", species="DF.No2", qty=9.0)                  # not in DB
        r3 = ReceivedEntry(group="ROOF", material="2X4", length="12'", species="DF.No2", qty=1.0)
        self.assertAlmostEqual(calc.received_line_total(r1, database, suppliers), 21.65, places=9)
        self.assertIsNone(calc.received_line_total(r2, database, suppliers))
        r1.qty = None
        self.assertEqual(calc.received_line_total(r1, database, suppliers), 0.0)
        r1.qty = 2.0
        self.assertAlmostEqual(calc.delivered_total(G1, [r1, r2, r3], database, suppliers), 21.65, places=9)
        self.assertAlmostEqual(calc.ordered_total(agg[G1]), 54.125, places=9)
        self.assertEqual(round(calc.delivered_percent(21.65, 54.125)), 40)
        self.assertEqual(calc.delivered_percent(80.0, 54.125), 100.0)
        self.assertEqual(calc.delivered_percent(5.0, 0.0), 0.0)


class AuditMathTests(unittest.TestCase):
    def test_diff(self):
        diffs = calc.audit_diff({"a": 5, "b": 2, "gone": 7}, {"a": 5, "b": 3, "new": 4})
        self.assertEqual([(d.action, d.item_key, d.old_qty, d.new_qty) for d in diffs],
                         [("CHANGED", "b", 2, 3), ("ADDED", "new", None, 4), ("REMOVED", "gone", 7, 0)])

    def test_totals(self):
        items, _, _ = _ordered_fixture()
        self.assertEqual(calc.totals_by_item_key(items), {"2x4|12'|df.no2": 5, "hanger|hangers_clips": 4})


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = db.connect(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_tables_exist(self):
        names = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ("projects", "project_info", "suppliers", "materials_db", "takeoff_items", "received_log",
                  "audit_log", "audit_snapshot"):
            self.assertIn(t, names)

    def test_project_create_and_cascade(self):
        pd = ProjectDao(self.conn)
        p = pd.create("avn", "AVENEL")
        self.assertEqual(p.abbr, "AVN")
        self.assertEqual(pd.create("toolong", "x").abbr, "TOOLO")
        self.assertEqual(pd.create("", "").abbr, "JOB")
        self.assertEqual([s.name for s in SupplierDao(self.conn).find_by_project(p.id)], ["FACTORY", "FIELD"])
        self.assertEqual(pd.get_info(p.id).name, "AVENEL")
        TakeoffItemDao(self.conn).insert(TakeoffItem(project_id=p.id, section_id="roof"))
        ReceivedDao(self.conn).insert(ReceivedEntry(project_id=p.id))
        pd.rename(p.id, "AV", "Avenel II")
        self.assertEqual(next(x for x in pd.find_all() if x.id == p.id).name, "Avenel II")
        pd.delete(p.id)
        self.assertEqual(TakeoffItemDao(self.conn).find_by_project(p.id), [])
        self.assertEqual(ReceivedDao(self.conn).find_by_project(p.id), [])
        self.assertEqual(SupplierDao(self.conn).find_by_project(p.id), [])

    def test_takeoff_and_materials_round_trip(self):
        p = ProjectDao(self.conn).create("T", "Test")
        td = TakeoffItemDao(self.conn)
        a = td.insert(TakeoffItem(project_id=p.id, section_id="roof", material="2X4", lf=24.0))
        td.insert(TakeoffItem(project_id=p.id, section_id="sub-floor"))
        a.sp = "16"; a.ea = None; td.update(a)
        got = td.find_by_section(p.id, "roof")
        self.assertEqual((got[0].sp, got[0].lf, got[0].ea), ("16", 24.0, None))
        self.assertEqual(len(td.find_by_project(p.id)), 2)
        td.delete(a.id)
        self.assertEqual(td.find_by_section(p.id, "roof"), [])
        md = MaterialDbDao(self.conn)
        d = md.insert(MaterialDbEntry(project_id=p.id, material="2X4", unit_price_out_tax=3.5))
        d.unit_price_out_tax = 4.0; md.update(d)
        self.assertEqual(md.find_by_project(p.id)[0].unit_price_out_tax, 4.0)
        md.delete(d.id)
        self.assertEqual(md.find_by_project(p.id), [])

    def test_received_dao(self):
        p = ProjectDao(self.conn).create("R", "Rcv")
        rd = ReceivedDao(self.conn)
        rd.insert(ReceivedEntry(project_id=p.id, group=G1, ticket="T-1", qty=4.0))
        rd.insert(ReceivedEntry(project_id=p.id, ticket="T-2"))
        rows = rd.find_by_project(p.id)
        self.assertEqual(rows[0].ticket, "T-2")            # newest first
        self.assertIsNone(rows[0].qty)
        self.assertEqual(rows[1].qty, 4.0)
        rows[1].payment = "Paid"; rows[1].date = "2026-10-16"; rd.update(rows[1])
        again = rd.find_by_project(p.id)[1]
        self.assertEqual((again.payment, again.date), ("Paid", "2026-10-16"))
        rd.delete(rows[0].id)
        self.assertEqual(len(rd.find_by_project(p.id)), 1)

    def test_section_order(self):
        items = [TakeoffItem(section_id="windows", id=1), TakeoffItem(section_id="roof", id=5),
                 TakeoffItem(section_id="sub-floor", id=9), TakeoffItem(section_id="roof", id=2)]
        self.assertEqual([(t.section_id, t.id) for t in sort_items(items)],
                         [("sub-floor", 9), ("roof", 2), ("roof", 5), ("windows", 1)])

    def test_audit_service(self):
        p = ProjectDao(self.conn).create("A", "Audit")
        td, ad = TakeoffItemDao(self.conn), AuditDao(self.conn)
        i1 = td.insert(TakeoffItem(project_id=p.id, section_id="roof", purpose="Stud", length="12'", lf=24.0,
                                   material="2X4", species="DF.No2"))                      # qty 2
        audit.ensure_baseline(self.conn, p.id)
        self.assertEqual(ad.count_log(p.id), 0)                                            # baseline makes no entries
        self.assertEqual(ad.get_snapshot(p.id), {"2x4|12'|df.no2": 2})
        self.assertEqual(audit.run_diff(self.conn, p.id), 0)
        i1.lf = 36.0; td.update(i1)                                                        # qty 3
        i2 = td.insert(TakeoffItem(project_id=p.id, section_id="roof", purpose="Hanger", ea=4.0,
                                   material="HANGER", species="HANGERS_CLIPS"))
        self.assertEqual(audit.run_diff(self.conn, p.id), 2)
        log = ad.find_log(p.id)
        self.assertEqual((log[0].action, log[0].old_qty, log[0].new_qty), ("CHANGED", 2, 3))   # first change on top
        self.assertEqual((log[1].action, log[1].old_qty), ("ADDED", None))
        td.delete(i2.id)
        audit.run_diff(self.conn, p.id)
        top = ad.find_log(p.id)[0]
        self.assertEqual((top.action, top.new_qty), ("REMOVED", 0))
        self.assertEqual(audit.run_diff(self.conn, p.id), 0)
        audit.ensure_baseline(self.conn, p.id)                                             # skipped: a log exists
        many = [calc.AuditChange("ADDED", f"k{i}", None, 1) for i in range(450)]
        ad.save_run(p.id, "2026-10-16T00:00:00Z", many, {"2x4|12'|df.no2": 3})
        self.assertEqual(ad.count_log(p.id), 400)                                          # trimmed to the last 400
        self.assertEqual(ad.find_log(p.id)[0].item_key, "k0")

    def test_default_path_follows_environment(self):
        old = os.environ.get("NLC_DB")
        os.environ["NLC_DB"] = str(Path(self.tmp.name) / "x.db")
        try:
            self.assertEqual(db.default_path(), Path(self.tmp.name) / "x.db")
        finally:
            if old is None:
                del os.environ["NLC_DB"]
            else:
                os.environ["NLC_DB"] = old


if __name__ == "__main__":
    unittest.main()
