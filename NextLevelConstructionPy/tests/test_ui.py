"""UI flow tests, run without a display (Qt "offscreen" platform). Skipped when PySide6 is not installed.

Use the virtual environment:  .venv\\Scripts\\python -m unittest discover -s tests -t .
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    Qt_ItemIsEditable = Qt.ItemIsEditable
    HAVE_QT = True
except ImportError:  # pragma: no cover
    HAVE_QT = False

from nlc import db
from nlc.dao import AuditDao, ProjectDao, TakeoffItemDao
from nlc.models import TakeoffItem


@unittest.skipUnless(HAVE_QT, "PySide6 is not installed")
class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from nlc.ui import theme
        cls.app.setStyleSheet(theme.STYLE_SHEET)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = db.connect(Path(self.tmp.name) / "ui.db")
        self.dao = ProjectDao(self.conn)
        self.avn = self.dao.create("AVN", "AVENEL")
        from nlc.ui.main_window import MainWindow
        self.win = MainWindow(self.conn)

    def tearDown(self):
        self.win.close()
        self.conn.close()
        self.tmp.cleanup()

    def _captions(self):
        return [t.caption for t in self.win.stack.currentWidget().grid.tiles()]

    def test_home_shows_new_job_then_one_circle_per_job(self):
        self.assertEqual(self.win.current_level, "home")
        self.assertEqual(self._captions(), ["New Job", "AVENEL"])

    def test_open_job_shows_the_19_circles(self):
        self.win.open_project(self.avn)
        self.assertEqual(self.win.current_level, "project-menu")
        self.assertEqual(self.win.back_link.text(), "← All Jobs")
        caps = self._captions()
        self.assertEqual(len(caps), 19)
        self.assertEqual(caps[0], "Dashboard")
        self.assertEqual(caps[-2:], ["Materials DB", "Suppliers & Tax"])

    def test_back_goes_up_exactly_one_level(self):
        self.win.open_project(self.avn)
        self.win.open_tile("roof")
        self.assertEqual((self.win.current_level, self.win.back_link.text()), ("screen", "← AVENEL"))
        self.win.go_back_one_level()
        self.assertEqual(self.win.current_level, "project-menu")
        self.win.go_back_one_level()
        self.assertEqual(self.win.current_level, "home")
        self.assertEqual(self.win.back_link.text(), "")

    def test_old_panels_are_dropped(self):
        for _ in range(3):
            self.win.open_project(self.avn)
            self.win.open_tile("roof")
            self.win.go_back_one_level()
            self.win.go_back_one_level()
        self.assertEqual(self.win.stack.count(), 1)

    def test_new_job_is_created_and_opened(self):
        home = self.win.stack.currentWidget()
        self.assertIsNone(home.create_job("", "  "))                    # blank does nothing
        p = home.create_job("nyd", "New York Developers")
        self.assertEqual((p.abbr, p.name), ("NYD", "New York Developers"))
        self.assertEqual(self.win.current_level, "project-menu")
        self.assertEqual(len(self.dao.find_all()), 2)

    def test_opening_a_job_stores_the_audit_baseline(self):
        TakeoffItemDao(self.conn).insert(TakeoffItem(project_id=self.avn.id, section_id="roof", purpose="Stud",
                                                     length="12'", lf=24.0, material="2X4", species="DF.No2"))
        self.win.open_project(self.avn)
        self.assertEqual(AuditDao(self.conn).get_snapshot(self.avn.id), {"2x4|12'|df.no2": 2})
        self.assertEqual(AuditDao(self.conn).count_log(self.avn.id), 0)

    def test_lista_has_one_row_per_job_and_opens_the_job(self):
        self.dao.create("NYD", "New York Developers")
        self.win.show_list()
        panel = self.win.stack.currentWidget()
        self.assertEqual([r.name.text() for r in panel.rows], ["AVENEL", "New York Developers"])
        self.assertEqual([r.badge.text() for r in panel.rows], ["AVN", "NYD"])
        self.assertTrue(panel.rows[0].meta.text().startswith("Criado em "))
        self.assertEqual((self.win.current_level, self.win.back_link.text()), ("home", ""))
        panel.rows[1].clicked.emit()
        self.assertEqual((self.win.current_level, self.win.current_project.abbr), ("project-menu", "NYD"))
        self.assertEqual(self.win.stack.count(), 1)

    def test_lista_without_jobs_shows_a_hint(self):
        for p in self.dao.find_all():
            self.dao.delete(p.id)
        self.win.show_list()
        self.assertEqual(self.win.stack.currentWidget().rows, [])

    def _add_stud(self, lf, group="1ST FLOOR - WALL"):
        return TakeoffItemDao(self.conn).insert(TakeoffItem(
            project_id=self.avn.id, section_id="1st-walls", purpose="Stud", length="12'", lf=lf, material="2X4",
            species="DF.No2", group=group))

    def test_ordered_screen_sums_by_group_and_exports_csv(self):
        from nlc.dao import MaterialDbDao
        from nlc.models import MaterialDbEntry
        MaterialDbDao(self.conn).insert(MaterialDbEntry(project_id=self.avn.id, material="2X4", length="12'",
                                                        species="DF.No2", unit_price_out_tax=10.0, supply="FACTORY"))
        self._add_stud(24.0)     # 2
        self._add_stud(36.0)     # 3
        self.win.open_project(self.avn)
        self.win.open_tile("ordered")
        panel = self.win.stack.currentWidget()
        self.assertEqual([r.kind for r in panel.rows], ["GROUP", "ITEM", "SUBTOTAL", "GRAND"])
        self.assertEqual(panel.rows[1].cells[2], "5")
        self.assertEqual(panel.rows[3].cells[5], "$50.00")
        self.assertEqual(panel.table.columnSpan(0, 0), 6)           # group header runs across the row
        self.assertEqual(panel.table.columnSpan(2, 0), 5)           # subtotal label runs up to the total column
        self.assertIsNone(panel.empty_label)
        self.assertEqual(panel.csv_text().split("\r\n")[1], "1ST FLOOR - WALL,2X4,12',DF.No2,5,FACTORY,10.00,50.00")

    def test_ordered_screen_without_items_shows_the_hint(self):
        self.win.open_project(self.avn)
        self.win.open_tile("ordered")
        panel = self.win.stack.currentWidget()
        self.assertEqual(panel.rows, [])
        self.assertIn("Nenhum item", panel.empty_label.text())

    def test_audit_screen_lists_changes_newest_first(self):
        item = self._add_stud(24.0)
        self.win.open_project(self.avn)                              # baseline: qty 2, no entries
        item.lf = 36.0
        TakeoffItemDao(self.conn).update(item)                       # qty 3, not compared yet
        self.win.open_tile("audit")                                  # opening the screen catches up
        panel = self.win.stack.currentWidget()
        self.assertEqual([r.cells[1:] for r in panel.rows], [["CHANGED", "2x4|12'|df.no2", "2", "3"]])
        self.assertEqual(panel.rows[0].tone[1], "warn")

    def test_audit_screen_empty_hint(self):
        self.win.open_project(self.avn)
        self.win.open_tile("audit")
        self.assertIn("Nenhuma mudança", self.win.stack.currentWidget().empty_label.text())

    def test_export_csv_writes_the_file_and_cancel_does_nothing(self):
        from unittest import mock
        self._add_stud(24.0)
        self.win.open_project(self.avn)
        self.win.open_tile("ordered")
        panel = self.win.stack.currentWidget()
        target = Path(self.tmp.name) / "out.csv"
        with mock.patch("nlc.ui.report_table.QFileDialog.getSaveFileName", return_value=(str(target), "CSV (*.csv)")):
            self.assertTrue(panel.export_csv())
        self.assertEqual(target.read_bytes().decode("utf-8-sig"), panel.csv_text())    # raw bytes: CRLF must stay CRLF
        self.assertEqual(target.read_bytes()[:3], bytes([0xEF, 0xBB, 0xBF]))      # BOM, like the web download
        self.assertTrue(target.read_bytes().decode("utf-8-sig").startswith("Group,Material,Length,Species,Qty,"))
        other = Path(self.tmp.name) / "none.csv"
        with mock.patch("nlc.ui.report_table.QFileDialog.getSaveFileName", return_value=("", "")):
            self.assertFalse(panel.export_csv())
        self.assertFalse(other.exists())

    # ---- Suppliers & Tax and Materials DB ----
    def _open(self, tile_id):
        self.win.open_project(self.avn)
        self.win.open_tile(tile_id)
        return self.win.stack.currentWidget()

    @staticmethod
    def _set(panel, row, col, text):
        return panel.model.setData(panel.model.index(row, col), text)

    def test_suppliers_screen_shows_the_default_suppliers(self):
        panel = self._open("suppliers")
        m = panel.model
        self.assertEqual([m.index(r, 0).data() for r in range(m.rowCount())], ["FACTORY", "FIELD"])
        self.assertEqual([m.headerData(c, Qt.Horizontal) for c in range(m.columnCount())],
                         ["Supply (name)", "Tax %", "Delay (days)", ""])
        self.assertEqual(m.index(0, 1).data(), "0")

    def test_suppliers_edit_is_saved_and_text_in_a_number_cell_is_rejected(self):
        from nlc.dao import SupplierDao
        panel = self._open("suppliers")
        self.assertTrue(self._set(panel, 0, 1, "8.25"))
        self.assertTrue(self._set(panel, 0, 2, "3.7"))
        self.assertFalse(self._set(panel, 0, 1, "abc"))                  # rejected: the old value stays
        self.assertEqual(panel.model.index(0, 1).data(), "8.25")
        self.assertTrue(self._set(panel, 1, 0, "  YARD  "))
        saved = SupplierDao(self.conn).find_by_project(self.avn.id)
        self.assertEqual([(s.name, s.tax, s.delay) for s in saved], [("FACTORY", 8.25, 3), ("YARD", 0.0, 0)])
        self.assertTrue(self._set(panel, 0, 1, ""))                       # blank means 0, like the web
        self.assertEqual(SupplierDao(self.conn).find_by_project(self.avn.id)[0].tax, 0.0)

    def test_suppliers_add_and_delete(self):
        from nlc.dao import SupplierDao
        panel = self._open("suppliers")
        panel.add_row()
        self.assertEqual(panel.model.rowCount(), 3)
        self.assertEqual(len(SupplierDao(self.conn).find_by_project(self.avn.id)), 3)
        panel._cell_clicked(panel.model.index(2, panel.model.delete_column))      # click the ×
        self.assertEqual(panel.model.rowCount(), 2)
        panel._cell_clicked(panel.model.index(0, 0))                              # any other cell does not delete
        self.assertEqual(len(SupplierDao(self.conn).find_by_project(self.avn.id)), 2)

    def test_materials_db_prices_with_the_supplier_tax(self):
        from nlc.dao import MaterialDbDao, SupplierDao
        sup = SupplierDao(self.conn).find_by_project(self.avn.id)[0]          # FACTORY
        sup.tax = 10.0
        SupplierDao(self.conn).update(sup)
        panel = self._open("database")
        self.assertEqual(panel.model.rowCount(), 0)
        self.assertFalse(panel.empty_label.isHidden())                          # "No materials yet."
        panel.add_row()
        self.assertTrue(panel.empty_label.isHidden())
        self.assertEqual(panel.model.index(0, 3).data(), "FACTORY")              # new rows start at FACTORY
        self._set(panel, 0, 0, "2X4")
        self._set(panel, 0, 1, "12'")
        self._set(panel, 0, 2, "DF.No2")
        self.assertTrue(self._set(panel, 0, 4, "10"))
        self.assertEqual((panel.model.index(0, 5).data(), panel.model.index(0, 6).data()), ("10.00", "11.00"))
        self.assertFalse(self._set(panel, 0, 4, "ten"))
        self._set(panel, 0, 3, "NOPE")                                          # unknown supplier: tax 0
        self.assertEqual((panel.model.index(0, 5).data(), panel.model.index(0, 6).data()), ("0.00", "10.00"))
        saved = MaterialDbDao(self.conn).find_by_project(self.avn.id)[0]
        self.assertEqual((saved.material, saved.length, saved.species, saved.supply, saved.unit_price_out_tax),
                         ("2X4", "12'", "DF.No2", "NOPE", 10.0))

    def test_materials_db_columns_and_suggestions(self):
        from nlc.seed import LENGTHS, SPECIES
        panel = self._open("database")
        m = panel.model
        self.assertEqual([m.headerData(c, Qt.Horizontal) for c in range(m.columnCount())],
                         ["Material", "Length", "Species", "Supply", "Unit $ (no tax)", "Tax%", "Unit $ (final)", ""])
        panel.add_row()
        self.assertTrue(m.flags(m.index(0, 4)) & Qt_ItemIsEditable)
        self.assertFalse(m.flags(m.index(0, 5)) & Qt_ItemIsEditable)               # Tax% is computed
        self.assertFalse(m.flags(m.index(0, 6)) & Qt_ItemIsEditable)               # final price is computed
        self.assertEqual(panel.table.itemDelegateForColumn(1).options, LENGTHS)
        self.assertEqual(panel.table.itemDelegateForColumn(2).options, SPECIES)
        self.assertEqual(panel.table.itemDelegateForColumn(3).options, ["FACTORY", "FIELD"])

    def test_materials_db_delete_and_reopen(self):
        from nlc.dao import MaterialDbDao
        panel = self._open("database")
        panel.add_row()
        panel.add_row()
        self._set(panel, 1, 0, "KEEP")
        panel._cell_clicked(panel.model.index(0, panel.model.delete_column))
        self.assertEqual([d.material for d in MaterialDbDao(self.conn).find_by_project(self.avn.id)], ["KEEP"])
        self.win.go_back_one_level()
        self.win.open_tile("database")
        self.assertEqual(self.win.stack.currentWidget().model.index(0, 0).data(), "KEEP")

    # ---- Received ----
    def test_received_new_delivery_goes_on_top_with_defaults(self):
        from nlc.dao import ReceivedDao
        panel = self._open("received")
        self.assertFalse(panel.empty_label.isHidden())
        panel.add_row()
        self._set(panel, 0, 8, "T-1")
        panel.add_row()                                            # newest on top
        self._set(panel, 0, 8, "T-2")
        self.assertEqual([panel.model.index(r, 8).data() for r in range(2)], ["T-2", "T-1"])
        self.assertEqual(panel.model.index(0, 1).data(), "FACTORY")
        self.assertTrue(panel.empty_label.isHidden())
        self.assertEqual([r.ticket for r in ReceivedDao(self.conn).find_by_project(self.avn.id)], ["T-2", "T-1"])
        self.win.go_back_one_level()
        self.win.open_tile("received")                              # order survives a reopen
        self.assertEqual(self.win.stack.currentWidget().model.index(0, 8).data(), "T-2")

    def test_received_qty_date_rules(self):
        from nlc.dao import ReceivedDao
        panel = self._open("received")
        panel.add_row()
        self.assertTrue(self._set(panel, 0, 7, "5"))
        self.assertFalse(self._set(panel, 0, 7, "12abc"))           # rejected, old value stays
        self.assertEqual(panel.model.index(0, 7).data(), "5")
        self.assertFalse(self._set(panel, 0, 3, "16/10/2026"))      # only yyyy-MM-dd
        self.assertTrue(self._set(panel, 0, 3, "2026-10-16"))
        saved = ReceivedDao(self.conn).find_by_project(self.avn.id)[0]
        self.assertEqual((saved.qty, saved.date), (5.0, "2026-10-16"))
        self.assertTrue(self._set(panel, 0, 7, ""))                  # blank clears the qty (it is not 0)
        self.assertIsNone(ReceivedDao(self.conn).find_by_project(self.avn.id)[0].qty)
        self.assertTrue(self._set(panel, 0, 3, ""))                  # a date may be cleared too
        self.assertEqual(ReceivedDao(self.conn).find_by_project(self.avn.id)[0].date, "")

    def test_received_total_and_delivered_vs_ordered_summary(self):
        from nlc.dao import MaterialDbDao
        from nlc.models import MaterialDbEntry
        MaterialDbDao(self.conn).insert(MaterialDbEntry(project_id=self.avn.id, material="2X4", length="12'",
                                                        species="DF.No2", unit_price_out_tax=10.0, supply="FACTORY"))
        self._add_stud(24.0)
        self._add_stud(36.0)                                         # ordered: 5 x $10 = $50
        panel = self._open("received")
        self.assertEqual([(b.group, b.ordered, b.delivered) for b in panel.summary.bars], [("1ST FLOOR - WALL", 50.0, 0.0)])
        panel.add_row()
        self._set(panel, 0, 0, "1ST FLOOR - WALL")
        self._set(panel, 0, 4, "2x4")
        self._set(panel, 0, 5, "12'")
        self._set(panel, 0, 6, "df.no2")
        self.assertEqual(panel.model.index(0, 11).data(), "$0.00")        # priced line, no qty yet: counts as 0
        self._set(panel, 0, 7, "2")
        self.assertEqual(panel.model.index(0, 11).data(), "$20.00")
        self.assertEqual((panel.summary.bars[0].delivered, round(panel.summary.bars[0].percent)), (20.0, 40))
        panel.remove_row(0)
        self.assertEqual(panel.summary.bars[0].delivered, 0.0)

    # ---- Dashboard ----
    def _seed_dashboard(self):
        from nlc.dao import MaterialDbDao
        from nlc.models import MaterialDbEntry
        MaterialDbDao(self.conn).insert(MaterialDbEntry(project_id=self.avn.id, material="2X4", length="12'",
                                                        species="DF.No2", unit_price_out_tax=10.0, supply="FACTORY"))
        tdao = TakeoffItemDao(self.conn)
        for lf, status in ((24.0, "pending"), (24.0, "ordered"), (24.0, "received"), (24.0, "received")):
            it = self._add_stud(lf)
            it.status = status
            tdao.update(it)                                        # 4 lines x 2 pieces x $10.00

    def test_dashboard_numbers(self):
        self._seed_dashboard()
        panel = self._open("dashboard")
        self.assertEqual(panel.kpis["items"].value_label.text(), "4")
        self.assertEqual(panel.kpis["total"].value_label.text(), "$80.00")
        self.assertEqual(panel.kpis["ordered"].value_label.text(), "$20.00")
        self.assertEqual(panel.kpis["received"].value_label.text(), "$40.00")
        self.assertEqual([(sid, t.count) for sid, t in panel.section_rows if t.count], [("1st-walls", 4)])
        self.assertEqual(len(panel.section_rows), 13)

    def test_dashboard_with_no_items_shows_zeros(self):
        panel = self._open("dashboard")
        self.assertEqual((panel.kpis["items"].value_label.text(), panel.kpis["total"].value_label.text()), ("0", "$0.00"))

    def test_dashboard_title_block_is_saved_on_edit(self):
        from nlc.dao import ProjectDao
        panel = self._open("dashboard")
        self.assertEqual(panel.fields["name"].text(), "AVENEL")                  # created with the job
        panel.fields["jobsite"].textEdited.emit("12 Main St")
        panel.fields["total_sf"].textEdited.emit("48,000")
        info = ProjectDao(self.conn).get_info(self.avn.id)
        self.assertEqual((info.jobsite, info.total_sf, info.name), ("12 Main St", "48,000", "AVENEL"))
        self.win.go_back_one_level()
        self.win.open_tile("dashboard")
        self.assertEqual(self.win.stack.currentWidget().fields["jobsite"].text(), "12 Main St")

    def test_dashboard_export_all(self):
        from unittest import mock
        self._seed_dashboard()
        panel = self._open("dashboard")
        target = Path(self.tmp.name) / "all.csv"
        with mock.patch("nlc.ui.report_table.QFileDialog.getSaveFileName", return_value=(str(target), "CSV (*.csv)")):
            self.assertTrue(panel.export_all())
        text = target.read_bytes().decode("utf-8-sig")
        self.assertEqual(len(text.split("\r\n")), 5)                              # header + 4 lines
        self.assertTrue(text.startswith("Section,Group,Purpose,"))
        self.assertIn("1st Floor Walls,1ST FLOOR - WALL,Stud,,2X4,12'", text)

    def test_circle_click_emits(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        self.win.show()
        home = self.win.stack.currentWidget()
        got = []
        home.open_project.connect(got.append)
        tile = home.grid.tiles()[1]
        QTest.mouseClick(tile.circle, Qt.LeftButton, Qt.NoModifier, QPoint(50, 50))
        self.assertEqual([p.abbr for p in got], ["AVN"])


if __name__ == "__main__":
    unittest.main()
