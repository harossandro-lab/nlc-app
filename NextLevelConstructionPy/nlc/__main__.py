"""Starts the desktop app:  python -m nlc"""
import sys

from PySide6.QtWidgets import QApplication

from .ui import theme
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLE_SHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
