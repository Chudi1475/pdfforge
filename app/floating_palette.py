"""Floating vertical tool palette overlaid on the left side of the canvas."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QToolButton, QButtonGroup, QMenu, QWidget
)

from . import icons
from .pdf_viewer import Tool


def _g(symbol: str, color: str = "#f5f5f5", size: int = 22) -> QIcon:
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    f = QFont("Segoe UI Symbol", int(size * 0.62)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color)); p.drawText(pix.rect(), Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


class FloatingPalette(QFrame):
    """A pill-shaped floating tool selector that sits inside the canvas."""
    tool_selected = Signal(object)  # Tool enum value
    extra_action = Signal(str)      # 'more'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FloatingPalette")
        self.setFixedWidth(58)

        v = QVBoxLayout(self); v.setContentsMargins(6, 8, 6, 8); v.setSpacing(2)

        self.group = QButtonGroup(self); self.group.setExclusive(True)

        def add(tool, icon, tip):
            b = QToolButton(); b.setObjectName("PaletteBtn")
            b.setIcon(icon); b.setIconSize(QSize(22, 22))
            b.setCheckable(True); b.setToolTip(tip)
            b.setFixedSize(40, 40)
            b.setCursor(Qt.PointingHandCursor)
            b.toggled.connect(lambda checked, t=tool: checked and self.tool_selected.emit(t))
            self.group.addButton(b)
            v.addWidget(b)
            return b

        def add_sep():
            line = QFrame(); line.setObjectName("PaletteSep")
            line.setFrameShape(QFrame.HLine)
            v.addWidget(line)

        # primary tools (matches the palette in screenshots)
        self.select_btn = add(Tool.SELECT, icons.select_icon("#f5f5f5", 22), "Select tool (V)")
        self.select_btn.setChecked(True)
        add_sep()
        self.comment_btn = add(Tool.NOTE, icons.note_icon("#f5f5f5", 22), "Add comment / sticky note")
        add(Tool.DRAW,      icons.draw_icon("#f5f5f5", 22),      "Draw")
        add(Tool.HAND,      icons.hand_icon("#f5f5f5", 22),      "Hand (pan)")
        add(Tool.TEXT,      icons.text_icon("#f5f5f5", 22),      "Add text")
        add(Tool.HIGHLIGHT, icons.highlight_icon("#f5f5f5", 22), "Highlight")
        add(Tool.RECT,      icons.rect_icon("#f5f5f5", 22),      "Rectangle")
        add(Tool.STAMP,     icons.bookmark_icon("#f5f5f5", 22),  "Add stamp")
        add_sep()
        # overflow ...
        more = QToolButton(); more.setObjectName("PaletteBtn")
        more.setText("…"); more.setFont(QFont("Segoe UI Symbol", 14, QFont.Bold))
        more.setFixedSize(40, 40)
        more.setToolTip("More tools")
        more.setCursor(Qt.PointingHandCursor)
        more.setPopupMode(QToolButton.InstantPopup)
        more.setMenu(self._build_more_menu())
        v.addWidget(more)

    def _build_more_menu(self) -> QMenu:
        m = QMenu(self)
        items = [
            ("Edit existing text",  Tool.EDIT_TEXT),
            ("Underline",           Tool.UNDERLINE),
            ("Strikeout",           Tool.STRIKEOUT),
            ("Squiggly",            Tool.SQUIGGLY),
            ("Oval",                Tool.OVAL),
            ("Line",                Tool.LINE),
            ("Arrow",               Tool.ARROW),
            ("Polygon",             Tool.POLYGON),
            ("Callout",             Tool.CALLOUT),
            ("Insert image",        Tool.IMAGE),
            ("Signature",           Tool.SIGNATURE),
            ("Crop page",           Tool.CROP),
            ("Hyperlink",           Tool.LINK),
            ("Redact",              Tool.REDACT),
            ("Mark for redaction",  Tool.REDACT_MARK),
            ("Measure distance",    Tool.MEASURE_DIST),
            ("Measure area",        Tool.MEASURE_AREA),
            ("Text select",         Tool.TEXT_SELECT),
            ("Eraser",              Tool.ERASER),
        ]
        for label, tool in items:
            a = m.addAction(label)
            a.triggered.connect(lambda _checked=False, t=tool: self.tool_selected.emit(t))
        return m

    def set_active_tool(self, tool: Tool):
        # uncheck all, then check matching primary button if any
        for b in self.group.buttons():
            b.blockSignals(True)
        for b in self.group.buttons():
            b.setChecked(False)
        # find matching primary
        mapping = {
            Tool.SELECT: self.select_btn,
            Tool.NOTE: self.comment_btn,
        }
        if tool in mapping:
            mapping[tool].setChecked(True)
        for b in self.group.buttons():
            b.blockSignals(False)
