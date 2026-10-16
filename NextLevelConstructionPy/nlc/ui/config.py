"""Config: manage the jobs — rename the abbreviation and name (saved as you type), open a job, or remove it.

Removing is a HARD delete here (everything of the job is erased from the database, with no way back), so it asks for
the abbreviation to be typed. The web app only hides the job from its list; this app deletes the data."""
import sqlite3
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from ..dao import ProjectDao
from ..models import Project
from . import theme


def delete_confirmed(project: Project, typed: str) -> bool:
    """The job may be deleted only when the typed text is its abbreviation (ignoring case and spaces around it)."""
    return bool(project.abbr.strip()) and typed.strip().upper() == project.abbr.strip().upper()


def describe_counts(counts: Dict[str, int]) -> str:
    parts = [f"{n} {name}" for name, n in counts.items() if n]
    return ", ".join(parts) if parts else "no records besides the job itself"


class DeleteJobDialog(QDialog):
    """Shows what will be erased and enables Delete only after the job's abbreviation is typed."""

    def __init__(self, project: Project, counts: Dict[str, int], parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Remove job")
        lay = QVBoxLayout(self)
        msg = QLabel(f"<b>Remove {project.name} ({project.abbr})?</b><br><br>"
                     f"This <b>permanently erases</b> the job and all its data: {describe_counts(counts)}.<br>"
                     f"There is no way to undo it.<br><br>Type <b>{project.abbr}</b> to confirm:")
        msg.setWordWrap(True)
        self.typed = QLineEdit()
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.delete_button = self.buttons.addButton("Delete job", QDialogButtonBox.AcceptRole)
        self.delete_button.setEnabled(False)
        self.typed.textChanged.connect(lambda t: self.delete_button.setEnabled(delete_confirmed(project, t)))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(msg)
        lay.addWidget(self.typed)
        lay.addWidget(self.buttons)


def ask_delete(project: Project, counts: Dict[str, int], parent=None) -> bool:
    return DeleteJobDialog(project, counts, parent).exec() == QDialog.Accepted


class ConfigPanel(QWidget):
    open_project = Signal(object)   # Project

    def __init__(self, conn: sqlite3.Connection, confirm_delete: Optional[Callable[[Project, Dict[str, int]], bool]] = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.dao = ProjectDao(conn)
        self._confirm_delete = confirm_delete or (lambda p, c: ask_delete(p, c, self))
        self.rows = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        heading = QLabel("Config")
        heading.setObjectName("heading")
        sub = QLabel("Gerenciar jobs — renomear sigla/nome ou remover.")
        sub.setObjectName("subtitle")
        lay.addWidget(heading)
        lay.addWidget(sub)
        self._holder = QWidget()
        self._holder.setObjectName("page")
        self._rows_layout = QVBoxLayout(self._holder)
        self._rows_layout.setContentsMargins(0, 12, 0, 0)
        self._rows_layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(self._holder)
        lay.addWidget(scroll, 1)
        self.reload()

    def reload(self) -> None:
        for r in self.rows:
            r["widget"].deleteLater()
        self.rows = []
        while self._rows_layout.count():
            self._rows_layout.takeAt(0)
        for p in self.dao.find_all():
            self._add_row(p)
        self._rows_layout.addStretch(1)

    def _add_row(self, p: Project) -> None:
        w = QWidget()
        w.setObjectName("page")
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        abbr = QLineEdit(p.abbr)
        abbr.setMaxLength(5)
        abbr.setFixedWidth(80)
        name = QLineEdit(p.name)
        open_button = QPushButton("Open")
        delete_button = QPushButton("×")
        delete_button.setToolTip("Remove job")
        delete_button.setFixedWidth(34)
        delete_button.setStyleSheet(f"color: {theme.RED}; font-weight: bold; font-size: 16px;")
        h.addWidget(abbr)
        h.addWidget(name, 1)
        h.addWidget(open_button)
        h.addWidget(delete_button)
        abbr.textEdited.connect(lambda text, proj=p, edit=abbr: self._rename(proj, edit, abbr=text))
        name.textEdited.connect(lambda text, proj=p: self._rename(proj, None, name=text))
        open_button.clicked.connect(lambda checked=False, proj=p: self.open_project.emit(proj))
        delete_button.clicked.connect(lambda checked=False, proj=p: self.remove(proj))
        self._rows_layout.addWidget(w)
        self.rows.append({"project": p, "abbr": abbr, "name": name, "open": open_button, "delete": delete_button, "widget": w})

    def _rename(self, p: Project, abbr_edit: Optional[QLineEdit], abbr: Optional[str] = None, name: Optional[str] = None) -> None:
        if abbr is not None:
            p.abbr = abbr.upper()                      # always upper-case, like the web
            if abbr_edit is not None and abbr_edit.text() != p.abbr:
                abbr_edit.setText(p.abbr)
        if name is not None:
            p.name = name
        self.dao.rename(p.id, p.abbr, p.name)

    def remove(self, p: Project) -> bool:
        """Asks for confirmation and, if given, deletes the job and all its data. Returns True when deleted."""
        if not self._confirm_delete(p, self.dao.counts(p.id)):
            return False
        self.dao.delete(p.id)
        self.reload()
        return True
