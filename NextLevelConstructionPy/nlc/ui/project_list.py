"""Lista ("All Jobs"): one row per job with its badge, name and creation date. Clicking a row opens the job."""
import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..dao import ProjectDao
from ..formatting import format_created
from ..models import Project
from . import theme


class JobRow(QFrame):
    clicked = Signal()

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setObjectName("jobrow")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"QFrame#jobrow {{ border: 1px solid {theme.LINE}; background: {theme.WHITE}; }}"
                           f"QFrame#jobrow:hover {{ border: 1px solid {theme.ORANGE}; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(14)

        self.badge = QLabel(project.abbr)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedSize(64, 40)
        self.badge.setStyleSheet(f"background: {theme.INK}; color: {theme.WHITE}; font-weight: bold; font-size: 13px;")

        text = QVBoxLayout()
        text.setSpacing(2)
        self.name = QLabel(project.name)
        self.name.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        self.meta = QLabel("Criado em " + format_created(project.created_at))
        self.meta.setStyleSheet(f"color: {theme.GRAY}; font-size: 11.5px; border: none;")
        text.addWidget(self.name)
        text.addWidget(self.meta)

        arrow = QLabel("›")
        arrow.setStyleSheet(f"color: {theme.ORANGE}; font-size: 22px; font-weight: bold; border: none;")

        lay.addWidget(self.badge)
        lay.addLayout(text, 1)
        lay.addWidget(arrow)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class ProjectListPanel(QWidget):
    open_project = Signal(object)   # Project

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        heading = QLabel("All Jobs")
        heading.setObjectName("heading")
        lay.addWidget(heading)

        projects = ProjectDao(conn).find_all()
        self.rows = []
        holder = QWidget()
        holder.setObjectName("page")
        col = QVBoxLayout(holder)
        col.setContentsMargins(0, 12, 0, 0)
        col.setSpacing(8)
        if not projects:
            empty = QLabel("Nenhum job ainda. Clique em Home para criar o primeiro.")
            empty.setObjectName("hint")
            col.addWidget(empty)
        for p in projects:
            row = JobRow(p)
            row.clicked.connect(lambda proj=p: self.open_project.emit(proj))
            self.rows.append(row)
            col.addWidget(row)
        col.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(holder)
        lay.addWidget(scroll, 1)
