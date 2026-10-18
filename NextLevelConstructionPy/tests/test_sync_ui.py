"""Team-sync widgets, without a display. Skipped when PySide6 is not installed (use the .venv)."""
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QThreadPool
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:  # pragma: no cover
    HAVE_QT = False

from nlc import db
from nlc.dao import ProjectDao
from nlc.sync import service


class FakeRemote:
    logged_in = True

    def __init__(self, fail=False):
        self.fail, self.pushed = fail, 0

    def push(self, changes):
        if self.fail:
            raise ConnectionError("down")
        self.pushed += len(changes)

    def pull(self, since, limit):
        return []


@unittest.skipUnless(HAVE_QT, "PySide6 is not installed")
class SyncUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = {k: os.environ.get(k) for k in ("NLC_SYNC", "NLC_SESSION")}
        os.environ["NLC_SYNC"] = str(Path(self.tmp.name) / "sync.json")        # never touch the real settings
        os.environ["NLC_SESSION"] = str(Path(self.tmp.name) / "session.json")
        self.conn = db.connect(Path(self.tmp.name) / "ui.db")
        ProjectDao(self.conn).create("AVN", "AVENEL")
        from nlc.ui.main_window import MainWindow
        self.MainWindow = MainWindow

    def tearDown(self):
        QThreadPool.globalInstance().waitForDone(5000)
        self.conn.close()
        for k, v in self.old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tmp.cleanup()

    def _settle(self, win):
        """Lets the first automatic round (against an address that refuses connections) finish."""
        end = time.time() + 5
        while time.time() < end and win.sync.busy:
            self.app.processEvents()
            time.sleep(0.02)
        self.app.processEvents()

    def _wait(self, win, text):
        end = time.time() + 5
        while time.time() < end and text not in win.sync_label.text():
            self.app.processEvents()
            time.sleep(0.02)

    def test_off_when_not_set_up_and_no_sync_flag_means_no_controller(self):
        plain = self.MainWindow(self.conn)
        self.assertIsNone(plain.sync)
        plain.close()
        win = self.MainWindow(self.conn, sync=True)
        self.assertIn("not set up", win.sync_label.text())
        win.close()

    def test_signed_in_window_syncs_and_shows_time(self):
        service.save_config("http://127.0.0.1:9", "K")
        Path(os.environ["NLC_SESSION"]).write_text('{"refresh_token": "r", "access_token": "a", "expires_at": 9999999999}')
        win = self.MainWindow(self.conn, sync=True)
        self._settle(win)
        win.sync.remote = FakeRemote()
        win.sync.sync_now()
        self._wait(win, "Synced")
        self.assertIn("Synced", win.sync_label.text())
        win.close()

    def test_offline_shows_waiting_count(self):
        service.save_config("http://127.0.0.1:9", "K")
        Path(os.environ["NLC_SESSION"]).write_text('{"refresh_token": "r", "access_token": "a", "expires_at": 9999999999}')
        win = self.MainWindow(self.conn, sync=True)
        self._settle(win)
        win.sync.remote = FakeRemote(fail=True)
        win.sync.sync_now()
        self._wait(win, "Offline")
        self.assertIn("Offline", win.sync_label.text())
        win.close()


if __name__ == "__main__":
    unittest.main()
