"""Second-level circle screen shown after opening a job: one tile per screen, in spreadsheet order."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..models import Project
from ..tiles import TILES, abbreviate
from .tile_grid import TileGrid
from .widgets import Tile


class ProjectMenuPanel(QWidget):
    tile_selected = Signal(str)

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        title = QLabel(project.name)
        title.setObjectName("subtitle")
        lay.addWidget(title)
        self.grid = TileGrid()
        tiles = []
        for tile_id, label in TILES:
            t = Tile(abbreviate(label), label)
            t.clicked.connect(lambda checked=False, tid=tile_id: self.tile_selected.emit(tid))
            t.tile_id = tile_id
            tiles.append(t)
        self.grid.set_tiles(tiles)
        lay.addWidget(self.grid)
