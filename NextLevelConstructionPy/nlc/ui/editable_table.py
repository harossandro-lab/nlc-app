"""Shared base of the editable table screens (Suppliers & Tax, Materials DB, Received, take-off sections): heading,
"+ Add" button and a table whose cells save at once. The last column is the red × that deletes the row.

Columns can be read-only (computed), clickable (the take-off Status pill), colored per cell, and drop-downs whose
options depend on the row (MATERIAL follows SPECIES). An optional search box filters rows without touching the data."""
import re
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton, QStyledItemDelegate,
                               QTableView, QVBoxLayout, QWidget)

from . import theme

DELETE_MARK = "×"


@dataclass
class Column:
    title: str
    text: Callable[[Any], str]                           # what the cell shows for a row object
    set: Optional[Callable[[Any, str], bool]] = None     # stores typed text; False = rejected; None = read-only
    right: bool = False
    width: int = 100
    delegate: Optional[QStyledItemDelegate] = None
    bold: bool = False
    on_click: Optional[Callable[[Any], bool]] = None     # a click changes the row (True = changed, then it is saved)
    color: Optional[Callable[[Any], Optional[str]]] = None        # text color of the cell
    background: Optional[Callable[[Any], Optional[str]]] = None   # background color of the cell


def row_object(index: QModelIndex):
    """The row object behind a model index."""
    return index.model().rows[index.row()]


class ComboDelegate(QStyledItemDelegate):
    """A drop-down of suggestions (with a blank first option). `editable` lets the user type something else.
    `options` may be a list or a function of the row (MATERIAL options depend on the row's SPECIES)."""

    def __init__(self, options, editable: bool, parent=None):
        super().__init__(parent)
        self._options = options
        self.editable = editable

    @property
    def options(self) -> List[str]:
        return list(self._options) if not callable(self._options) else []

    def options_for(self, index: QModelIndex) -> List[str]:
        return list(self._options(row_object(index))) if callable(self._options) else list(self._options)

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(self.editable)
        combo.addItem("")
        combo.addItems(self.options_for(index))
        return combo

    def setEditorData(self, editor, index):
        text = str(index.data(Qt.EditRole) or "")
        i = editor.findText(text)
        if i >= 0:
            editor.setCurrentIndex(i)
        elif self.editable:
            editor.setCurrentText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)


class RecordTableModel(QAbstractTableModel):
    def __init__(self, columns: List[Column], rows: list, persist: Callable[[Any], None], parent=None):
        super().__init__(parent)
        self.columns = columns          # the delete column is the extra last one
        self.rows = rows
        self.persist = persist

    @property
    def delete_column(self) -> int:
        return len(self.columns)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns) + 1

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return "" if section == self.delete_column else self.columns[section].title
        return None

    def flags(self, index):
        if index.column() == self.delete_column:
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self.columns[index.column()].set is not None:
            flags |= Qt.ItemIsEditable
        return flags

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        if col == self.delete_column:
            if role == Qt.DisplayRole:
                return DELETE_MARK
            if role == Qt.ForegroundRole:
                return QBrush(QColor(theme.RED))
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignCenter)
            return None
        column, row = self.columns[col], self.rows[index.row()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            return column.text(row)
        if role == Qt.TextAlignmentRole:
            return int((Qt.AlignRight if column.right else Qt.AlignLeft) | Qt.AlignVCenter)
        if role == Qt.FontRole and column.bold:
            font = QFont()
            font.setBold(True)
            return font
        if role == Qt.ForegroundRole:
            c = column.color(row) if column.color else (theme.GRAY if column.set is None and column.on_click is None else None)
            return QBrush(QColor(c)) if c else None
        if role == Qt.BackgroundRole and column.background:
            c = column.background(row)
            return QBrush(QColor(c)) if c else None
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or index.column() == self.delete_column:
            return False
        column = self.columns[index.column()]
        if column.set is None:
            return False
        row = self.rows[index.row()]
        if not column.set(row, str(value).strip()):
            QApplication.beep()          # not accepted (e.g. text in a number cell): the old value stays
            return False
        self._saved(index.row(), row)
        return True

    def click(self, r: int, c: int) -> bool:
        """A click on a clickable cell (e.g. Status): changes the row, saves it. False for other cells."""
        if c == self.delete_column or c >= len(self.columns) or self.columns[c].on_click is None:
            return False
        row = self.rows[r]
        if not self.columns[c].on_click(row):
            return False
        self._saved(r, row)
        return True

    def _saved(self, r: int, row) -> None:
        self.persist(row)
        # the whole row is refreshed: computed columns (tax, final price, QTY, total) depend on what was just typed
        self.dataChanged.emit(self.index(r, 0), self.index(r, self.delete_column))

    def append(self, row) -> None:
        self.insert(len(self.rows), row)

    def insert(self, at: int, row) -> None:
        self.beginInsertRows(QModelIndex(), at, at)
        self.rows.insert(at, row)
        self.endInsertRows()

    def remove(self, r: int):
        self.beginRemoveRows(QModelIndex(), r, r)
        row = self.rows.pop(r)
        self.endRemoveRows()
        return row


def normalize(text: str) -> str:
    """Lower case, no accents-insensitive tricks needed for the filter: the web only trims and lower-cases."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


class EditableTablePanel(QWidget):
    def __init__(self, title: str, subtitle: str, add_label: str, columns: List[Column], rows: list,
                 persist: Callable[[Any], None], create_row: Callable[[], Any], delete_row: Callable[[Any], None],
                 empty_hint: str = "", new_rows_on_top: bool = False,
                 header_widgets: Sequence[QWidget] = (), search_text: Optional[Callable[[Any], str]] = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._create_row = create_row
        self._delete_row = delete_row
        self._new_rows_on_top = new_rows_on_top

        lay = QVBoxLayout(self)
        self._layout = lay
        lay.setContentsMargins(26, 22, 26, 26)
        lay.setSpacing(14)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        heading = QLabel(title)
        heading.setObjectName("heading")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("subtitle")
        titles.addWidget(heading)
        titles.addWidget(self.subtitle_label)
        top.addLayout(titles, 1)
        for w in header_widgets:
            top.addWidget(w, 0, Qt.AlignTop)
        self.add_button = QPushButton(add_label)
        self.add_button.setObjectName("accent")
        self.add_button.clicked.connect(self.add_row)
        top.addWidget(self.add_button, 0, Qt.AlignTop)
        lay.addLayout(top)

        self.model = RecordTableModel(columns, rows, persist)
        self._search_text = search_text
        self._needle = ""
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setShowGrid(True)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed | QTableView.AnyKeyPressed)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        header = self.table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        self.table.setStyleSheet(f"QTableView {{ gridline-color: {theme.LINE}; border: 1px solid {theme.LINE}; }}"
                                 f"QHeaderView::section {{ background: {theme.WHITE}; color: {theme.GRAY}; border: none; "
                                 f"border-bottom: 1px solid {theme.LINE}; padding: 6px 8px; font-weight: bold; }}")
        for i, c in enumerate(columns):
            self.table.setColumnWidth(i, c.width)
            if c.delegate is not None:
                self.table.setItemDelegateForColumn(i, c.delegate)
        self.table.setColumnWidth(self.model.delete_column, 34)
        self.table.clicked.connect(self._cell_clicked)
        lay.addWidget(self.table, 1)

        self.empty_label = QLabel(empty_hint)
        self.empty_label.setObjectName("hint")
        lay.addWidget(self.empty_label)
        self.model.rowsInserted.connect(self._update_empty)
        self.model.rowsRemoved.connect(self._update_empty)
        for signal in (self.model.rowsInserted, self.model.rowsRemoved, self.model.dataChanged):
            signal.connect(lambda *a: self._apply_filter())
        self._update_empty()

    def _update_empty(self, *args) -> None:
        self.empty_label.setVisible(bool(self.empty_label.text()) and self.model.rowCount() == 0)

    def set_filter(self, text: str) -> None:
        """Shows only the rows whose search text contains `text` (empty = all rows). Rows are only hidden in the
        table: the data is never touched."""
        self._needle = normalize(text)
        self._apply_filter()

    def _apply_filter(self) -> None:
        for r, row in enumerate(self.model.rows):
            hidden = bool(self._needle) and self._search_text is not None \
                and self._needle not in normalize(self._search_text(row))
            if self.table.isRowHidden(r) != hidden:
                self.table.setRowHidden(r, hidden)

    def visible_row_count(self) -> int:
        return sum(1 for r in range(self.model.rowCount()) if not self.table.isRowHidden(r))

    def add_footer(self, widget: QWidget) -> None:
        """Puts an extra widget (e.g. a summary) under the table."""
        self._layout.addWidget(widget)

    def add_row(self) -> None:
        row = self._create_row()
        if self._new_rows_on_top:
            self.model.insert(0, row)
            self.table.scrollToTop()
        else:
            self.model.append(row)
            self.table.scrollToBottom()

    def remove_row(self, r: int) -> None:
        """Deletes the row at SOURCE position r (the position in the unfiltered data)."""
        if self.table.state() == QTableView.EditingState:
            self.table.closePersistentEditor(self.table.currentIndex())
        self._delete_row(self.model.rows[r])
        self.model.remove(r)

    def _cell_clicked(self, index) -> None:
        """The × deletes the row, a clickable cell (Status) changes it."""
        if not index.isValid():
            return
        if index.column() == self.model.delete_column:
            self.remove_row(index.row())
        else:
            self.model.click(index.row(), index.column())
