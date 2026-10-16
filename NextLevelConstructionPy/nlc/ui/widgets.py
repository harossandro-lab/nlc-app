"""Small reusable widgets."""
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from . import theme


class CircleButton(QWidget):
    """A round tile: dark filled circle with a short label. `dashed` draws the "+ New Job" style."""
    clicked = Signal()

    def __init__(self, text: str, dashed: bool = False, parent=None):
        super().__init__(parent)
        self._text = text
        self._dashed = dashed
        self._hover = False
        self.setFixedSize(104, 104)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        d = min(self.width(), self.height()) - (8 if self._hover else 4)
        x = (self.width() - d) / 2
        y = (self.height() - d) / 2 + (0 if self._hover else 1)
        rect = QRectF(x, y, d, d)
        if self._dashed:
            p.setBrush(QColor("#EAF1F8") if self._hover else QColor(theme.WHITE))
            pen = QPen(QColor(theme.ORANGE if self._hover else theme.LINE), 2, Qt.DashLine)
            p.setPen(pen)
            p.drawEllipse(rect.adjusted(1, 1, -1, -1))
            p.setPen(QColor(theme.ORANGE))
            font = QFont(self.font())
            font.setPixelSize(int(d * 0.42))
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, "+")
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.INK))
            p.drawEllipse(rect)
            p.setPen(QColor(theme.WHITE))
            font = QFont(self.font())
            font.setBold(True)
            font.setPixelSize(max(13, int(d * 0.17)))
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self._text)
        p.end()


class Tile(QWidget):
    """A circle with its caption underneath."""
    clicked = Signal()

    def __init__(self, circle_text: str, caption: str, dashed: bool = False, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.circle = CircleButton(circle_text, dashed)
        self.circle.clicked.connect(self.clicked)
        label = QLabel(caption)
        label.setObjectName("tilelabel")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        lay.addWidget(self.circle, 0, Qt.AlignHCenter)
        lay.addWidget(label)
        self.setFixedWidth(150)
        self.caption = caption
