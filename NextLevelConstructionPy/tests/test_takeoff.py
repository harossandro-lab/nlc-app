"""Take-off section rules that do not need Qt."""
import unittest

from nlc import seed, takeoff
from nlc.models import MaterialDbEntry, Supplier, TakeoffItem


def item(**kw):
    base = dict(section_id="roof", purpose="Stud", length="12'", lf=24.0, material="2X4", species="DF.No2")
    base.update(kw)
    return TakeoffItem(**base)


class StatusTests(unittest.TestCase):
    def test_cycle(self):
        self.assertEqual(takeoff.next_status("pending"), "ordered")
        self.assertEqual(takeoff.next_status("ordered"), "received")
        self.assertEqual(takeoff.next_status("received"), "pending")
        self.assertEqual(takeoff.next_status(None), "ordered")       # unknown counts as pending
        self.assertEqual(takeoff.next_status("weird"), "ordered")

    def test_key_and_label(self):
        self.assertEqual(takeoff.status_key("weird"), "pending")
        self.assertEqual(takeoff.STATUS_LABEL[takeoff.status_key(None)], "Pending")
        self.assertEqual(takeoff.STATUS_LABEL["received"], "Received")


class NumberTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(takeoff.parse_takeoff_number("24"), (True, 24.0))
        self.assertEqual(takeoff.parse_takeoff_number("7,5"), (True, 7.5))        # decimal comma
        self.assertEqual(takeoff.parse_takeoff_number(" 7.5 "), (True, 7.5))
        self.assertEqual(takeoff.parse_takeoff_number(""), (True, None))          # blank stays empty
        self.assertEqual(takeoff.parse_takeoff_number("0"), (True, 0.0))

    def test_rejected(self):
        for text in ("abc", "12abc", "1,000.5", "1,2,3", "NaN", "1_0"):
            self.assertEqual(takeoff.parse_takeoff_number(text), (False, None), text)


class SectionDefaultsTests(unittest.TestCase):
    def test_new_item_uses_the_default_group_of_each_section(self):
        for sec in seed.SECTIONS:
            it = takeoff.new_item("p1", sec["id"])
            self.assertEqual(it.group, seed.DEFAULT_GROUP.get(sec["id"], ""))
            self.assertEqual((it.location, it.status, it.section_id, it.project_id), ("FACTORY", "pending", sec["id"], "p1"))
        self.assertEqual(takeoff.new_item("p", "sub-floor").group, "SUB-LOOR - WALL")
        self.assertEqual(takeoff.new_item("p", "flush-beam").group, "")
        self.assertEqual(takeoff.new_item("p", "balcony").group, "BALCONY - FRONT  ELEVATION")

    def test_every_default_group_is_a_real_group(self):
        for g in seed.DEFAULT_GROUP.values():
            self.assertTrue(g == "" or g in seed.GROUPS, g)

    def test_sp_options_have_the_spacings_and_the_plies(self):
        self.assertEqual(takeoff.SP_OPTIONS, seed.SPACINGS + ["2 Ply", "3 Ply"])


class TextTests(unittest.TestCase):
    DB = [MaterialDbEntry(material="2X4", length="12'", species="DF.No2", unit_price_out_tax=10.0, supply="ACME")]
    SUP = [Supplier(name="ACME", tax=10.0)]

    def test_computed_cells(self):
        it = item()
        self.assertEqual(takeoff.qty_text(it), "2")
        self.assertEqual(takeoff.unit_text(it, self.DB, self.SUP), "11.00")
        self.assertEqual(takeoff.total_text(it, self.DB, self.SUP), "$22.00")

    def test_dash_when_not_computable(self):
        it = item(lf=None, length="")
        self.assertEqual(takeoff.qty_text(it), "—")
        self.assertEqual(takeoff.total_text(item(material="NOPE"), self.DB, self.SUP), "—")
        self.assertEqual(takeoff.unit_text(item(material="NOPE"), self.DB, self.SUP), "—")

    def test_search_text_covers_the_columns_the_web_searches(self):
        it = item(group="ROOF", page_detail="A-101", location="FIELD")
        for word in ("roof", "stud", "a-101", "2x4", "12'", "df.no2", "field"):
            self.assertIn(word, takeoff.search_text(it).lower())

    def test_subtitle_like_the_web(self):
        self.assertEqual(takeoff.section_subtitle(3, 1234.5), "3 line item(s) · estimated $1,234.50")

    def test_section_csv(self):
        lines = takeoff.section_csv([item(group="ROOF")], self.DB, self.SUP).split("\r\n")
        self.assertEqual(lines[0], "Group,Purpose,Page/Detail,Material,Length,Species,LF,SF,SP,EA,QTY,Location,ItemKey,"
                                   "Unit Price,Total,Status")
        self.assertEqual(lines[1], "ROOF,Stud,,2X4,12',DF.No2,24,,,,2,FACTORY,2X4|12'|DF.No2,11.00,22.00,pending")
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
