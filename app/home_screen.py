"""Home / start screen shown when no document is open."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy
)

from . import APP_NAME, APP_TAGLINE, icons


RECENTS_FILE = Path.home() / ".chudipdfpro" / "recents.json"
MAX_RECENTS = 12


def load_recents() -> list[str]:
    try:
        if RECENTS_FILE.is_file():
            data = json.loads(RECENTS_FILE.read_text("utf-8"))
            return [p for p in data if os.path.isfile(p)][:MAX_RECENTS]
    except Exception:
        pass
    return []


def save_recents(paths: list[str]):
    try:
        RECENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        RECENTS_FILE.write_text(json.dumps(paths[:MAX_RECENTS]), encoding="utf-8")
    except Exception:
        pass


def add_recent(path: str):
    items = load_recents()
    if path in items:
        items.remove(path)
    items.insert(0, path)
    save_recents(items)


class QuickActionButton(QPushButton):
    def __init__(self, label: str, sublabel: str, icon, parent=None):
        super().__init__(parent)
        self.setObjectName("QuickAction")
        self.setIcon(icon); self.setIconSize(QSize(28, 28))
        self.setText(f"\n{label}\n\n{sublabel}")
        self.setMinimumHeight(110)


class HomeScreen(QFrame):
    open_file = Signal()
    open_path = Signal(str)
    new_blank = Signal()
    merge_pdfs = Signal()
    images_to_pdf = Signal()
    request_action = Signal(str)  # action key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HomeRoot")
        self._build()
        self.refresh_recents()

    def _build(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent; border:none;")
        outer.addWidget(scroll)

        body = QWidget(); scroll.setWidget(body)
        v = QVBoxLayout(body); v.setContentsMargins(48, 36, 48, 36); v.setSpacing(28)

        # hero
        hero = QHBoxLayout(); hero.setSpacing(20)
        logo = QLabel(); logo.setPixmap(icons.app_logo(72).pixmap(72, 72))
        hero.addWidget(logo, 0, Qt.AlignTop)
        ht = QVBoxLayout(); ht.setSpacing(4)
        title = QLabel(f"Welcome to {APP_NAME}"); title.setObjectName("HomeTitle")
        subtitle = QLabel(APP_TAGLINE); subtitle.setObjectName("HomeSubtitle")
        ht.addWidget(title); ht.addWidget(subtitle)
        hero.addLayout(ht, 1)
        v.addLayout(hero)

        # quick actions row
        actions_label = QLabel("Quick start"); actions_label.setObjectName("ToolGroupHeader")
        v.addWidget(actions_label)
        grid = QGridLayout(); grid.setSpacing(12); grid.setContentsMargins(0, 0, 0, 0)
        items = [
            ("Open file",       "Browse for a PDF",        icons.folder_icon("#e63946", 28),  self.open_file.emit),
            ("Blank document",  "Start from a blank page", icons.pages_icon("#2196f3", 28),    self.new_blank.emit),
            ("Combine PDFs",    "Merge files into one",    icons.merge_icon("#43a047", 28),    self.merge_pdfs.emit),
            ("Build from images","Convert images to PDF",  icons.image_icon("#fb8c00", 28),    self.images_to_pdf.emit),
        ]
        for i, (lbl, sub, icon, slot) in enumerate(items):
            btn = QuickActionButton(lbl, sub, icon)
            btn.clicked.connect(slot)
            grid.addWidget(btn, 0, i)
        for i in range(len(items)):
            grid.setColumnStretch(i, 1)
        v.addLayout(grid)

        # recents
        rh = QHBoxLayout()
        rlabel = QLabel("Recent files"); rlabel.setObjectName("ToolGroupHeader")
        rh.addWidget(rlabel, 1)
        self.clear_btn = QPushButton("Clear"); self.clear_btn.setObjectName("link")
        self.clear_btn.clicked.connect(self._clear_recents)
        rh.addWidget(self.clear_btn, 0)
        v.addLayout(rh)

        self.recents_container = QVBoxLayout(); self.recents_container.setSpacing(8)
        v.addLayout(self.recents_container)
        v.addStretch(1)

    def _clear_recents(self):
        save_recents([])
        self.refresh_recents()

    def refresh_recents(self):
        # clear current
        while self.recents_container.count():
            it = self.recents_container.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        items = load_recents()
        if not items:
            empty = QLabel("No recent files yet — open something to get started.")
            empty.setStyleSheet("color: #888; padding: 16px;")
            self.recents_container.addWidget(empty)
            self.clear_btn.setVisible(False)
            return
        self.clear_btn.setVisible(True)
        for path in items:
            b = QPushButton()
            b.setObjectName("RecentCard")
            b.setIcon(icons.folder_icon("#e63946", 22))
            b.setIconSize(QSize(22, 22))
            stem = os.path.basename(path)
            folder = os.path.dirname(path)
            b.setText(f"  {stem}\n  {folder}")
            b.setMinimumHeight(58)
            b.clicked.connect(lambda _checked=False, p=path: self.open_path.emit(p))
            self.recents_container.addWidget(b)
