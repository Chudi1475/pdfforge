"""Left-side mode panels - the contents change based on selected mode tab.

Layout pattern matches the screenshots: title row with gear + close, section
headers in uppercase, list of tool buttons with leading icon, and a "More"
or "View less" toggle at the bottom of long lists.
"""
from __future__ import annotations
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QScrollArea, QWidget, QSizePolicy, QStackedWidget
)

from . import icons


class SectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName("SectionHeader")


class ToolButton(QPushButton):
    """Left-aligned button with icon and label, list-style."""
    def __init__(self, label: str, icon: QIcon, key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeToolBtn")
        self.key = key
        self.setText("    " + label)
        self.setIcon(icon)
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(36)


class IconRow(QWidget):
    """Small icon-only row (e.g. the rotate/insert/delete/swap icons in Modify page section)."""
    clicked = Signal(str)

    def __init__(self, items: list[tuple[str, QIcon, str]], parent=None):
        """items: list of (key, icon, tooltip)"""
        super().__init__(parent)
        h = QHBoxLayout(self); h.setContentsMargins(18, 4, 18, 4); h.setSpacing(10)
        for key, icon, tip in items:
            b = QToolButton(); b.setObjectName("IconCircle")
            b.setIcon(icon); b.setIconSize(QSize(20, 20))
            b.setFixedSize(36, 36)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, k=key: self.clicked.emit(k))
            h.addWidget(b)
        h.addStretch(1)


class BasePanel(QScrollArea):
    """Common scrollable panel with a title row and stacked sections."""
    action = Signal(str)  # tool key
    close_requested = Signal()

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True); self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background:transparent; border:none;")
        self._title_text = title

        outer = QWidget(); self.setWidget(outer)
        self._outer_layout = QVBoxLayout(outer)
        self._outer_layout.setContentsMargins(0, 0, 0, 0); self._outer_layout.setSpacing(0)

        # title row
        top = QWidget()
        th = QHBoxLayout(top); th.setContentsMargins(18, 8, 8, 0); th.setSpacing(4)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("ModePanelTitle")
        th.addWidget(self.title_lbl, 1)

        self.gear_btn = QToolButton(); self.gear_btn.setObjectName("GearBtn")
        from .icons import _new, _painter
        # gear-style icon
        from PySide6.QtGui import QPainter, QPen, QColor, QFont as Qf
        from PySide6.QtGui import QPixmap as Qp
        gear_pix = Qp(20, 20); gear_pix.fill(Qt.transparent)
        gp = QPainter(gear_pix); gp.setRenderHint(QPainter.Antialiasing)
        gp.setPen(QPen(QColor("#a3a3a3"), 1.5))
        gp.setFont(Qf("Segoe UI Symbol", 12)); gp.setPen(QColor("#a3a3a3"))
        gp.drawText(gear_pix.rect(), Qt.AlignCenter, "⚙")
        gp.end()
        self.gear_btn.setIcon(QIcon(gear_pix))
        self.gear_btn.setFixedSize(28, 28); self.gear_btn.setIconSize(QSize(16, 16))
        th.addWidget(self.gear_btn)

        self.close_btn = QToolButton(); self.close_btn.setObjectName("ModePanelClose")
        close_pix = Qp(20, 20); close_pix.fill(Qt.transparent)
        cp = QPainter(close_pix); cp.setRenderHint(QPainter.Antialiasing)
        cp.setFont(Qf("Segoe UI Symbol", 14)); cp.setPen(QColor("#a3a3a3"))
        cp.drawText(close_pix.rect(), Qt.AlignCenter, "✕")
        cp.end()
        self.close_btn.setIcon(QIcon(close_pix))
        self.close_btn.setFixedSize(28, 28); self.close_btn.setIconSize(QSize(14, 14))
        self.close_btn.clicked.connect(self.close_requested.emit)
        th.addWidget(self.close_btn)
        self._outer_layout.addWidget(top)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 12); self._body.setSpacing(0)
        self._outer_layout.addLayout(self._body)
        self._outer_layout.addStretch(1)

    def add_section(self, header: str):
        self._body.addWidget(SectionHeader(header))

    def add_tool(self, key: str, label: str, icon: QIcon):
        b = ToolButton(label, icon, key)
        b.clicked.connect(lambda _checked=False, k=key: self.action.emit(k))
        self._body.addWidget(b)
        return b

    def add_icon_row(self, items: list[tuple[str, QIcon, str]]):
        row = IconRow(items)
        row.clicked.connect(self.action.emit)
        self._body.addWidget(row)

    def add_spacer(self, h: int = 6):
        w = QWidget(); w.setFixedHeight(h); self._body.addWidget(w)

    def add_more_toggle(self, more_items: list[tuple[str, str, QIcon]]):
        """After the basics, a 'More' link reveals more_items."""
        more_btn = QPushButton("More")
        more_btn.setObjectName("MoreBtn")
        less_btn = QPushButton("View less")
        less_btn.setObjectName("ViewLessBtn"); less_btn.hide()

        # create hidden widgets
        hidden = []
        for key, label, icon in more_items:
            b = ToolButton(label, icon, key)
            b.clicked.connect(lambda _checked=False, k=key: self.action.emit(k))
            b.hide()
            self._body.addWidget(b)
            hidden.append(b)

        def show_more():
            for b in hidden: b.show()
            more_btn.hide(); less_btn.show()
        def show_less():
            for b in hidden: b.hide()
            less_btn.hide(); more_btn.show()
        more_btn.clicked.connect(show_more)
        less_btn.clicked.connect(show_less)
        self._body.addWidget(more_btn)
        self._body.addWidget(less_btn)


def make_all_tools_panel() -> BasePanel:
    p = BasePanel("All tools")
    items = [
        ("ai",          "AI Assistant",       icons.comment_icon),
        ("summarize",   "Generative summary", icons.comment_icon),
        ("export",      "Export a PDF",       icons.export_icon),
        ("edit",        "Edit a PDF",         icons.text_icon),
        ("create",      "Create a PDF",       icons.pages_icon),
        ("combine",     "Combine files",      icons.merge_icon),
        ("organize",    "Organize pages",     icons.pages_icon),
        ("comments",    "Send for comments",  icons.comment_icon),
        ("esign",       "Request e-signatures", icons.sign_icon),
        ("ocr",         "Scan & OCR",         icons.ocr_icon),
        ("protect",     "Protect a PDF",      icons.lock_icon),
        ("redact",      "Redact a PDF",       icons.redact_icon),
        ("compress",    "Compress a PDF",     icons.compress_icon),
        ("forms",       "Prepare a form",     icons.note_icon),
    ]
    more_items = [
        ("convert_pdf", "Convert to PDF",     icons.export_icon),
        ("stamp",       "Add a stamp",        icons.bookmark_icon),
        ("certify",     "Use a certificate",  icons.lock_icon),
        ("measure",     "Measure objects",    icons.rect_icon),
        ("compare",     "Compare files",      icons.search_icon),
        ("media",       "Add rich media",     icons.image_icon),
        ("guided",      "Use guided actions", icons.note_icon),
        ("accessibility","Prepare for accessibility", icons.note_icon),
        ("standards",   "Apply PDF standards", icons.note_icon),
        ("index",       "Add search index",   icons.search_icon),
        ("javascript",  "Use JavaScript",     icons.text_icon),
        ("custom_tool", "Create custom tool", icons.rect_icon),
    ]
    for key, label, icon_fn in items:
        p.add_tool(key, label, icon_fn("#f5f5f5", 18))
    p.add_more_toggle([(k, l, icon_fn("#f5f5f5", 18)) for k, l, icon_fn in more_items])
    return p


def make_edit_panel() -> BasePanel:
    p = BasePanel("Edit")
    p.add_section("Modify page")
    p.add_icon_row([
        ("rotate_right_one", icons.rotate_right_icon("#f5f5f5", 22), "Rotate page"),
        ("insert_pages",     icons.merge_icon("#f5f5f5", 22),        "Insert pages"),
        ("delete_page",      icons.redact_icon("#f5f5f5", 22),       "Delete page"),
        ("extract_pg",       icons.export_icon("#f5f5f5", 22),       "Extract pages"),
    ])
    p.add_tool("organize", "Organize pages", icons.pages_icon("#f5f5f5", 18))

    p.add_section("Add content")
    p.add_tool("add_text",     "Text",              icons.text_icon("#f5f5f5", 18))
    p.add_tool("insert_image", "Image",             icons.image_icon("#f5f5f5", 18))
    p.add_tool("header_footer","Header and footer", icons.note_icon("#f5f5f5", 18))
    p.add_tool("watermark",    "Watermark",         icons.watermark_icon("#f5f5f5", 18))
    p.add_tool("hyperlink",    "Link",              icons.attach_icon("#f5f5f5", 18))

    p.add_more_toggle([
        ("edit_text",   "Edit existing text", icons.text_icon("#f5f5f5", 18)),
        ("crop",        "Crop page",          icons.rect_icon("#f5f5f5", 18)),
        ("add_bookmark","Add bookmark",       icons.bookmark_icon("#f5f5f5", 18)),
        ("find_replace","Find & replace",     icons.search_icon("#f5f5f5", 18)),
        ("metadata",    "Document properties",icons.note_icon("#f5f5f5", 18)),
    ])

    p.add_section("Other options")
    p.add_tool("combine",    "Combine files",  icons.merge_icon("#f5f5f5", 18))
    p.add_tool("redact",     "Redact a PDF",   icons.redact_icon("#f5f5f5", 18))
    p.add_tool("forms",      "Prepare a form", icons.note_icon("#f5f5f5", 18))
    return p


def make_convert_panel() -> BasePanel:
    p = BasePanel("Convert")
    p.add_section("Export PDF to")

    def fmt_row(key: str, label: str, ext: str):
        row = QWidget()
        h = QHBoxLayout(row); h.setContentsMargins(18, 0, 18, 0); h.setSpacing(8)
        radio = QToolButton(); radio.setCheckable(True); radio.setFixedSize(18, 18)
        radio.setStyleSheet(
            "QToolButton{background: transparent; border:1px solid #404040; border-radius: 9px;}"
            "QToolButton:checked{background: #e63946; border:1px solid #e63946;}"
        )
        h.addWidget(radio)
        lbl = QLabel(label); h.addWidget(lbl, 1)
        ext_lbl = QLabel(ext); ext_lbl.setStyleSheet("color:#a3a3a3;")
        h.addWidget(ext_lbl)
        chev = QToolButton(); chev.setText("▾"); chev.setStyleSheet("background:transparent; color:#a3a3a3; border:none;")
        h.addWidget(chev)
        row.key = key
        row.radio = radio
        radio.clicked.connect(lambda _checked=False, k=key, r=row: p._pick_format(k, r))
        return row

    word_row  = fmt_row("export_docx", "Microsoft Word",       "DOCX")
    ppt_row   = fmt_row("export_pptx", "Microsoft PowerPoint", "PPTX")
    excel_row = fmt_row("export_xlsx", "Microsoft Excel",      "XLSX")
    image_row = fmt_row("export_png",  "Image format",         "PNG")
    other_row = fmt_row("export_rtf",  "Other format",         "RTF")
    word_row.radio.setChecked(True)
    p._selected_format = "export_docx"
    p._format_rows = [word_row, ppt_row, excel_row, image_row, other_row]
    def _pick(k, row):
        for r in p._format_rows:
            r.radio.setChecked(r is row)
        p._selected_format = k
    p._pick_format = _pick
    for r in p._format_rows: p._body.addWidget(r)

    # Convert button
    btn_wrap = QWidget(); bv = QHBoxLayout(btn_wrap); bv.setContentsMargins(18, 16, 18, 16)
    convert_btn = QPushButton("Convert")
    convert_btn.setObjectName("PrimaryRound")
    convert_btn.clicked.connect(lambda: p.action.emit(p._selected_format))
    bv.addWidget(convert_btn); bv.addStretch(1)
    p._body.addWidget(btn_wrap)

    p.add_section("Other options")
    p.add_tool("convert_pdf",  "Convert to PDF",    icons.export_icon("#f5f5f5", 18))
    p.add_tool("compress",     "Compress a PDF",    icons.compress_icon("#f5f5f5", 18))
    p.add_tool("export_html",  "Convert to HTML",   icons.export_icon("#f5f5f5", 18))
    p.add_tool("export_txt",   "Extract text",      icons.export_icon("#f5f5f5", 18))
    p.add_tool("compare",      "Compare PDFs",      icons.search_icon("#f5f5f5", 18))
    return p


def make_esign_panel() -> BasePanel:
    p = BasePanel("E-Sign")
    p.add_section("Get e-signatures fast")
    # request signatures card
    req_card = QFrame()
    req_card.setStyleSheet("QFrame{background:#262626; border-radius:6px; margin:0 18px;}")
    rv = QVBoxLayout(req_card); rv.setContentsMargins(16, 14, 16, 14); rv.setSpacing(4)
    title = QLabel("Request e-signatures"); title.setStyleSheet("color:#f5f5f5; font-weight:600;")
    desc = QLabel("Send this document to anyone to e-sign online in 3 easy steps")
    desc.setStyleSheet("color:#a3a3a3; font-size:12px;"); desc.setWordWrap(True)
    rv.addWidget(title); rv.addWidget(desc)
    p._body.addWidget(req_card)

    p.add_section("Fill and sign yourself")
    # quick fill tools row
    p.add_icon_row([
        ("add_text",       icons.text_icon("#f5f5f5", 22),    "Add text"),
        ("sign_x",         icons.strike_icon("#f5f5f5", 22),  "X mark"),
        ("sign_check",     icons.underline_icon("#f5f5f5", 22), "Check mark"),
        ("sign_dot",       icons.rect_icon("#f5f5f5", 22),    "Dot"),
        ("sign_box",       icons.rect_icon("#f5f5f5", 22),    "Box"),
        ("sign_line",      icons.draw_icon("#f5f5f5", 22),    "Line"),
    ])
    p.add_tool("signature", "Add your signature", icons.sign_icon("#f5f5f5", 18))
    p.add_tool("initials",  "Add initials",       icons.sign_icon("#f5f5f5", 18))

    p.add_section("After signing")
    p.add_tool("save_certified", "Save a certified copy", icons.save_icon("#f5f5f5", 18))
    p.add_tool("encrypt",  "Password protect",  icons.lock_icon("#f5f5f5", 18))
    return p
