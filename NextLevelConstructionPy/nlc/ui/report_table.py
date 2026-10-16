"""Shared base of the read-only report screens (Ordered, Audit Log): heading, subtitle, Export CSV and a table."""
from typing import Callable, List, Optional, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableView,
                               QVBoxLayout, QWidget)

from ..reports import ReportRow
from . import theme

_KIND_BACKGROUND = {"GROUP": "#EEF2F6", "SUBTOTAL": "#F7F9FB", "GRAND": theme.INK}
_TONE_COLOR = {"good": theme.GREEN, "warn": theme.AMBER, "bad": theme.RED, "muted": theme.GRAY, "accent": theme.ORANGE}


class ReportModel(QAbstractTableModel):
    def __init__(self, columns: Sequence[str], rows: List[ReportRow], right_cols: Sequence[int] = (), parent=None):
        super().__init__(parent)
        self.columns = list(columns)
        self.rows = rows
        self.right_cols = set(right_cols)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = self.rows[index.row()], index.column()
        if role == Qt.DisplayRole:
            return row.cells[col]
        if role == Qt.TextAlignmentRole:
            return int((Qt.AlignRight if col in self.right_cols else Qt.AlignLeft) | Qt.AlignVCenter)
        if role == Qt.FontRole:
            font = QFont()
            font.setBold(row.kind != "ITEM")
            return font
        if role == Qt.BackgroundRole and row.kind in _KIND_BACKGROUND:
            return QBrush(QColor(_KIND_BACKGROUND[row.kind]))
        if role == Qt.ForegroundRole:
            if row.kind == "GRAND":
                return QBrush(QColor(theme.WHITE))
            if row.kind == "SUBTOTAL":
                return QBrush(QColor(theme.GRAY))
            tone = row.tone.get(col)
            return QBrush(QColor(_TONE_COLOR[tone])) if tone else None
        return None

    def flags(self, index):
        return Qt.ItemIsEnabled


def save_csv(parent: QWidget, suggested_name: str, text: str) -> bool:
    """Asks where to save and writes the file as UTF-8. Returns False when cancelled or the write failed."""
    path, _ = QFileDialog.getSaveFileName(parent, "Export CSV", suggested_name, "CSV (*.csv)")
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    except OSError as e:
        QMessageBox.critical(parent, "Export CSV", f"Não consegui salvar o arquivo: {e}")
        return False
    return True


class ReportPanel(QWidget):
    def __init__(self, title: str, subtitle: str, columns: Sequence[str], rows: List[ReportRow],
                 right_cols: Sequence[int], widths: Sequence[int], csv_text: Callable[[], str], csv_name: str,
                 empty_hint: str, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._csv_text = csv_text
        self._csv_name = csv_name
        self.rows = rows

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 26)
        lay.setSpacing(14)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        heading = QLabel(title)
        heading.setObjectName("heading")
        sub = QLabel(subtitle)
        sub.setObjectName("subtitle")
        titles.addWidget(heading)
        titles.addWidget(sub)
        top.addLayout(titles, 1)
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        top.addWidget(self.export_button, 0, Qt.AlignTop)
        lay.addLayout(top)

        self.model = ReportModel(columns, rows, right_cols)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QTableView.NoSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(26)
        header = self.table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setStretchLastSection(True)
        for i, w in enumerate(widths):
            self.table.setColumnWidth(i, w)
        self.table.setStyleSheet(f"QTableView {{ border: 1px solid {theme.LINE}; }}"
                                 f"QHeaderView::section {{ background: {theme.WHITE}; color: {theme.GRAY}; border: none; "
                                 f"border-bottom: 1px solid {theme.LINE}; padding: 6px 8px; font-weight: bold; }}")
        self._apply_spans()
        lay.addWidget(self.table, 1)

        self.empty_label: Optional[QLabel] = None
        if not rows:
            self.empty_label = QLabel(empty_hint)
            self.empty_label.setObjectName("hint")
            self.empty_label.setWordWrap(True)
            lay.addWidget(self.empty_label)

    def _apply_spans(self) -> None:
        """Group headers run across the whole row; subtotal and grand total labels run up to the last column."""
        n = len(self.model.columns)
        for r, row in enumerate(self.rows):
            if row.kind == "GROUP":
                self.table.setSpan(r, 0, 1, n)
            elif row.kind in ("SUBTOTAL", "GRAND"):
                self.table.setSpan(r, 0, 1, n - 1)

    def csv_text(self) -> str:
        return self._csv_text()

    def export_csv(self) -> bool:
        return save_csv(self, self._csv_name, self._csv_text())
