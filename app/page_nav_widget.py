"""Corner page-navigation overlay shown on top of the canvas."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPainter, QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QToolButton, QMenu
)


def _g(symbol: str, color: str = "#f5f5f5", size: int = 18) -> QIcon:
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    f = QFont("Segoe UI Symbol", int(size * 0.72)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color)); p.drawText(pix.rect(), Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


class PageNavWidget(QFrame):
    """Vertical strip in the bottom-right with: page#, total, up/down, zoom in/out, more."""
    page_change = Signal(int)        # 1-based
    page_step = Signal(int)          # +1 / -1
    zoom_in = Signal()
    zoom_out = Signal()
    reload_clicked = Signal()
    overflow_action = Signal(str)    # menu action keys

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PageNav")
        self.setFixedWidth(56)

        v = QVBoxLayout(self); v.setContentsMargins(6, 6, 6, 6); v.setSpacing(2)

        # current page input
        self.page_input = QLineEdit("1"); self.page_input.setObjectName("PageNavInput")
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setFixedHeight(24)
        self.page_input.returnPressed.connect(self._emit_change)
        v.addWidget(self.page_input)

        self.total_label = QLabel("/ 0"); self.total_label.setObjectName("PageNavLabel")
        self.total_label.setAlignment(Qt.AlignCenter)
        v.addWidget(self.total_label)

        v.addSpacing(4)

        # up / down
        self.up_btn = QToolButton(); self.up_btn.setObjectName("PageNavBtn")
        self.up_btn.setIcon(_g("▲", "#f5f5f5", 14))
        self.up_btn.setFixedSize(36, 28)
        self.up_btn.clicked.connect(lambda: self.page_step.emit(-1))
        v.addWidget(self.up_btn, 0, Qt.AlignHCenter)

        self.down_btn = QToolButton(); self.down_btn.setObjectName("PageNavBtn")
        self.down_btn.setIcon(_g("▼", "#f5f5f5", 14))
        self.down_btn.setFixedSize(36, 28)
        self.down_btn.clicked.connect(lambda: self.page_step.emit(+1))
        v.addWidget(self.down_btn, 0, Qt.AlignHCenter)

        v.addSpacing(4)

        # refresh / fit
        self.reload_btn = QToolButton(); self.reload_btn.setObjectName("PageNavBtn")
        self.reload_btn.setIcon(_g("⟳", "#f5f5f5", 14))
        self.reload_btn.setFixedSize(36, 28)
        self.reload_btn.setToolTip("Fit page")
        self.reload_btn.clicked.connect(self.reload_clicked.emit)
        v.addWidget(self.reload_btn, 0, Qt.AlignHCenter)

        # overflow menu
        self.more_btn = QToolButton(); self.more_btn.setObjectName("PageNavBtn")
        self.more_btn.setText("⋯"); self.more_btn.setFont(QFont("Segoe UI Symbol", 13, QFont.Bold))
        self.more_btn.setFixedSize(36, 28)
        self.more_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        for label, key in [("Single page", "single"), ("Continuous", "continuous"),
                           ("Two-page spread", "two_page"), ("Reading mode", "reading"),
                           ("Rotate view CW", "rot_cw"), ("Rotate view CCW", "rot_ccw")]:
            a = menu.addAction(label)
            a.triggered.connect(lambda _checked=False, k=key: self.overflow_action.emit(k))
        self.more_btn.setMenu(menu)
        v.addWidget(self.more_btn, 0, Qt.AlignHCenter)

        v.addSpacing(4)

        # zoom +/-
        self.zoom_in_btn = QToolButton(); self.zoom_in_btn.setObjectName("PageNavBtn")
        self.zoom_in_btn.setIcon(_g("＋", "#f5f5f5", 16))
        self.zoom_in_btn.setFixedSize(36, 28)
        self.zoom_in_btn.clicked.connect(self.zoom_in.emit)
        v.addWidget(self.zoom_in_btn, 0, Qt.AlignHCenter)

        self.zoom_out_btn = QToolButton(); self.zoom_out_btn.setObjectName("PageNavBtn")
        self.zoom_out_btn.setIcon(_g("－", "#f5f5f5", 16))
        self.zoom_out_btn.setFixedSize(36, 28)
        self.zoom_out_btn.clicked.connect(self.zoom_out.emit)
        v.addWidget(self.zoom_out_btn, 0, Qt.AlignHCenter)

    def set_page(self, page_1indexed: int, total: int):
        self.page_input.blockSignals(True)
        self.page_input.setText(str(page_1indexed))
        self.page_input.blockSignals(False)
        self.total_label.setText(f"/ {total}")

    def _emit_change(self):
        try:
            n = int(self.page_input.text())
            self.page_change.emit(n)
        except ValueError:
            pass
