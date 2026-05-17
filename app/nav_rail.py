"""Left-side icon rail - toggles which side panel is visible."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QFrame, QVBoxLayout, QToolButton

from . import icons


class NavRail(QFrame):
    selected = Signal(str)  # 'pages' | 'bookmarks' | 'comments' | 'attachments' | None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavRail")
        self.setFixedWidth(56)
        v = QVBoxLayout(self); v.setContentsMargins(0, 4, 0, 4); v.setSpacing(2)

        self.buttons = {}
        items = [
            ("pages",       "Pages",       icons.pages_icon),
            ("bookmarks",   "Bookmarks",   icons.bookmark_icon),
            ("comments",    "Comments",    icons.comment_icon),
            ("attachments", "Attachments", icons.attach_icon),
        ]
        for key, label, icon_fn in items:
            b = QToolButton()
            b.setObjectName("RailButton")
            b.setCheckable(True)
            b.setIcon(icon_fn("#e8e8e8", 22))
            b.setIconSize(QSize(22, 22))
            b.setText(label)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setFixedWidth(56)
            b.setFixedHeight(58)
            b.clicked.connect(lambda _checked=False, k=key: self._on_clicked(k))
            self.buttons[key] = b
            v.addWidget(b)
        v.addStretch(1)
        # default: pages selected
        self.buttons["pages"].setChecked(True)
        self._current = "pages"

    def _on_clicked(self, key: str):
        if self._current == key and not self.buttons[key].isChecked():
            # toggled off - hide panel
            self._current = None
            self.selected.emit("")
            return
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        self._current = key
        self.selected.emit(key)
