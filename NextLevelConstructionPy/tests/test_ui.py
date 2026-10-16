"""UI flow tests, run without a display (Qt "offscreen" platform). Skipped when PySide6 is not installed.

Use the virtual environment:  .venv\\Scripts\\python -m unittest discover -s tests -t .
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
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
        self.assertEqual(panel.csv_text().split("\n")[1], "1ST FLOOR - WALL,2X4,12',DF.No2,5,FACTORY,10.00,50.00")

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
        self.assertEqual(target.read_text(encoding="utf-8"), panel.csv_text())
        self.assertTrue(target.read_text(encoding="utf-8").startswith("Group,Material,Length,Species,Qty,"))
        other = Path(self.tmp.name) / "none.csv"
        with mock.patch("nlc.ui.report_table.QFileDialog.getSaveFileName", return_value=("", "")):
            self.assertFalse(panel.export_csv())
        self.assertFalse(other.exists())

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
