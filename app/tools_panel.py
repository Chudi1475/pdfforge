"""Right-side Tools panel with tabbed categories and tool cards."""
from __future__ import annotations
from typing import Callable

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QWidget, QButtonGroup, QToolButton, QSizePolicy
)

from . import icons


CATEGORIES = [
    ("all",      "All"),
    ("edit",     "Edit"),
    ("comment",  "Comment"),
    ("sign",     "Fill & Sign"),
    ("organize", "Organize"),
    ("protect",  "Protect"),
    ("convert",  "Convert"),
]


# (key, label, category, icon_fn)
TOOLS = [
    # ---- Edit ----
    ("edit_text",    "Edit text",         "edit",     icons.text_icon),
    ("add_text",     "Add text",          "edit",     icons.text_icon),
    ("insert_image", "Insert image",      "edit",     icons.image_icon),
    ("crop",         "Crop pages",        "edit",     icons.rect_icon),
    ("crop_all",     "Crop margins...",   "edit",     icons.rect_icon),
    ("header_footer","Header & footer",   "edit",     icons.note_icon),
    ("hyperlink",    "Add hyperlink",     "edit",     icons.attach_icon),
    ("add_bookmark", "Add bookmark",      "edit",     icons.bookmark_icon),
    ("find_replace", "Find & replace",    "edit",     icons.search_icon),
    ("metadata",     "Document properties","edit",    icons.note_icon),

    # ---- Comment ----
    ("highlight",    "Highlight",         "comment",  icons.highlight_icon),
    ("underline",    "Underline",         "comment",  icons.underline_icon),
    ("strikeout",    "Strikeout",         "comment",  icons.strike_icon),
    ("squiggly",     "Squiggly",          "comment",  icons.underline_icon),
    ("note",         "Sticky note",       "comment",  icons.note_icon),
    ("callout",      "Text callout",      "comment",  icons.comment_icon),
    ("draw",         "Free draw",         "comment",  icons.draw_icon),
    ("rect",         "Rectangle",         "comment",  icons.rect_icon),
    ("oval",         "Oval",              "comment",  icons.rect_icon),
    ("line",         "Line",              "comment",  icons.draw_icon),
    ("arrow",        "Arrow",             "comment",  icons.draw_icon),
    ("polygon",      "Polygon",           "comment",  icons.rect_icon),
    ("eraser",       "Erase annotation",  "comment",  icons.redact_icon),
    ("stamp",        "Stamp",             "comment",  icons.bookmark_icon),

    # ---- Fill & Sign ----
    ("signature",    "Sign yourself",     "sign",     icons.sign_icon),
    ("forms_fill",   "Fill form fields",  "sign",     icons.note_icon),
    ("add_field",    "Add text field",    "sign",     icons.text_icon),
    ("add_checkbox", "Add checkbox",      "sign",     icons.rect_icon),

    # ---- Organize ----
    ("rotate_left",  "Rotate left",       "organize", icons.rotate_left_icon),
    ("rotate_right", "Rotate right",      "organize", icons.rotate_right_icon),
    ("rotate_all",   "Rotate all",        "organize", icons.rotate_right_icon),
    ("insert_blank", "Insert blank",      "organize", icons.pages_icon),
    ("duplicate_pg", "Duplicate page",    "organize", icons.pages_icon),
    ("delete_page",  "Delete page",       "organize", icons.redact_icon),
    ("extract_pg",   "Extract pages",     "organize", icons.export_icon),
    ("insert_pages", "Insert from PDF",   "organize", icons.merge_icon),
    ("replace_page", "Replace page",      "organize", icons.pages_icon),
    ("reorder",      "Apply page order",  "organize", icons.pages_icon),
    ("merge",        "Combine PDFs",      "organize", icons.merge_icon),
    ("split",        "Split file",        "organize", icons.split_icon),

    # ---- Protect ----
    ("encrypt",      "Password protect",  "protect",  icons.lock_icon),
    ("decrypt",      "Remove password",   "protect",  icons.lock_icon),
    ("redact_draw",  "Redact area",       "protect",  icons.redact_icon),
    ("redact_mark",  "Mark for redaction","protect",  icons.redact_icon),
    ("redact_apply", "Apply redactions",  "protect",  icons.redact_icon),
    ("redact_text",  "Redact by text",    "protect",  icons.redact_icon),
    ("sanitize",     "Sanitize document", "protect",  icons.lock_icon),
    ("watermark",    "Text watermark",    "protect",  icons.watermark_icon),
    ("image_wm",     "Image watermark",   "protect",  icons.image_icon),
    ("page_numbers", "Page numbers",      "protect",  icons.note_icon),

    # ---- Convert ----
    ("compress",     "Compress",          "convert",  icons.compress_icon),
    ("ocr",          "Make searchable",   "convert",  icons.ocr_icon),
    ("export_docx",  "PDF → Word",        "convert",  icons.export_icon),
    ("export_xlsx",  "PDF → Excel",       "convert",  icons.export_icon),
    ("export_html",  "PDF → HTML",        "convert",  icons.export_icon),
    ("export_png",   "PDF → Images",      "convert",  icons.image_icon),
    ("export_txt",   "Extract text",      "convert",  icons.export_icon),
    ("images_pdf",   "Images → PDF",      "convert",  icons.image_icon),
    ("compare",      "Compare PDFs",      "convert",  icons.search_icon),
    ("batch",        "Batch processor",   "convert",  icons.merge_icon),
    ("tts",          "Read aloud",        "convert",  icons.comment_icon),
]


class ToolCard(QPushButton):
    def __init__(self, label: str, icon: QIcon, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolCard")
        self.setIcon(icon); self.setIconSize(QSize(20, 20))
        self.setText("   " + label)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)


class CategoryTab(QToolButton):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QToolButton {
                background: transparent; color: #b8b8b8; border: none;
                padding: 8px 10px; font-weight: 600; font-size: 11px;
                border-bottom: 2px solid transparent;
            }
            QToolButton:hover { color: #f0f0f0; }
            QToolButton:checked { color: #e63946; border-bottom: 2px solid #e63946; }
        """)


class ToolsPane(QFrame):
    action = Signal(str)  # tool key emitted on click

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolsPane")
        self.setMinimumWidth(260); self.setMaximumWidth(360)

        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        header = QLabel("TOOLS"); header.setObjectName("PanelTitle")
        outer.addWidget(header)

        # category tabs
        tab_row = QFrame(); tab_row.setStyleSheet("background:#2b2b2b; border-bottom:1px solid #1f1f1f;")
        tr = QHBoxLayout(tab_row); tr.setContentsMargins(4, 0, 4, 0); tr.setSpacing(0)
        self.tab_buttons: dict[str, CategoryTab] = {}
        self.tab_group = QButtonGroup(self); self.tab_group.setExclusive(True)
        for key, label in CATEGORIES:
            b = CategoryTab(label)
            b.toggled.connect(lambda checked, k=key: checked and self._show_category(k))
            self.tab_buttons[key] = b
            self.tab_group.addButton(b)
            tr.addWidget(b)
        outer.addWidget(tab_row)

        # body scroll
        scroll = QScrollArea(); scroll.setObjectName("ToolsScroll")
        scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll, 1)

        self.body = QWidget(); scroll.setWidget(self.body)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(8, 6, 8, 16); self.body_layout.setSpacing(2)

        self.cards: dict[str, ToolCard] = {}
        self._build_all_cards()

        self.tab_buttons["all"].setChecked(True)
        self._show_category("all")

    def _build_all_cards(self):
        # group by category for nicer ordering when "All" is shown
        for cat_key, cat_label in CATEGORIES:
            if cat_key == "all":
                continue
            header = QLabel(cat_label)
            header.setObjectName("ToolGroupHeader")
            self.body_layout.addWidget(header)
            for tool_key, label, c, icon_fn in TOOLS:
                if c != cat_key:
                    continue
                icon = icon_fn("#e8e8e8", 22)
                card = ToolCard(label, icon)
                card.clicked.connect(lambda _checked=False, k=tool_key: self.action.emit(k))
                self.body_layout.addWidget(card)
                self.cards[tool_key] = card
        self.body_layout.addStretch(1)

    def _show_category(self, cat: str):
        # iterate over all rows; for "all" show everything; otherwise hide non-matching
        for i in range(self.body_layout.count()):
            w = self.body_layout.itemAt(i).widget()
            if w is None: continue
            # header rows have objectName == "ToolGroupHeader"
            if w.objectName() == "ToolGroupHeader":
                # only show headers in "all" view
                w.setVisible(cat == "all")
                continue
            if not isinstance(w, ToolCard):
                continue
            tool_key = None
            for k, c in self.cards.items():
                if c is w: tool_key = k; break
            if tool_key is None: continue
            real_cat = next((c for (k, _l, c, _ic) in TOOLS if k == tool_key), None)
            w.setVisible(cat == "all" or real_cat == cat)

    def set_enabled_all(self, on: bool):
        for c in self.cards.values():
            c.setEnabled(on)
