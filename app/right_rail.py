"""Right edge icon rail - AI sparkle, Search, Bookmarks, Pages, Attachments."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPainter, QColor, QFont, QPixmap
from PySide6.QtWidgets import QFrame, QVBoxLayout, QToolButton, QButtonGroup

from . import icons


def _g(symbol: str, color: str = "#f5f5f5", size: int = 18) -> QIcon:
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    f = QFont("Segoe UI Symbol", int(size * 0.72)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color)); p.drawText(pix.rect(), Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


class RightRail(QFrame):
    """Vertical icon rail. Each button toggles a flyout panel."""
    panel_requested = Signal(str)   # 'ai' | 'search' | 'bookmarks' | 'pages' | 'attachments' | ''

    BUTTONS = [
        ("ai",          "AI Assistant",          "✦"),
        ("search",      "Search this document",  "🔍"),
        ("bookmarks",   "Bookmarks",             "🔖"),
        ("pages",       "Page thumbnails",       "▤"),
        ("attachments", "Attachments",           "📎"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RightRail")
        self.setFixedWidth(44)

        v = QVBoxLayout(self); v.setContentsMargins(0, 6, 0, 6); v.setSpacing(2)

        self.group = QButtonGroup(self); self.group.setExclusive(False)
        self.buttons: dict[str, QToolButton] = {}
        for key, tip, symbol in self.BUTTONS:
            b = QToolButton(); b.setObjectName("RailBtn")
            color = "#a855f7" if key == "ai" else "#f5f5f5"
            b.setIcon(_g(symbol, color, 20))
            b.setIconSize(QSize(20, 20))
            b.setCheckable(True)
            b.setFixedSize(44, 44)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.toggled.connect(lambda checked, k=key: self._on_toggled(k, checked))
            self.group.addButton(b)
            self.buttons[key] = b
            v.addWidget(b)
        v.addStretch(1)

    def _on_toggled(self, key: str, checked: bool):
        if checked:
            for k, b in self.buttons.items():
                if k != key:
                    b.blockSignals(True); b.setChecked(False); b.blockSignals(False)
            self.panel_requested.emit(key)
        else:
            # nothing checked
            if not any(b.isChecked() for b in self.buttons.values()):
                self.panel_requested.emit("")

    def select(self, key: str):
        for k, b in self.buttons.items():
            b.blockSignals(True); b.setChecked(k == key); b.blockSignals(False)

    def clear(self):
        for b in self.buttons.values():
            b.blockSignals(True); b.setChecked(False); b.blockSignals(False)
