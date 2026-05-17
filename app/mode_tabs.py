"""Mode tab bar - All tools / Edit / Convert / E-Sign + right-side actions."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QToolButton, QButtonGroup, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QWidget
)

from . import icons


def _glyph(symbol: str, color: str = "#f5f5f5", size: int = 18) -> QIcon:
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    f = QFont("Segoe UI Symbol", int(size * 0.66)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color)); p.drawText(pix.rect(), Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


def _gradient_sparkle(size: int = 18) -> QIcon:
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
    grad_color = QColor("#a855f7")
    f = QFont("Segoe UI Symbol", int(size * 0.7)); f.setBold(True)
    p.setFont(f); p.setPen(grad_color); p.drawText(pix.rect(), Qt.AlignCenter, "✦")
    p.end()
    return QIcon(pix)


class ModeTabsBar(QFrame):
    """Top mode selector row + search + right-side actions."""
    mode_changed = Signal(str)           # 'all', 'edit', 'convert', 'esign'
    search_submitted = Signal(str)
    save_clicked = Signal()
    cloud_clicked = Signal()
    print_clicked = Signal()
    share_clicked = Signal()
    ask_ai_clicked = Signal()
    ai_button_clicked = Signal()
    find_focus_requested = Signal()

    MODES = [("all", "All tools"), ("edit", "Edit"), ("convert", "Convert"), ("esign", "E-Sign")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeBar")
        self.setFixedHeight(48)
        h = QHBoxLayout(self); h.setContentsMargins(12, 0, 12, 0); h.setSpacing(2)

        self._group = QButtonGroup(self); self._group.setExclusive(True)
        self.buttons: dict[str, QToolButton] = {}
        for key, label in self.MODES:
            b = QToolButton(); b.setObjectName("ModeTab")
            b.setText(label); b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.toggled.connect(lambda checked, k=key: checked and self.mode_changed.emit(k))
            self._group.addButton(b)
            self.buttons[key] = b
            h.addWidget(b)
        self.buttons["all"].setChecked(True)

        h.addStretch(1)

        # find box
        find_wrap = QWidget(); fw = QHBoxLayout(find_wrap); fw.setContentsMargins(0, 0, 0, 0)
        self.find = QLineEdit()
        self.find.setObjectName("FindBox")
        self.find.setPlaceholderText("Find text or tools")
        self.find.returnPressed.connect(lambda: self.search_submitted.emit(self.find.text()))
        find_wrap.setFixedWidth(290)
        # search glyph overlay
        search_lbl = QLabel(find_wrap)
        search_lbl.setText("🔍")
        search_lbl.setStyleSheet("color:#a3a3a3; font-size: 14px;")
        search_lbl.setGeometry(10, 10, 18, 18)
        fw.addWidget(self.find)
        h.addWidget(find_wrap)

        h.addSpacing(6)

        # ai sparkle
        self.ai_btn = QToolButton(); self.ai_btn.setObjectName("TopActionBtn")
        self.ai_btn.setIcon(_gradient_sparkle(20)); self.ai_btn.setIconSize(QSize(20, 20))
        self.ai_btn.setToolTip("AI Assistant")
        self.ai_btn.setFixedSize(32, 32)
        self.ai_btn.clicked.connect(self.ai_button_clicked.emit)
        h.addWidget(self.ai_btn)

        # save
        self.save_btn = QToolButton(); self.save_btn.setObjectName("TopActionBtn")
        self.save_btn.setIcon(icons.save_icon("#f5f5f5", 20)); self.save_btn.setIconSize(QSize(20, 20))
        self.save_btn.setToolTip("Save (Ctrl+S)")
        self.save_btn.setFixedSize(32, 32)
        self.save_btn.clicked.connect(self.save_clicked.emit)
        h.addWidget(self.save_btn)

        # cloud / save-to-recent
        self.cloud_btn = QToolButton(); self.cloud_btn.setObjectName("TopActionBtn")
        self.cloud_btn.setIcon(_glyph("⬆", "#f5f5f5", 18)); self.cloud_btn.setIconSize(QSize(20, 20))
        self.cloud_btn.setToolTip("Save as / Export")
        self.cloud_btn.setFixedSize(32, 32)
        self.cloud_btn.clicked.connect(self.cloud_clicked.emit)
        h.addWidget(self.cloud_btn)

        # print
        self.print_btn = QToolButton(); self.print_btn.setObjectName("TopActionBtn")
        self.print_btn.setIcon(icons.print_icon("#f5f5f5", 20)); self.print_btn.setIconSize(QSize(20, 20))
        self.print_btn.setToolTip("Print (Ctrl+P)")
        self.print_btn.setFixedSize(32, 32)
        self.print_btn.clicked.connect(self.print_clicked.emit)
        h.addWidget(self.print_btn)

        h.addSpacing(6)

        # Share button
        self.share_btn = QPushButton("Share")
        self.share_btn.setObjectName("ShareBtn")
        self.share_btn.clicked.connect(self.share_clicked.emit)
        h.addWidget(self.share_btn)

        # Ask AI Assistant pill
        self.ask_ai = QPushButton(" ✦  Ask AI Assistant")
        self.ask_ai.setObjectName("AskAiBtn")
        self.ask_ai.clicked.connect(self.ask_ai_clicked.emit)
        h.addWidget(self.ask_ai)

    def set_mode(self, key: str):
        if key in self.buttons:
            self.buttons[key].setChecked(True)
