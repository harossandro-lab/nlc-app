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
