"""Renders the app (offscreen) to PNG files so the look can be checked without a display.

    .venv\\Scripts\\python tools\\screenshot.py OUT_DIR

Uses a throwaway database with one sample job; nothing touches the real data.
"""
import os
import sys
import tempfile
from pathlib import Path

# The "offscreen" platform has no fonts on Windows (text turns into boxes), so use the real platform and never
# show() the window: widget.grab() renders it without putting anything on screen.
if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from nlc import db  # noqa: E402
from nlc.dao import ProjectDao  # noqa: E402
from nlc.ui import theme  # noqa: E402
from nlc.ui.main_window import MainWindow  # noqa: E402


def main(out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyleSheet(theme.STYLE_SHEET)
    with tempfile.TemporaryDirectory() as tmp:
        conn = db.connect(Path(tmp) / "shot.db")
        dao = ProjectDao(conn)
        avn = dao.create("AVN", "AVENEL")
        dao.create("NYD", "New York Developers")
        win = MainWindow(conn)
        app.processEvents()
        win.grab().save(str(out / "home.png"))
        win.open_project(avn)
        app.processEvents()
        win.grab().save(str(out / "project_menu.png"))
        win.open_tile("roof")
        app.processEvents()
        win.grab().save(str(out / "screen.png"))
        win.close()
        conn.close()
    print("saved to", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "shots")
