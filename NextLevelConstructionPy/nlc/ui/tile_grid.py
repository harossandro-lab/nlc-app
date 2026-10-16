"""A scrollable grid of tiles that re-flows its columns when the window is resized."""
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QScrollArea, QWidget


class TileGrid(QScrollArea):
    GAP = 24
    TILE_WIDTH = 150

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._holder = QWidget()
        self._holder.setObjectName("page")
        self._grid = QGridLayout(self._holder)
        self._grid.setContentsMargins(0, 20, 0, 0)
        self._grid.setHorizontalSpacing(self.GAP)
        self._grid.setVerticalSpacing(self.GAP)
        self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setWidget(self._holder)
        self._tiles: List[QWidget] = []

    def set_tiles(self, tiles: List[QWidget]) -> None:
        for t in self._tiles:
            self._grid.removeWidget(t)
            t.deleteLater()
        self._tiles = list(tiles)
        self._relayout()

    def tiles(self) -> List[QWidget]:
        return list(self._tiles)

    def columns(self) -> int:
        width = max(self.viewport().width(), self.TILE_WIDTH)
        return max(1, (width + self.GAP) // (self.TILE_WIDTH + self.GAP))

    def _relayout(self) -> None:
        cols = self.columns()
        for t in self._tiles:
            self._grid.removeWidget(t)
        for i, t in enumerate(self._tiles):
            self._grid.addWidget(t, i // cols, i % cols, Qt.AlignTop)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()
