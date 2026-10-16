"""Top-level window. Three-level navigation, same shape as the Java and web apps:
Home (job circles) -> project menu (screen circles) -> a screen. The back link always goes up exactly one level."""
import sqlite3
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import audit, db
from ..models import Project
from ..tiles import TILES
from .audit_log import AuditPanel
from .home import HomePanel
from .materials_db import MaterialsDbPanel
from .ordered import OrderedPanel
from .project_list import ProjectListPanel
from .project_menu import ProjectMenuPanel
from .received import ReceivedPanel
from .suppliers import SuppliersPanel


class PlaceholderPanel(QWidget):
    """Stands in for a screen that is not ported to Python yet."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 26)
        heading = QLabel(title)
        heading.setObjectName("heading")
        hint = QLabel("Esta tela ainda não foi portada para Python (o app Java já a tem).")
        hint.setObjectName("hint")
        lay.addWidget(heading)
        lay.addWidget(hint)
        lay.addStretch(1)


class ClickableLabel(QLabel):
    def __init__(self, text: str, on_click, parent=None):
        super().__init__(text, parent)
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click()


class MainWindow(QMainWindow):
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        super().__init__()
        self.conn = conn if conn is not None else db.connect()
        self.setWindowTitle("Next Level Construction — Material List")
        self.resize(1180, 780)

        self.current_level = "home"        # home | project-menu | screen
        self.current_project: Optional[Project] = None
        self.stack = QStackedWidget()

        central = QWidget()
        central.setObjectName("page")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._top_bar())
        root.addWidget(self.stack, 1)
        root.addWidget(self._bottom_nav())
        self.setCentralWidget(central)
        self.show_home()

    # ---------------- chrome ----------------
    def _top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 12, 18, 12)
        brand = QLabel("NEXT LEVEL CONSTRUCTION")
        brand.setObjectName("brand")
        self.back_link = ClickableLabel("", self.go_back_one_level)
        self.back_link.setObjectName("backlink")
        lay.addWidget(brand)
        lay.addWidget(self.back_link)
        lay.addStretch(1)
        return bar

    def _bottom_nav(self) -> QFrame:
        nav = QFrame()
        nav.setObjectName("bottomnav")
        lay = QHBoxLayout(nav)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        for label, action in (("Home", self.show_home), ("Lista", self.show_list), ("More", self.show_about)):
            b = QPushButton(label)
            b.setObjectName("navbutton")
            b.setFlat(True)
            b.clicked.connect(lambda checked=False, a=action: a())
            lay.addWidget(b, 1)
        return nav

    # ---------------- navigation ----------------
    def _show(self, widget: QWidget, keep: Optional[QWidget] = None) -> None:
        """Shows `widget`, dropping every other panel except `keep` (avoids piling up old screens)."""
        for i in reversed(range(self.stack.count())):
            w = self.stack.widget(i)
            if w is not widget and w is not keep:
                self.stack.removeWidget(w)
                w.deleteLater()
        if self.stack.indexOf(widget) < 0:
            self.stack.addWidget(widget)
        self.stack.setCurrentWidget(widget)

    def show_home(self) -> None:
        self.current_level = "home"
        self.current_project = None
        self.back_link.setText("")
        panel = HomePanel(self.conn)
        panel.open_project.connect(self.open_project)
        self._show(panel)

    def show_list(self) -> None:
        """Lista (All Jobs): rebuilt each time so new and renamed jobs show up. Like Home, it has nothing above it."""
        self.current_level = "home"
        self.current_project = None
        self.back_link.setText("")
        panel = ProjectListPanel(self.conn)
        panel.open_project.connect(self.open_project)
        self._show(panel)

    def open_project(self, project: Project) -> None:
        self.current_project = project
        audit.ensure_baseline(self.conn, project.id)
        self.current_level = "project-menu"
        self.back_link.setText("← All Jobs")
        menu = ProjectMenuPanel(project)
        menu.tile_selected.connect(self.open_tile)
        self._show(menu)

    def open_tile(self, tile_id: str) -> None:
        assert self.current_project is not None
        self.current_level = "screen"
        self.back_link.setText("← " + self.current_project.name)
        self._show(self._build_screen(tile_id))

    def _build_screen(self, tile_id: str) -> QWidget:
        """The screen behind a circle; the ones not ported yet show a placeholder."""
        project = self.current_project
        if tile_id == "ordered":
            return OrderedPanel(self.conn, project)
        if tile_id == "audit":
            return AuditPanel(self.conn, project)
        if tile_id == "received":
            return ReceivedPanel(self.conn, project)
        if tile_id == "database":
            return MaterialsDbPanel(self.conn, project)
        if tile_id == "suppliers":
            return SuppliersPanel(self.conn, project)
        return PlaceholderPanel(dict(TILES).get(tile_id, tile_id))

    def go_back_one_level(self) -> None:
        if self.current_level == "screen" and self.current_project is not None:
            self.open_project(self.current_project)
        elif self.current_level == "project-menu":
            self.show_home()

    def show_about(self) -> None:
        QMessageBox.information(
            self, "More",
            "Next Level Construction — Material List\n\n"
            "Cada job tem seu banco de dados local (SQLite) em:\n"
            f"{db.default_path()}\n\n"
            "QTY calculado com a mesma fórmula da planilha original.")
