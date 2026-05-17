"""Right-side Tools panel with grouped tool cards."""
from __future__ import annotations
from typing import Callable

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
)

from . import icons


class ToolCard(QPushButton):
    def __init__(self, label: str, icon: QIcon, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolCard")
        self.setIcon(icon); self.setIconSize(QSize(20, 20))
        self.setText("   " + label)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)


class ToolsPane(QFrame):
    action = Signal(str)  # emits an action key

    GROUPS = [
        ("Edit & annotate", [
            ("add_text",     "Add text",       "T"),
            ("highlight",    "Highlight",      "H"),
            ("underline",    "Underline",      "U"),
            ("strikeout",    "Strikeout",      "S"),
            ("note",         "Sticky note",    "N"),
            ("draw",         "Draw",           "D"),
            ("rect",         "Rectangle",      "R"),
            ("insert_image", "Insert image",   "I"),
        ]),
        ("Fill & sign", [
            ("signature",    "Sign yourself",  "G"),
        ]),
        ("Organize pages", [
            ("rotate_left",  "Rotate left",    "L"),
            ("rotate_right", "Rotate right",   "K"),
            ("insert_blank", "Insert blank",   "B"),
            ("duplicate_pg", "Duplicate page", "P"),
            ("delete_page",  "Delete page",    "X"),
            ("extract_pg",   "Extract pages",  "E"),
            ("reorder",      "Apply order",    "O"),
        ]),
        ("Combine & split", [
            ("merge",        "Merge files",    "M"),
            ("split",        "Split file",     "Y"),
        ]),
        ("Convert & export", [
            ("export",       "Export to...",   "Z"),
            ("images_pdf",   "Images to PDF",  "Q"),
            ("metadata",     "Metadata",       "W"),
        ]),
        ("Protect & enhance", [
            ("compress",     "Compress",       "Z"),
            ("watermark",    "Watermark",      "M"),
            ("page_numbers", "Page numbers",   "P"),
            ("encrypt",      "Password protect","P"),
            ("decrypt",      "Remove password","R"),
            ("redact_text",  "Redact by text", "T"),
            ("redact_draw",  "Redact (drag)",  "D"),
            ("ocr",          "Make searchable","O"),
        ]),
    ]

    ICONS = {
        "add_text":     icons.text_icon,
        "highlight":    icons.highlight_icon,
        "underline":    icons.underline_icon,
        "strikeout":    icons.strike_icon,
        "note":         icons.note_icon,
        "draw":         icons.draw_icon,
        "rect":         icons.rect_icon,
        "insert_image": icons.image_icon,
        "signature":    icons.sign_icon,
        "rotate_left":  icons.rotate_left_icon,
        "rotate_right": icons.rotate_right_icon,
        "insert_blank": icons.pages_icon,
        "duplicate_pg": icons.pages_icon,
        "delete_page":  icons.redact_icon,
        "extract_pg":   icons.export_icon,
        "reorder":      icons.pages_icon,
        "merge":        icons.merge_icon,
        "split":        icons.split_icon,
        "export":       icons.export_icon,
        "images_pdf":   icons.image_icon,
        "metadata":     icons.note_icon,
        "compress":     icons.compress_icon,
        "watermark":    icons.watermark_icon,
        "page_numbers": icons.note_icon,
        "encrypt":      icons.lock_icon,
        "decrypt":      icons.lock_icon,
        "redact_text":  icons.redact_icon,
        "redact_draw":  icons.redact_icon,
        "ocr":          icons.ocr_icon,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolsPane")
        self.setFixedWidth(260)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        header = QLabel("TOOLS"); header.setObjectName("PanelTitle")
        outer.addWidget(header)

        scroll = QScrollArea(); scroll.setObjectName("ToolsScroll")
        scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll, 1)

        body = QWidget(); scroll.setWidget(body)
        v = QVBoxLayout(body); v.setContentsMargins(8, 4, 8, 16); v.setSpacing(2)

        self._buttons: dict[str, ToolCard] = {}
        for group_name, items in self.GROUPS:
            lbl = QLabel(group_name); lbl.setObjectName("ToolGroupHeader")
            v.addWidget(lbl)
            for key, label, _ in items:
                icon = self.ICONS.get(key, icons.rect_icon)("#e8e8e8", 22)
                card = ToolCard(label, icon)
                card.clicked.connect(lambda _checked=False, k=key: self.action.emit(k))
                v.addWidget(card)
                self._buttons[key] = card
        v.addStretch(1)

    def set_enabled_all(self, on: bool):
        for b in self._buttons.values():
            b.setEnabled(on)
