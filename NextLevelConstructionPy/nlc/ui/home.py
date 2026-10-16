"""Home screen: the "+ New Job" tile followed by one circle per job."""
import sqlite3

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget)

from ..dao import ProjectDao
from ..models import Project
from .tile_grid import TileGrid
from .widgets import Tile


class NewJobDialog(QDialog):
    """Asks for the 2-5 letter abbreviation (shown in the circle) and the job name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Job")
        self.abbr = QLineEdit()
        self.abbr.setMaxLength(5)
        self.abbr.setPlaceholderText("e.g. NYD")
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. New York Developers")
        form = QFormLayout()
        form.addRow("Abbreviation (2-5 letters, shows in the circle):", self.abbr)
        form.addRow("Job name:", self.name)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)


class HomePanel(QWidget):
    open_project = Signal(object)   # Project

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.conn = conn
        self.dao = ProjectDao(conn)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        title = QLabel("NEXT LEVEL CONSTRUCTION")
        title.setObjectName("subtitle")
        lay.addWidget(title)
        self.grid = TileGrid()
        lay.addWidget(self.grid)
        self.reload()

    def reload(self) -> None:
        new_tile = Tile("+", "New Job", dashed=True)
        new_tile.clicked.connect(self.show_new_job_dialog)
        tiles = [new_tile]
        for p in self.dao.find_all():
            t = Tile(p.abbr, p.name)
            t.clicked.connect(lambda checked=False, proj=p: self.open_project.emit(proj))
            tiles.append(t)
        self.grid.set_tiles(tiles)

    def create_job(self, abbr: str, name: str):
        """Creates a job and opens it. Returns None when both fields are blank (nothing happens)."""
        if not abbr.strip() and not name.strip():
            return None
        project = self.dao.create(abbr, name)
        self.reload()
        self.open_project.emit(project)
        return project

    def show_new_job_dialog(self) -> None:
        dlg = NewJobDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.create_job(dlg.abbr.text(), dlg.name.text())
