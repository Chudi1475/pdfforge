"""Top title bar with hamburger menu, home, document tabs, +Create, and right icons."""
from __future__ import annotations
import os
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QToolButton, QPushButton, QLabel, QMenu, QSizePolicy,
    QWidget, QVBoxLayout
)

from . import icons


def _make_glyph(symbol: str, color: str = "#f5f5f5", size: int = 18) -> QIcon:
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    f = QFont("Segoe UI Symbol", int(size * 0.66)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color))
    p.drawText(pix.rect(), Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


class DocTab(QFrame):
    """A single document tab in the top bar."""
    clicked = Signal(int)
    close_clicked = Signal(int)

    def __init__(self, index: int, label: str, active: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("DocTabActive" if active else "DocTab")
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)
        self.setCursor(Qt.PointingHandCursor)
        h = QHBoxLayout(self); h.setContentsMargins(8, 0, 4, 0); h.setSpacing(4)
        icon = QLabel()
        icon.setPixmap(icons.folder_icon("#e63946", 16).pixmap(14, 14))
        h.addWidget(icon)
        self.label = QLabel(self._elide(label))
        self.label.setObjectName("DocTabLabel" if active else "DocTabLabelInactive")
        self.label.setToolTip(label)
        h.addWidget(self.label, 1)
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("DocTabClose")
        self.close_btn.setIcon(_make_glyph("✕", "#a3a3a3", 12))
        self.close_btn.setIconSize(QSize(10, 10))
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.clicked.connect(lambda: self.close_clicked.emit(self.index))
        h.addWidget(self.close_btn)
        self._active = active

    @staticmethod
    def _elide(s: str, n: int = 22) -> str:
        return s if len(s) <= n else s[: n - 1] + "…"

    def set_active(self, active: bool):
        self._active = active
        self.setObjectName("DocTabActive" if active else "DocTab")
        self.label.setObjectName("DocTabLabel" if active else "DocTabLabelInactive")
        # force re-style
        self.style().unpolish(self); self.style().polish(self)
        self.label.style().unpolish(self.label); self.label.style().polish(self.label)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.close_btn.geometry().contains(e.pos()):
            self.clicked.emit(self.index)
        super().mousePressEvent(e)


class TopBar(QFrame):
    """The chrome at the very top of the window."""
    menu_action = Signal(str)            # for hamburger menu items
    home_clicked = Signal()
    create_clicked = Signal()
    tab_clicked = Signal(int)
    tab_closed = Signal(int)
    notifications_clicked = Signal()
    help_clicked = Signal()
    profile_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(46)
        self.tabs: list[DocTab] = []

        h = QHBoxLayout(self); h.setContentsMargins(8, 4, 8, 4); h.setSpacing(4)

        # hamburger menu
        self.burger = QToolButton(); self.burger.setObjectName("TopBarBtn")
        self.burger.setText("☰"); self.burger.setFont(QFont("Segoe UI Symbol", 16))
        self.burger.setPopupMode(QToolButton.InstantPopup)
        self.burger.setMenu(self._build_menu())
        self.burger.setFixedSize(38, 32)
        h.addWidget(self.burger)

        # home button
        self.home_btn = QToolButton(); self.home_btn.setObjectName("TopBarBtn")
        self.home_btn.setIcon(_make_glyph("⌂", "#f5f5f5", 18))
        self.home_btn.setIconSize(QSize(18, 18))
        self.home_btn.setFixedSize(38, 32)
        self.home_btn.clicked.connect(self.home_clicked.emit)
        self.home_btn.setToolTip("Home")
        h.addWidget(self.home_btn)

        # document tab strip
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0); self.tabs_layout.setSpacing(0)
        self.tabs_layout.addStretch(1)
        h.addWidget(self.tabs_container, 1)

        # + Create button
        self.create_btn = QPushButton("+ Create")
        self.create_btn.setObjectName("CreateBtn")
        self.create_btn.clicked.connect(self.create_clicked.emit)
        h.addWidget(self.create_btn)

        h.addSpacing(8)

        # right-side action icons
        self.help_btn = QToolButton(); self.help_btn.setObjectName("TopBarBtn")
        self.help_btn.setIcon(_make_glyph("?", "#f5f5f5", 16))
        self.help_btn.setFixedSize(32, 32)
        self.help_btn.setToolTip("Help")
        self.help_btn.clicked.connect(self.help_clicked.emit)
        h.addWidget(self.help_btn)

        self.notif_btn = QToolButton(); self.notif_btn.setObjectName("TopBarBtn")
        self.notif_btn.setIcon(_make_glyph("🔔", "#f5f5f5", 16))
        self.notif_btn.setFixedSize(32, 32)
        self.notif_btn.setToolTip("Notifications")
        self.notif_btn.clicked.connect(self.notifications_clicked.emit)
        h.addWidget(self.notif_btn)

        # brand badge
        h.addSpacing(4)
        logo = QLabel(); logo.setPixmap(icons.app_logo(20).pixmap(20, 20))
        h.addWidget(logo)
        brand = QLabel("Chudi PDF Pro"); brand.setObjectName("Brand")
        h.addWidget(brand)

    def _build_menu(self) -> QMenu:
        m = QMenu(self)
        for label, key in [
            ("Open...",         "open"),
            ("Open recent",     "recent"),
            (None, None),
            ("Save",            "save"),
            ("Save as...",      "save_as"),
            (None, None),
            ("Print...",        "print"),
            ("Properties",      "properties"),
            (None, None),
            ("Preferences",     "preferences"),
            ("About",           "about"),
            (None, None),
            ("Exit",            "exit"),
        ]:
            if label is None:
                m.addSeparator()
            else:
                a = m.addAction(label)
                a.triggered.connect(lambda _checked=False, k=key: self.menu_action.emit(k))
        return m

    # ------- tab management -------
    def set_tabs(self, tab_labels: list[str], active_index: int):
        """Replace all tabs and highlight the active one."""
        # clear current tabs
        for t in self.tabs:
            self.tabs_layout.removeWidget(t)
            t.deleteLater()
        self.tabs.clear()
        # remove any leftover stretches/spacers
        while self.tabs_layout.count():
            it = self.tabs_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        for i, label in enumerate(tab_labels):
            tab = DocTab(i, label, active=(i == active_index))
            tab.clicked.connect(self.tab_clicked.emit)
            tab.close_clicked.connect(self.tab_closed.emit)
            self.tabs_layout.addWidget(tab)
            self.tabs.append(tab)
        self.tabs_layout.addStretch(1)

    def set_active(self, index: int):
        for i, t in enumerate(self.tabs):
            t.set_active(i == index)

    def update_tab_label(self, index: int, label: str):
        if 0 <= index < len(self.tabs):
            self.tabs[index].label.setText(DocTab._elide(label))
            self.tabs[index].label.setToolTip(label)
