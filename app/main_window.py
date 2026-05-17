"""Chudi PDF Pro - main window with multi-doc tabs, side panels, tools pane,
view modes, reading mode, redaction queue, TTS, and the full menu/toolbar set.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QDesktopServices, QFont, QIcon, QKeySequence,
    QPainter, QPainterPath, QPen, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSizePolicy, QSpinBox, QStackedWidget, QStatusBar,
    QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget, QSplitter, QMenu
)

from . import APP_NAME, __version__, icons
from .pdf_engine import PdfDocument
from .pdf_viewer import PdfGraphicsView, Tool, ViewMode
from .nav_rail import NavRail
from .side_panel import SidePanel
from .tools_panel import ToolsPane
from .home_screen import HomeScreen, add_recent
from .tools.dialogs import (
    MergeDialog, SplitDialog, EncryptDialog, CompressDialog, OcrDialog,
    WatermarkDialog, ImageWatermarkDialog, PageNumbersDialog, RedactTextDialog,
    SignatureDialog, ExportDialog, SearchPanel, HeaderFooterDialog, CropDialog,
    InsertPagesDialog, ReplacePageDialog, FindReplaceDialog, HyperlinkDialog,
    AddBookmarkDialog, StampsDialog, CompareDialog, BatchDialog, SanitizeDialog,
    TtsDialog,
)
from .forms import FormFillDialog


@dataclass
class DocTab:
    view: PdfGraphicsView
    doc: PdfDocument
    path: Optional[str]
    modified: bool = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1560, 980)
        self.setWindowIcon(icons.app_logo(32))
        self._tabs: list[DocTab] = []
        self._signature_pix: Optional[QPixmap] = None
        self._search_matches: list = []
        self._search_idx = -1
        self._search_options = {"case_sensitive": False, "whole_words": False}
        self._reading_mode_chrome = None  # saved widget visibility state
        self._tts_dialog: Optional[TtsDialog] = None

        self._build_actions()
        self._build_central()
        self._build_top_bar()
        self._build_toolbar()
        self._build_property_strip()
        self._build_statusbar()

        self.setAcceptDrops(True)
        self._update_enabled()
        self._show_home()

    # ============== central layout ==============
    def _build_central(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Home
        self.home = HomeScreen()
        self.home.open_file.connect(self.open_file)
        self.home.open_path.connect(self.load_pdf)
        self.home.new_blank.connect(self._new_blank)
        self.home.merge_pdfs.connect(self._do_merge)
        self.home.images_to_pdf.connect(self._do_images_to_pdf)
        self.stack.addWidget(self.home)

        # Editor
        editor = QWidget()
        eh = QHBoxLayout(editor); eh.setContentsMargins(0, 0, 0, 0); eh.setSpacing(0)

        self.rail = NavRail()
        self.rail.selected.connect(self._on_rail_selected)
        eh.addWidget(self.rail)

        self.splitter = QSplitter(Qt.Horizontal); self.splitter.setHandleWidth(1)

        self.side = SidePanel()
        self.side.page_clicked.connect(self._side_goto_page)
        self.side.pages_reordered.connect(self._mark_modified)
        self.side.delete_pages_requested.connect(self._delete_pages)
        self.side.rotate_pages_requested.connect(self._rotate_pages)
        self.side.duplicate_page_requested.connect(self._duplicate_page)
        self.side.extract_pages_requested.connect(self._extract_pages_list)
        self.side.insert_blank_requested.connect(self._insert_blank_after)

        center = QWidget()
        cv = QVBoxLayout(center); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(0)
        self.search = SearchPanel(); self.search.hide()
        self.search.search_changed.connect(self._on_search_text)
        self.search.next_match.connect(lambda: self._goto_match(+1))
        self.search.prev_match.connect(lambda: self._goto_match(-1))
        self.search.case_changed.connect(lambda v: self._set_search_option("case_sensitive", v))
        self.search.whole_words_changed.connect(lambda v: self._set_search_option("whole_words", v))
        self.search.close_requested.connect(self._close_search)
        cv.addWidget(self.search)

        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        cv.addWidget(self.tabs, 1)

        self.tools = ToolsPane()
        self.tools.action.connect(self._on_tool_action)

        self.splitter.addWidget(self.side)
        self.splitter.addWidget(center)
        self.splitter.addWidget(self.tools)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([240, 900, 280])

        eh.addWidget(self.splitter, 1)
        self.stack.addWidget(editor)

    # ============== top bar ==============
    def _build_top_bar(self):
        bar = QFrame(); bar.setObjectName("TopBar"); bar.setFixedHeight(40)
        h = QHBoxLayout(bar); h.setContentsMargins(10, 4, 10, 4); h.setSpacing(8)

        # hamburger menu
        burger = QToolButton(); burger.setText("☰"); burger.setObjectName("flat")
        burger.setStyleSheet("QToolButton{background:transparent;color:#f0f0f0;font-size:18px;padding:2px 8px;}"
                             "QToolButton:hover{background:#3d3d3d;}")
        burger.setPopupMode(QToolButton.InstantPopup)
        burger.setMenu(self._build_main_menu())
        h.addWidget(burger)

        logo = QLabel(); logo.setPixmap(icons.app_logo(22).pixmap(22, 22))
        h.addWidget(logo)
        brand1 = QLabel("Chudi"); brand1.setObjectName("Brand")
        brand2 = QLabel("PDF Pro"); brand2.setStyleSheet("color:#e63946; font-weight:700; font-size:14px;")
        h.addWidget(brand1); h.addWidget(brand2)

        h.addStretch(1)

        self.top_search = QLineEdit()
        self.top_search.setObjectName("TopSearch")
        self.top_search.setPlaceholderText("Search in document   (Ctrl+F)")
        self.top_search.returnPressed.connect(self._top_search_submit)
        h.addWidget(self.top_search)

        b_home = QPushButton("Home"); b_home.setObjectName("flat"); b_home.clicked.connect(self._show_home)
        h.addWidget(b_home)

        b_read = QPushButton("Reading mode"); b_read.setObjectName("flat")
        b_read.clicked.connect(self._toggle_reading_mode)
        h.addWidget(b_read)

        self.setMenuWidget(bar)

    def _build_main_menu(self) -> QMenu:
        m = QMenu(self)

        f = m.addMenu("File")
        f.addActions([self.act_open, self.act_save, self.act_save_as])
        f.addSeparator()
        f.addActions([self.act_close, self.act_print])
        f.addSeparator()
        f.addAction(self.act_quit)

        e = m.addMenu("Edit")
        e.addActions([self.act_undo, self.act_redo])
        e.addSeparator()
        e.addActions([self.act_find, self.act_find_replace])

        v = m.addMenu("View")
        v.addActions([self.act_zoom_in, self.act_zoom_out, self.act_fit_width, self.act_fit_page, self.act_actual])
        v.addSeparator()
        v.addActions([self.act_view_continuous, self.act_view_single, self.act_view_two_page])
        v.addSeparator()
        v.addAction(self.act_reading_mode)

        t = m.addMenu("Tools")
        for a in (self.act_t_select, self.act_t_hand, self.act_t_text, self.act_t_edit_text,
                  self.act_t_note, self.act_t_highlight, self.act_t_underline, self.act_t_strike,
                  self.act_t_draw, self.act_t_rect, self.act_t_oval, self.act_t_line, self.act_t_arrow,
                  self.act_t_image, self.act_t_sign, self.act_t_stamp, self.act_t_redact,
                  self.act_t_crop, self.act_t_link, self.act_t_measure_dist, self.act_t_measure_area):
            t.addAction(a)

        p = m.addMenu("Pages")
        p.addActions([self.act_rot_l, self.act_rot_r, self.act_rotate_all])
        p.addSeparator()
        p.addActions([self.act_insert_blank, self.act_delete_page, self.act_extract,
                      self.act_insert_pages, self.act_replace_page, self.act_reorder_apply])
        p.addSeparator()
        p.addAction(self.act_crop_dialog)

        d = m.addMenu("Document")
        d.addActions([self.act_merge, self.act_split])
        d.addSeparator()
        d.addActions([self.act_compress, self.act_watermark, self.act_image_wm, self.act_page_numbers, self.act_header_footer])
        d.addSeparator()
        d.addActions([self.act_encrypt, self.act_decrypt, self.act_sanitize])
        d.addSeparator()
        d.addActions([self.act_ocr, self.act_redact_text, self.act_redact_apply])

        x = m.addMenu("Export")
        for a in (self.act_export, self.act_export_docx, self.act_export_xlsx,
                  self.act_export_html, self.act_export_png, self.act_images_to_pdf):
            x.addAction(a)

        a = m.addMenu("Advanced")
        a.addActions([self.act_forms_fill, self.act_compare, self.act_batch, self.act_tts])
        a.addSeparator()
        a.addActions([self.act_metadata, self.act_add_bookmark, self.act_hyperlink])

        h = m.addMenu("Help")
        h.addAction(self.act_about)

        return m

    # ============== actions ==============
    def _build_actions(self):
        A = QAction
        # File
        self.act_open = A(icons.folder_icon(), "&Open...", self); self.act_open.setShortcut(QKeySequence.Open)
        self.act_save = A(icons.save_icon(), "&Save", self); self.act_save.setShortcut(QKeySequence.Save)
        self.act_save_as = A(icons.save_icon(), "Save &as...", self); self.act_save_as.setShortcut(QKeySequence.SaveAs)
        self.act_close = A("Close tab", self); self.act_close.setShortcut("Ctrl+W")
        self.act_quit = A("Exit", self); self.act_quit.setShortcut("Ctrl+Q")
        self.act_print = A(icons.print_icon(), "Print...", self); self.act_print.setShortcut(QKeySequence.Print)

        # Edit
        self.act_undo = A(icons.undo_icon(), "Undo", self); self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo = A(icons.redo_icon(), "Redo", self); self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_find = A(icons.search_icon(), "Find", self); self.act_find.setShortcut(QKeySequence.Find)
        self.act_find_replace = A("Find & replace", self); self.act_find_replace.setShortcut("Ctrl+H")

        # View
        self.act_zoom_in = A(icons.zoom_in_icon(), "Zoom in", self); self.act_zoom_in.setShortcut("Ctrl+=")
        self.act_zoom_out = A(icons.zoom_out_icon(), "Zoom out", self); self.act_zoom_out.setShortcut("Ctrl+-")
        self.act_fit_width = A("Fit width", self); self.act_fit_width.setShortcut("Ctrl+1")
        self.act_fit_page = A("Fit page", self); self.act_fit_page.setShortcut("Ctrl+0")
        self.act_actual = A("Actual size", self); self.act_actual.setShortcut("Ctrl+2")
        self.act_prev_page = A("Previous page", self); self.act_prev_page.setShortcut("PgUp")
        self.act_next_page = A("Next page", self); self.act_next_page.setShortcut("PgDown")

        # View modes
        view_mode_group = QActionGroup(self); view_mode_group.setExclusive(True)
        self.act_view_continuous = A("Continuous", self); self.act_view_continuous.setCheckable(True); self.act_view_continuous.setChecked(True)
        self.act_view_single = A("Single page", self); self.act_view_single.setCheckable(True)
        self.act_view_two_page = A("Two-page spread", self); self.act_view_two_page.setCheckable(True)
        for a in (self.act_view_continuous, self.act_view_single, self.act_view_two_page):
            view_mode_group.addAction(a)
        self.act_view_continuous.triggered.connect(lambda: self._set_view_mode(ViewMode.CONTINUOUS))
        self.act_view_single.triggered.connect(lambda: self._set_view_mode(ViewMode.SINGLE))
        self.act_view_two_page.triggered.connect(lambda: self._set_view_mode(ViewMode.TWO_PAGE))
        self.act_reading_mode = A("Reading mode", self); self.act_reading_mode.setShortcut("F11")
        self.act_reading_mode.triggered.connect(self._toggle_reading_mode)

        # Tools (mutually exclusive)
        self.tool_group = QActionGroup(self)
        def tact(icon_fn, name, tool, shortcut=None):
            a = A(icon_fn(), name, self); a.setCheckable(True)
            a.triggered.connect(lambda: self._set_tool(tool))
            self.tool_group.addAction(a)
            if shortcut: a.setShortcut(shortcut)
            return a
        self.act_t_select = tact(icons.select_icon, "Select", Tool.SELECT, "V"); self.act_t_select.setChecked(True)
        self.act_t_hand = tact(icons.hand_icon, "Hand", Tool.HAND, "H")
        self.act_t_text = tact(icons.text_icon, "Add text", Tool.TEXT, "Shift+T")
        self.act_t_edit_text = tact(icons.text_icon, "Edit existing text", Tool.EDIT_TEXT, "Shift+E")
        self.act_t_note = tact(icons.note_icon, "Sticky note", Tool.NOTE)
        self.act_t_highlight = tact(icons.highlight_icon, "Highlight", Tool.HIGHLIGHT, "Shift+H")
        self.act_t_underline = tact(icons.underline_icon, "Underline", Tool.UNDERLINE)
        self.act_t_strike = tact(icons.strike_icon, "Strikeout", Tool.STRIKEOUT)
        self.act_t_squiggly = tact(icons.underline_icon, "Squiggly", Tool.SQUIGGLY)
        self.act_t_draw = tact(icons.draw_icon, "Draw", Tool.DRAW, "Shift+D")
        self.act_t_rect = tact(icons.rect_icon, "Rectangle", Tool.RECT)
        self.act_t_oval = tact(icons.rect_icon, "Oval", Tool.OVAL)
        self.act_t_line = tact(icons.draw_icon, "Line", Tool.LINE)
        self.act_t_arrow = tact(icons.draw_icon, "Arrow", Tool.ARROW)
        self.act_t_polygon = tact(icons.rect_icon, "Polygon", Tool.POLYGON)
        self.act_t_callout = tact(icons.comment_icon, "Callout", Tool.CALLOUT)
        self.act_t_image = tact(icons.image_icon, "Insert image", Tool.IMAGE)
        self.act_t_sign = tact(icons.sign_icon, "Sign", Tool.SIGNATURE)
        self.act_t_stamp = tact(icons.bookmark_icon, "Stamp", Tool.STAMP)
        self.act_t_redact = tact(icons.redact_icon, "Redact", Tool.REDACT)
        self.act_t_redact_mark = tact(icons.redact_icon, "Mark for redaction", Tool.REDACT_MARK)
        self.act_t_crop = tact(icons.rect_icon, "Crop page", Tool.CROP)
        self.act_t_link = tact(icons.attach_icon, "Link", Tool.LINK)
        self.act_t_measure_dist = tact(icons.draw_icon, "Measure distance", Tool.MEASURE_DIST)
        self.act_t_measure_area = tact(icons.rect_icon, "Measure area", Tool.MEASURE_AREA)
        self.act_t_text_select = tact(icons.text_icon, "Select text", Tool.TEXT_SELECT)
        self.act_t_eraser = tact(icons.redact_icon, "Erase annotation", Tool.ERASER)

        # Rotations
        self.act_rot_l = A(icons.rotate_left_icon(), "Rotate left", self)
        self.act_rot_r = A(icons.rotate_right_icon(), "Rotate right", self)
        self.act_rotate_all = A("Rotate all pages...", self)

        # Doc ops
        self.act_merge = A(icons.merge_icon(), "Combine PDFs", self)
        self.act_split = A(icons.split_icon(), "Split file", self)
        self.act_compress = A(icons.compress_icon(), "Compress", self)
        self.act_encrypt = A(icons.lock_icon(), "Password protect", self)
        self.act_decrypt = A("Remove password", self)
        self.act_ocr = A(icons.ocr_icon(), "Make searchable (OCR)", self)
        self.act_watermark = A(icons.watermark_icon(), "Text watermark", self)
        self.act_image_wm = A("Image watermark", self)
        self.act_page_numbers = A("Page numbers", self)
        self.act_header_footer = A("Headers & footers", self)
        self.act_redact_text = A("Redact by text", self)
        self.act_redact_apply = A("Apply marked redactions", self)
        self.act_sanitize = A("Sanitize document", self)

        # Pages
        self.act_insert_blank = A("Insert blank page", self)
        self.act_delete_page = A("Delete current page", self); self.act_delete_page.setShortcut("Ctrl+Shift+D")
        self.act_extract = A("Extract pages...", self)
        self.act_insert_pages = A("Insert pages from PDF...", self)
        self.act_replace_page = A("Replace current page...", self)
        self.act_reorder_apply = A("Apply thumbnail order", self)
        self.act_crop_dialog = A("Crop margins...", self)

        # Export
        self.act_export = A(icons.export_icon(), "Export...", self)
        self.act_export_docx = A("Export to Word (.docx)", self)
        self.act_export_xlsx = A("Export to Excel (.xlsx)", self)
        self.act_export_html = A("Export to HTML", self)
        self.act_export_png = A("Export as PNG images", self)
        self.act_images_to_pdf = A(icons.image_icon(), "Build PDF from images", self)

        # Advanced
        self.act_metadata = A("Document properties", self)
        self.act_add_bookmark = A("Add bookmark", self); self.act_add_bookmark.setShortcut("Ctrl+B")
        self.act_hyperlink = A("Create hyperlink", self); self.act_hyperlink.setShortcut("Ctrl+K")
        self.act_forms_fill = A("Fill form fields", self)
        self.act_compare = A("Compare PDFs", self)
        self.act_batch = A("Batch processor", self)
        self.act_tts = A("Read aloud", self); self.act_tts.setShortcut("Ctrl+Shift+R")

        self.act_about = A("About", self)

        # ---- wire up ----
        self.act_open.triggered.connect(self.open_file)
        self.act_save.triggered.connect(self.save)
        self.act_save_as.triggered.connect(self.save_as)
        self.act_close.triggered.connect(self._close_current_tab)
        self.act_quit.triggered.connect(self.close)
        self.act_print.triggered.connect(self.print_pdf)
        self.act_undo.triggered.connect(self.undo)
        self.act_redo.triggered.connect(self.redo)
        self.act_find.triggered.connect(self._toggle_search)
        self.act_find_replace.triggered.connect(self._do_find_replace)
        self.act_zoom_in.triggered.connect(lambda: self._on_view(lambda v: v.zoom_in()))
        self.act_zoom_out.triggered.connect(lambda: self._on_view(lambda v: v.zoom_out()))
        self.act_fit_width.triggered.connect(lambda: self._on_view(lambda v: v.fit_width()))
        self.act_fit_page.triggered.connect(lambda: self._on_view(lambda v: v.fit_page()))
        self.act_actual.triggered.connect(lambda: self._on_view(lambda v: v.set_zoom(1.0)))
        self.act_prev_page.triggered.connect(lambda: self._on_view(lambda v: v.goto_page(v.current_page_index() - 1)))
        self.act_next_page.triggered.connect(lambda: self._on_view(lambda v: v.goto_page(v.current_page_index() + 1)))
        self.act_rot_l.triggered.connect(lambda: self._rotate_current(-90))
        self.act_rot_r.triggered.connect(lambda: self._rotate_current(90))
        self.act_rotate_all.triggered.connect(self._do_rotate_all)
        self.act_merge.triggered.connect(self._do_merge)
        self.act_split.triggered.connect(self._do_split)
        self.act_compress.triggered.connect(self._do_compress)
        self.act_encrypt.triggered.connect(self._do_encrypt)
        self.act_decrypt.triggered.connect(self._do_decrypt)
        self.act_ocr.triggered.connect(self._do_ocr)
        self.act_watermark.triggered.connect(self._do_watermark)
        self.act_image_wm.triggered.connect(self._do_image_watermark)
        self.act_page_numbers.triggered.connect(self._do_page_numbers)
        self.act_header_footer.triggered.connect(self._do_header_footer)
        self.act_redact_text.triggered.connect(self._do_redact_text)
        self.act_redact_apply.triggered.connect(self._apply_pending_redactions)
        self.act_sanitize.triggered.connect(self._do_sanitize)
        self.act_insert_blank.triggered.connect(self._insert_blank)
        self.act_delete_page.triggered.connect(self._delete_current)
        self.act_extract.triggered.connect(self._extract_pages_prompt)
        self.act_insert_pages.triggered.connect(self._do_insert_pages)
        self.act_replace_page.triggered.connect(self._do_replace_page)
        self.act_reorder_apply.triggered.connect(self._apply_thumb_order)
        self.act_crop_dialog.triggered.connect(self._do_crop_margins)
        self.act_export.triggered.connect(self._do_export)
        self.act_export_docx.triggered.connect(self._do_export_docx)
        self.act_export_xlsx.triggered.connect(self._do_export_xlsx)
        self.act_export_html.triggered.connect(self._do_export_html)
        self.act_export_png.triggered.connect(self._do_export_png)
        self.act_images_to_pdf.triggered.connect(self._do_images_to_pdf)
        self.act_metadata.triggered.connect(self._edit_metadata)
        self.act_add_bookmark.triggered.connect(self._do_add_bookmark)
        self.act_hyperlink.triggered.connect(self._do_hyperlink)
        self.act_forms_fill.triggered.connect(self._do_forms_fill)
        self.act_compare.triggered.connect(self._do_compare)
        self.act_batch.triggered.connect(self._do_batch)
        self.act_tts.triggered.connect(self._do_tts)
        self.act_t_sign.triggered.connect(self._maybe_pick_signature)
        self.act_t_image.triggered.connect(self._maybe_pick_image)
        self.act_t_stamp.triggered.connect(self._maybe_pick_stamp)
        self.act_t_link.triggered.connect(self._maybe_pick_link_target)
        self.act_about.triggered.connect(self._about)

    # ============== toolbar ==============
    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setIconSize(QSize(22, 22)); tb.setMovable(False)
        self.addToolBar(tb)
        tb.addActions([self.act_open, self.act_save, self.act_print])
        tb.addSeparator()
        tb.addActions([self.act_undo, self.act_redo])
        tb.addSeparator()
        tb.addAction(self.act_prev_page)
        self.page_indicator = QLineEdit("1"); self.page_indicator.setFixedWidth(46); self.page_indicator.setAlignment(Qt.AlignCenter)
        self.page_indicator.returnPressed.connect(self._goto_page_from_indicator)
        tb.addWidget(self.page_indicator)
        self.of_label = QLabel(" / 0"); tb.addWidget(self.of_label)
        tb.addAction(self.act_next_page)
        tb.addSeparator()
        tb.addActions([self.act_zoom_out, self.act_zoom_in])
        self.zoom_combo = QComboBox(); self.zoom_combo.setEditable(True); self.zoom_combo.setMinimumWidth(110)
        for z in ("50%", "75%", "100%", "125%", "150%", "200%", "300%", "Fit width", "Fit page"):
            self.zoom_combo.addItem(z)
        self.zoom_combo.setCurrentText("125%")
        self.zoom_combo.activated.connect(self._on_zoom_combo)
        tb.addWidget(self.zoom_combo)
        tb.addSeparator()
        tb.addActions([self.act_rot_l, self.act_rot_r])
        tb.addSeparator()

        # view modes
        for a in (self.act_view_continuous, self.act_view_single, self.act_view_two_page):
            b = QToolButton(); b.setDefaultAction(a); b.setIconSize(QSize(20, 20))
            tb.addWidget(b)
        tb.addSeparator()
        tb.addAction(self.act_find)
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); tb.addWidget(spacer)
        # quick utility actions on the right
        tb.addAction(self.act_tts)

    def _build_property_strip(self):
        strip = QFrame(); strip.setObjectName("PropertyStrip")
        h = QHBoxLayout(strip); h.setContentsMargins(8, 4, 8, 4); h.setSpacing(2)

        for a in (self.act_t_select, self.act_t_hand, self.act_t_text_select):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())
        for a in (self.act_t_text, self.act_t_edit_text, self.act_t_note, self.act_t_callout):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())
        for a in (self.act_t_highlight, self.act_t_underline, self.act_t_strike, self.act_t_squiggly):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())
        for a in (self.act_t_draw, self.act_t_rect, self.act_t_oval, self.act_t_line,
                  self.act_t_arrow, self.act_t_polygon, self.act_t_eraser):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())
        for a in (self.act_t_image, self.act_t_sign, self.act_t_stamp):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())
        for a in (self.act_t_redact, self.act_t_redact_mark, self.act_t_crop, self.act_t_link):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())
        for a in (self.act_t_measure_dist, self.act_t_measure_area):
            h.addWidget(self._tool_btn(a))
        h.addWidget(self._sep())

        h.addWidget(QLabel(" Color:"))
        self.color_btn = QPushButton(""); self.color_btn.setFixedSize(28, 22); self.color_btn.setObjectName("flat")
        self.color_btn.clicked.connect(self._pick_color)
        h.addWidget(self.color_btn)

        h.addWidget(QLabel(" Text:"))
        self.text_size_spin = QSpinBox(); self.text_size_spin.setRange(6, 96); self.text_size_spin.setValue(12); self.text_size_spin.setFixedWidth(58)
        self.text_size_spin.valueChanged.connect(self._on_text_size_changed)
        h.addWidget(self.text_size_spin)

        h.addWidget(QLabel(" Stroke:"))
        self.stroke_spin = QSpinBox(); self.stroke_spin.setRange(1, 20); self.stroke_spin.setValue(2); self.stroke_spin.setFixedWidth(50)
        self.stroke_spin.valueChanged.connect(self._on_stroke_changed)
        h.addWidget(self.stroke_spin)

        h.addStretch(1)

        self.addToolBarBreak()
        wrapper = QToolBar(); wrapper.setMovable(False); wrapper.addWidget(strip)
        wrapper.setStyleSheet("QToolBar{background:#2b2b2b; border:none; padding:0;}")
        self.addToolBar(wrapper)
        self.property_strip = wrapper

        self._draw_color = QColor("#000000")
        self._refresh_color_btn()

    def _tool_btn(self, action: QAction):
        b = QToolButton(); b.setDefaultAction(action); b.setIconSize(QSize(20, 20))
        b.setToolButtonStyle(Qt.ToolButtonIconOnly)
        return b

    def _sep(self):
        s = QFrame(); s.setFrameShape(QFrame.VLine); s.setStyleSheet("color:#404040;"); s.setFixedHeight(20)
        return s

    def _build_statusbar(self):
        sb = QStatusBar(); self.setStatusBar(sb)
        self.modified_label = QLabel(""); sb.addWidget(self.modified_label)
        self.redact_label = QLabel(""); sb.addWidget(self.redact_label)
        self.page_label = QLabel("—"); sb.addPermanentWidget(self.page_label)
        self.zoom_label = QLabel("—"); sb.addPermanentWidget(self.zoom_label)
        self.tool_label = QLabel("Select"); sb.addPermanentWidget(self.tool_label)
        self.mode_label = QLabel("Continuous"); sb.addPermanentWidget(self.mode_label)

    # ============== doc tab management ==============
    def _current_tab(self) -> Optional[DocTab]:
        i = self.tabs.currentIndex()
        if i < 0 or i >= len(self._tabs): return None
        return self._tabs[i]

    def _on_view(self, fn):
        t = self._current_tab()
        if t: fn(t.view)

    def _show_home(self):
        self.stack.setCurrentIndex(0)
        self.home.refresh_recents()
        self._update_enabled()
        self.setWindowTitle(APP_NAME)

    def _show_editor(self):
        self.stack.setCurrentIndex(1)
        self._update_enabled()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")
        if path: self.load_pdf(path)

    def load_pdf(self, path: str):
        for i, t in enumerate(self._tabs):
            if t.path and os.path.abspath(t.path) == os.path.abspath(path):
                self.tabs.setCurrentIndex(i); self._show_editor(); return
        try:
            doc = PdfDocument(path)
        except PermissionError:
            pw, ok = QInputDialog.getText(self, "Password required",
                                          f"'{os.path.basename(path)}' is encrypted.\nEnter password:",
                                          echo=QLineEdit.Password)
            if not ok: return
            try:
                doc = PdfDocument(path, password=pw)
            except Exception as e:
                QMessageBox.critical(self, "Open failed", str(e)); return
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e)); return
        self._create_tab(doc, path)
        add_recent(path)
        self.statusBar().showMessage(f"Opened {path}", 3000)

    def _new_blank(self):
        doc = PdfDocument()
        doc.insert_blank_page(0)
        self._create_tab(doc, None, modified=True, tab_name="Untitled.pdf")

    def _create_tab(self, doc: PdfDocument, path: Optional[str], *,
                    modified: bool = False, tab_name: Optional[str] = None):
        view = PdfGraphicsView()
        tab = DocTab(view=view, doc=doc, path=path, modified=modified)
        view.set_document(doc)
        view.page_changed.connect(lambda n, t=tab: self._on_view_page_changed(t, n))
        view.zoom_changed.connect(lambda z, t=tab: self._on_view_zoom_changed(t, z))
        view.document_modified.connect(lambda t=tab: self._on_view_modified(t))
        view.tool_done.connect(self._reset_select_tool)
        view.status.connect(lambda s: self.statusBar().showMessage(s, 5000))
        self._tabs.append(tab)
        name = tab_name or (os.path.basename(path) if path else "Untitled.pdf")
        if modified: name += " •"
        idx = self.tabs.addTab(view, name)
        if path: self.tabs.setTabToolTip(idx, path)
        self.tabs.setCurrentIndex(idx)
        self._show_editor()

    def _close_current_tab(self):
        i = self.tabs.currentIndex()
        if i >= 0: self._close_tab(i)

    def _close_tab(self, index: int):
        if index < 0 or index >= len(self._tabs): return
        t = self._tabs[index]
        if t.modified:
            r = QMessageBox.question(self, "Unsaved changes",
                                     f"Save changes to {os.path.basename(t.path or 'Untitled.pdf')}?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel: return
            if r == QMessageBox.Save:
                self._save_tab(t)
                if t.modified: return
        t.doc.close()
        self.tabs.removeTab(index)
        del self._tabs[index]
        if not self._tabs: self._show_home()

    def _on_tab_changed(self, idx: int):
        t = self._current_tab()
        if not t: return
        self.side.load_document(t.doc)
        rail_key = "pages"
        for k, btn in self.rail.buttons.items():
            if btn.isChecked(): rail_key = k; break
        self.side.show_panel(rail_key)
        self._update_enabled()
        self.setWindowTitle(f"{APP_NAME} — {os.path.basename(t.path or 'Untitled.pdf')}")
        self.of_label.setText(f" / {t.doc.page_count}")
        self.page_indicator.setText(str(t.view.current_page_index() + 1))
        self._on_view_zoom_changed(t, t.view.zoom)
        # sync view mode
        m = t.view.view_mode
        self.act_view_continuous.setChecked(m == ViewMode.CONTINUOUS)
        self.act_view_single.setChecked(m == ViewMode.SINGLE)
        self.act_view_two_page.setChecked(m == ViewMode.TWO_PAGE)
        self.mode_label.setText(m.value.replace("_", "-").capitalize())
        # update redaction queue label
        self._refresh_redact_label()

    def save(self):
        t = self._current_tab()
        if t: self._save_tab(t)

    def _save_tab(self, t: DocTab):
        if not t.path: return self._save_as_tab(t)
        try:
            t.doc.save(); t.modified = False
            self.modified_label.setText("")
            i = self._tabs.index(t); self.tabs.setTabText(i, os.path.basename(t.path))
            self.statusBar().showMessage("Saved", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def save_as(self):
        t = self._current_tab()
        if t: self._save_as_tab(t)

    def _save_as_tab(self, t: DocTab):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF as", t.path or "untitled.pdf", "PDF (*.pdf)")
        if not path: return
        try:
            t.doc.save_copy(path)
            t.path = path; t.doc.path = path; t.modified = False
            self.modified_label.setText("")
            i = self._tabs.index(t)
            self.tabs.setTabText(i, os.path.basename(path)); self.tabs.setTabToolTip(i, path)
            self.setWindowTitle(f"{APP_NAME} — {os.path.basename(path)}")
            add_recent(path)
            self.statusBar().showMessage(f"Saved to {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def print_pdf(self):
        t = self._current_tab()
        if not t: return
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.HighResolution)
        if QPrintDialog(printer, self).exec() != QPrintDialog.Accepted: return
        painter = QPainter(printer)
        try:
            for i in range(t.doc.page_count):
                if i > 0: printer.newPage()
                pix = QPixmap(); pix.loadFromData(t.doc.render(i, zoom=3))
                if pix.isNull(): continue
                r = painter.viewport()
                scaled = pix.scaled(r.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap((r.width()-scaled.width())//2, (r.height()-scaled.height())//2, scaled)
        finally:
            painter.end()

    # ============== view signals ==============
    def _on_view_page_changed(self, tab: DocTab, n: int):
        if tab is not self._current_tab(): return
        self.page_label.setText(f"Page {n} of {tab.doc.page_count}")
        self.of_label.setText(f" / {tab.doc.page_count}")
        self.page_indicator.blockSignals(True); self.page_indicator.setText(str(n)); self.page_indicator.blockSignals(False)

    def _on_view_zoom_changed(self, tab: DocTab, z: float):
        if tab is not self._current_tab(): return
        self.zoom_label.setText(f"{int(z*100)}%")
        self.zoom_combo.blockSignals(True); self.zoom_combo.setCurrentText(f"{int(z*100)}%"); self.zoom_combo.blockSignals(False)

    def _on_view_modified(self, tab: DocTab):
        tab.modified = True
        i = self._tabs.index(tab)
        name = os.path.basename(tab.path or "Untitled.pdf")
        self.tabs.setTabText(i, name + " •")
        if tab is self._current_tab():
            self.modified_label.setText("●  unsaved changes")
        self._refresh_redact_label()

    def _mark_modified(self):
        t = self._current_tab()
        if t: self._on_view_modified(t)

    def _refresh_redact_label(self):
        t = self._current_tab()
        if t and t.doc.pending_redactions:
            self.redact_label.setText(f" |  {len(t.doc.pending_redactions)} redaction(s) queued")
        else:
            self.redact_label.setText("")

    # ============== search ==============
    def _toggle_search(self):
        if self.search.isVisible(): self._close_search()
        else:
            self.search.show(); self.search.input.setFocus(); self.search.input.selectAll()

    def _close_search(self):
        self.search.hide(); self._search_matches = []

    def _top_search_submit(self):
        text = self.top_search.text()
        if not text: return
        self.search.input.setText(text)
        self._on_search_text(text)
        self.search.show()
        self._goto_match(+1)

    def _set_search_option(self, key: str, val: bool):
        self._search_options[key] = val
        self._on_search_text(self.search.input.text())

    def _on_search_text(self, txt: str):
        t = self._current_tab()
        if not t or not txt:
            self._search_matches = []; self._search_idx = -1
            self.search.status.setText(""); return
        self._search_matches = t.doc.search(
            txt, case_sensitive=self._search_options["case_sensitive"],
            whole_words=self._search_options["whole_words"])
        self._search_idx = -1
        self.search.status.setText(f"{len(self._search_matches)} found")

    def _goto_match(self, delta: int):
        if not self._search_matches: return
        self._search_idx = (self._search_idx + delta) % len(self._search_matches)
        page_idx, _ = self._search_matches[self._search_idx]
        t = self._current_tab()
        if t: t.view.goto_page(page_idx)
        self.search.status.setText(f"{self._search_idx+1} of {len(self._search_matches)}")

    # ============== nav rail ==============
    def _on_rail_selected(self, key: str):
        if not key: self.side.setVisible(False); return
        self.side.setVisible(True); self.side.show_panel(key)

    def _side_goto_page(self, page_index: int):
        t = self._current_tab()
        if t: t.view.goto_page(page_index)

    # ============== undo / redo ==============
    def undo(self):
        t = self._current_tab()
        if t and t.doc.can_undo():
            t.doc.undo(); t.view.reload_all(); self.side.refresh(); self._mark_modified()

    def redo(self):
        t = self._current_tab()
        if t and t.doc.can_redo():
            t.doc.redo(); t.view.reload_all(); self.side.refresh(); self._mark_modified()

    # ============== view modes ==============
    def _set_view_mode(self, mode: ViewMode):
        t = self._current_tab()
        if t:
            t.view.set_view_mode(mode)
            self.mode_label.setText(mode.value.replace("_", "-").capitalize())

    def _toggle_reading_mode(self):
        chrome = (self.menuWidget(), self.statusBar())
        toolbars = self.findChildren(QToolBar)
        if self._reading_mode_chrome is None:
            self._reading_mode_chrome = {
                "menu": True, "status": True,
                "toolbars": [(tb, tb.isVisible()) for tb in toolbars],
                "rail": self.rail.isVisible(),
                "side": self.side.isVisible(),
                "tools": self.tools.isVisible(),
                "fullscreen": self.isFullScreen(),
            }
            if self.menuWidget(): self.menuWidget().hide()
            for tb in toolbars: tb.hide()
            self.rail.hide(); self.side.hide(); self.tools.hide()
            self.showFullScreen()
            self.statusBar().showMessage("Press F11 or Esc to exit reading mode", 5000)
        else:
            if self.menuWidget(): self.menuWidget().show()
            for tb, vis in self._reading_mode_chrome["toolbars"]: tb.setVisible(vis)
            self.rail.setVisible(self._reading_mode_chrome["rail"])
            self.side.setVisible(self._reading_mode_chrome["side"])
            self.tools.setVisible(self._reading_mode_chrome["tools"])
            if not self._reading_mode_chrome["fullscreen"]: self.showNormal()
            self._reading_mode_chrome = None

    # ============== zoom / page ==============
    def _on_zoom_combo(self):
        v = self.zoom_combo.currentText().strip()
        t = self._current_tab()
        if not t: return
        if v == "Fit width": t.view.fit_width(); return
        if v == "Fit page": t.view.fit_page(); return
        try:
            t.view.set_zoom(int(v.replace("%", "").strip()) / 100)
        except ValueError: pass

    def _goto_page_from_indicator(self):
        t = self._current_tab()
        if not t: return
        try:
            i = int(self.page_indicator.text()) - 1
            t.view.goto_page(max(0, min(t.doc.page_count - 1, i)))
        except ValueError: pass

    # ============== tools ==============
    def _set_tool(self, tool: Tool):
        t = self._current_tab()
        if t: t.view.set_tool(tool)
        self.tool_label.setText(tool.value.replace("_", " ").capitalize())

    def _reset_select_tool(self):
        self.act_t_select.setChecked(True); self._set_tool(Tool.SELECT)

    def _on_text_size_changed(self, v: int):
        for t in self._tabs: t.view.text_size = v

    def _on_stroke_changed(self, v: int):
        for t in self._tabs: t.view.draw_width = float(v)

    def _pick_color(self):
        c = QColorDialog.getColor(self._draw_color, self, "Pick color")
        if c.isValid():
            self._draw_color = c
            for t in self._tabs: t.view.draw_color = c
            self._refresh_color_btn()

    def _refresh_color_btn(self):
        c = self._draw_color
        self.color_btn.setStyleSheet(f"background:{c.name()}; border:1px solid #555; border-radius:3px;")

    def _maybe_pick_signature(self):
        if not self._current_tab():
            QMessageBox.information(self, "Sign", "Open a PDF first"); self._reset_select_tool(); return
        if self._signature_pix is None:
            d = SignatureDialog(self)
            if d.exec() != SignatureDialog.Accepted or d.result_pixmap is None:
                self._reset_select_tool(); return
            self._signature_pix = d.result_pixmap
        self._current_tab().view.set_signature(self._signature_pix)
        self.statusBar().showMessage("Drag a rectangle to place your signature", 4000)

    def _maybe_pick_image(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Image", "Open a PDF first"); self._reset_select_tool(); return
        path, _ = QFileDialog.getOpenFileName(self, "Image to insert", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path: self._reset_select_tool(); return
        t.view.set_image_to_place(path)
        self.statusBar().showMessage("Drag a rectangle to place the image", 4000)

    def _maybe_pick_stamp(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Stamp", "Open a PDF first"); self._reset_select_tool(); return
        dlg = StampsDialog(self)
        chosen = {"pix": None}
        dlg.chosen.connect(lambda p: chosen.update(pix=p))
        dlg.exec()
        if chosen["pix"] is None:
            self._reset_select_tool(); return
        t.view.set_stamp(chosen["pix"])
        self.statusBar().showMessage("Drag a rectangle to place the stamp", 4000)

    def _maybe_pick_link_target(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Link", "Open a PDF first"); self._reset_select_tool(); return
        d = HyperlinkDialog(t.doc.page_count, self)
        if d.exec() != HyperlinkDialog.Accepted:
            self._reset_select_tool(); return
        t.view.set_link_target(d.target())
        self.statusBar().showMessage("Drag a rectangle for the clickable area", 4000)

    # ============== tools panel actions ==============
    def _on_tool_action(self, key: str):
        mapping = {
            # Edit
            "edit_text":     lambda: self._fire_tool(self.act_t_edit_text, Tool.EDIT_TEXT),
            "add_text":      lambda: self._fire_tool(self.act_t_text, Tool.TEXT),
            "insert_image":  self._maybe_pick_image,
            "crop":          lambda: self._fire_tool(self.act_t_crop, Tool.CROP),
            "crop_all":      self._do_crop_margins,
            "header_footer": self._do_header_footer,
            "hyperlink":     self._maybe_pick_link_target,
            "add_bookmark":  self._do_add_bookmark,
            "find_replace":  self._do_find_replace,
            "metadata":      self._edit_metadata,

            # Comment
            "highlight":     lambda: self._fire_tool(self.act_t_highlight, Tool.HIGHLIGHT),
            "underline":     lambda: self._fire_tool(self.act_t_underline, Tool.UNDERLINE),
            "strikeout":     lambda: self._fire_tool(self.act_t_strike, Tool.STRIKEOUT),
            "squiggly":      lambda: self._fire_tool(self.act_t_squiggly, Tool.SQUIGGLY),
            "note":          lambda: self._fire_tool(self.act_t_note, Tool.NOTE),
            "callout":       lambda: self._fire_tool(self.act_t_callout, Tool.CALLOUT),
            "draw":          lambda: self._fire_tool(self.act_t_draw, Tool.DRAW),
            "rect":          lambda: self._fire_tool(self.act_t_rect, Tool.RECT),
            "oval":          lambda: self._fire_tool(self.act_t_oval, Tool.OVAL),
            "line":          lambda: self._fire_tool(self.act_t_line, Tool.LINE),
            "arrow":         lambda: self._fire_tool(self.act_t_arrow, Tool.ARROW),
            "polygon":       lambda: self._fire_tool(self.act_t_polygon, Tool.POLYGON),
            "eraser":        lambda: self._fire_tool(self.act_t_eraser, Tool.ERASER),
            "stamp":         self._maybe_pick_stamp,

            # Fill & Sign
            "signature":     self._maybe_pick_signature,
            "forms_fill":    self._do_forms_fill,
            "add_field":     self._add_text_field,
            "add_checkbox":  self._add_checkbox,

            # Organize
            "rotate_left":   lambda: self._rotate_current(-90),
            "rotate_right":  lambda: self._rotate_current(90),
            "rotate_all":    self._do_rotate_all,
            "insert_blank":  self._insert_blank,
            "duplicate_pg":  self._duplicate_current,
            "delete_page":   self._delete_current,
            "extract_pg":    self._extract_pages_prompt,
            "insert_pages":  self._do_insert_pages,
            "replace_page":  self._do_replace_page,
            "reorder":       self._apply_thumb_order,
            "merge":         self._do_merge,
            "split":         self._do_split,

            # Protect
            "encrypt":       self._do_encrypt,
            "decrypt":       self._do_decrypt,
            "redact_draw":   lambda: self._fire_tool(self.act_t_redact, Tool.REDACT),
            "redact_mark":   lambda: self._fire_tool(self.act_t_redact_mark, Tool.REDACT_MARK),
            "redact_apply":  self._apply_pending_redactions,
            "redact_text":   self._do_redact_text,
            "sanitize":      self._do_sanitize,
            "watermark":     self._do_watermark,
            "image_wm":      self._do_image_watermark,
            "page_numbers":  self._do_page_numbers,

            # Convert
            "compress":      self._do_compress,
            "ocr":           self._do_ocr,
            "export_docx":   self._do_export_docx,
            "export_xlsx":   self._do_export_xlsx,
            "export_html":   self._do_export_html,
            "export_png":    self._do_export_png,
            "export_txt":    self._do_export_txt,
            "images_pdf":    self._do_images_to_pdf,
            "compare":       self._do_compare,
            "batch":         self._do_batch,
            "tts":           self._do_tts,
        }
        fn = mapping.get(key)
        if fn: fn()

    def _fire_tool(self, action: QAction, tool: Tool):
        action.setChecked(True); self._set_tool(tool)

    # ============== page ops ==============
    def _rotate_current(self, deg: int):
        t = self._current_tab()
        if not t: return
        i = t.view.current_page_index()
        t.doc.rotate_page(i, deg)
        t.view.reload_all(); self.side.thumbs.refresh(i); self._mark_modified()

    def _do_rotate_all(self):
        t = self._current_tab()
        if not t: return
        items = ["All pages — 90 left", "All pages — 90 right", "All pages — 180",
                 "Odd pages — 90 right", "Even pages — 90 right"]
        choice, ok = QInputDialog.getItem(self, "Rotate all", "Apply rotation:", items, 0, False)
        if not ok: return
        deg = -90 if "90 left" in choice else 90 if "90 right" in choice else 180
        odd = "Odd pages" in choice; even = "Even pages" in choice
        t.doc.rotate_all(deg, even_only=even, odd_only=odd)
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _rotate_pages(self, indices: list, deg: int):
        t = self._current_tab()
        if not t: return
        for i in indices: t.doc.rotate_page(i, deg)
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _delete_current(self):
        t = self._current_tab()
        if not t: return
        if t.doc.page_count <= 1:
            QMessageBox.warning(self, "Delete", "Cannot delete the only page"); return
        self._delete_pages([t.view.current_page_index()])

    def _delete_pages(self, indices: list):
        t = self._current_tab()
        if not t or not indices: return
        if len(indices) >= t.doc.page_count:
            QMessageBox.warning(self, "Delete", "Cannot delete all pages"); return
        if QMessageBox.question(self, "Delete", f"Delete {len(indices)} page(s)?") != QMessageBox.Yes: return
        t.doc.delete_pages(indices)
        t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()

    def _duplicate_current(self):
        t = self._current_tab()
        if t: self._duplicate_page(t.view.current_page_index())

    def _duplicate_page(self, index: int):
        t = self._current_tab()
        if not t: return
        t.doc.duplicate_page(index)
        t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()

    def _insert_blank(self):
        t = self._current_tab()
        if not t: self._new_blank(); return
        i = t.view.current_page_index()
        t.doc.insert_blank_page(i + 1)
        t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()

    def _insert_blank_after(self, index: int):
        t = self._current_tab()
        if not t: return
        t.doc.insert_blank_page(index + 1)
        t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()

    def _extract_pages_prompt(self):
        t = self._current_tab()
        if not t: return
        txt, ok = QInputDialog.getText(self, "Extract pages", "Page range (e.g. 1-3, 5):")
        if not ok or not txt.strip(): return
        try:
            indices = self._parse_page_list(txt, t.doc.page_count)
        except Exception as e:
            QMessageBox.warning(self, "Extract", f"Bad range: {e}"); return
        self._extract_pages_list(indices)

    def _extract_pages_list(self, indices: list):
        t = self._current_tab()
        if not t: return
        out, _ = QFileDialog.getSaveFileName(self, "Save extracted pages", "extracted.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            t.doc.extract_pages(indices, out)
            QMessageBox.information(self, "Extract", f"Saved to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Extract failed", str(e))

    def _parse_page_list(self, txt: str, total: int) -> list[int]:
        out = []
        for part in txt.split(","):
            part = part.strip()
            if "-" in part:
                a, b = [int(x) - 1 for x in part.split("-")]
                out.extend(range(a, b + 1))
            else:
                out.append(int(part) - 1)
        if any(i < 0 or i >= total for i in out):
            raise ValueError("out of range")
        return out

    def _apply_thumb_order(self):
        t = self._current_tab()
        if not t: return
        order = self.side.thumbs.get_page_order()
        if order == list(range(t.doc.page_count)):
            self.statusBar().showMessage("No reorder needed", 2000); return
        import fitz
        new = fitz.open()
        for src_idx in order:
            new.insert_pdf(t.doc.doc, from_page=src_idx, to_page=src_idx)
        old = t.doc.doc
        t.doc.snapshot(); t.doc.doc = new; old.close()
        t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()

    def _do_crop_margins(self):
        t = self._current_tab()
        if not t: return
        d = CropDialog(self)
        if d.exec() != CropDialog.Accepted: return
        if d.is_reset():
            t.doc.reset_crop()
        else:
            t.doc.crop_all(d.margins(), mode="margins")
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _do_insert_pages(self):
        t = self._current_tab()
        if not t: return
        d = InsertPagesDialog(t.view.current_page_index(), t.doc.page_count, self)
        if d.exec() != InsertPagesDialog.Accepted: return
        s = d.settings()
        if not os.path.isfile(s["source"]):
            QMessageBox.warning(self, "Insert", "Pick a source PDF first"); return
        try:
            t.doc.insert_pdf(s["source"], s["at_index"], s["from_page"], s["to_page"])
            t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()
        except Exception as e:
            QMessageBox.critical(self, "Insert failed", str(e))

    def _do_replace_page(self):
        t = self._current_tab()
        if not t: return
        d = ReplacePageDialog(t.view.current_page_index(), self)
        if d.exec() != ReplacePageDialog.Accepted: return
        s = d.settings()
        if not os.path.isfile(s["source"]):
            QMessageBox.warning(self, "Replace", "Pick a source PDF"); return
        try:
            t.doc.replace_page(t.view.current_page_index(), s["source"], s["page"])
            t.view.set_document(t.doc); self.side.load_document(t.doc); self._mark_modified()
        except Exception as e:
            QMessageBox.critical(self, "Replace failed", str(e))

    # ============== document ops ==============
    def _need_doc(self):
        if not self._current_tab():
            QMessageBox.information(self, APP_NAME, "Open a PDF first"); return False
        return True

    def _do_merge(self):
        MergeDialog(self).exec()

    def _do_split(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Split", "Save the PDF first"); return
        SplitDialog(t.path, t.doc.page_count, self).exec()

    def _do_compress(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Compress", "Save the PDF first"); return
        CompressDialog(t.path, self).exec()

    def _do_encrypt(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Protect", "Save the PDF first"); return
        EncryptDialog(t.path, self).exec()

    def _do_decrypt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Encrypted PDF", "", "PDF (*.pdf)")
        if not path: return
        pw, ok = QInputDialog.getText(self, "Password", "Password:", echo=QLineEdit.Password)
        if not ok: return
        out, _ = QFileDialog.getSaveFileName(self, "Save decrypted",
                                             f"{Path(path).stem}_decrypted.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            from .pdf_engine import decrypt_pdf
            decrypt_pdf(path, out, pw)
            QMessageBox.information(self, "Decrypt", f"Saved to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Decrypt failed", str(e))

    def _do_ocr(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "OCR", "Save the PDF first"); return
        OcrDialog(t.path, self).exec()

    def _do_watermark(self):
        if not self._need_doc(): return
        d = WatermarkDialog(self)
        if d.exec() != WatermarkDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_watermark(s["text"], opacity=s["opacity"], fontsize=s["fontsize"],
                            color=s["color"], rotation=s["rotation"])
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _do_image_watermark(self):
        if not self._need_doc(): return
        d = ImageWatermarkDialog(self)
        if d.exec() != ImageWatermarkDialog.Accepted: return
        s = d.settings()
        if not os.path.isfile(s["image_path"]):
            QMessageBox.warning(self, "Watermark", "Pick a valid image"); return
        t = self._current_tab()
        try:
            t.doc.add_image_watermark(s["image_path"], opacity=s["opacity"],
                                      scale=s["scale"], rotation=s["rotation"])
            t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()
        except Exception as e:
            QMessageBox.critical(self, "Watermark failed", str(e))

    def _do_page_numbers(self):
        if not self._need_doc(): return
        d = PageNumbersDialog(self)
        if d.exec() != PageNumbersDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_page_numbers(start=s["start"], fontsize=s["fontsize"],
                               position=s["position"], pattern=s["pattern"])
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _do_header_footer(self):
        if not self._need_doc(): return
        d = HeaderFooterDialog(self)
        if d.exec() != HeaderFooterDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_header_footer(**s)
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _do_redact_text(self):
        if not self._need_doc(): return
        d = RedactTextDialog(self)
        if d.exec() != RedactTextDialog.Accepted: return
        terms = d.terms()
        if not terms: return
        t = self._current_tab(); total = 0
        for term in terms:
            total += t.doc.redact_text(term, case_sensitive=d.case.isChecked())
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()
        QMessageBox.information(self, "Redact", f"Redacted {total} occurrence(s).")

    def _apply_pending_redactions(self):
        t = self._current_tab()
        if not t: return
        n = t.view.apply_redact_marks()
        if n == 0:
            QMessageBox.information(self, "Redact", "Nothing to apply.\n"
                                    "Use the Mark for redaction tool first.")
        else:
            self.statusBar().showMessage(f"Applied {n} redaction(s)", 4000)
            self.side.thumbs.refresh()
        self._refresh_redact_label()

    def _do_sanitize(self):
        t = self._current_tab()
        if not t: return
        d = SanitizeDialog(self)
        if d.exec() != SanitizeDialog.Accepted: return
        t.doc.sanitize()
        self._mark_modified()
        QMessageBox.information(self, "Sanitize", "Document sanitized.")

    def _do_find_replace(self):
        t = self._current_tab()
        if not t: return
        d = FindReplaceDialog(self)
        if d.exec() != FindReplaceDialog.Accepted: return
        s = d.settings()
        if not s["find"]:
            QMessageBox.warning(self, "Replace", "Enter text to find"); return
        n = t.doc.find_and_replace(s["find"], s["replace"], case_sensitive=s["case_sensitive"])
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()
        QMessageBox.information(self, "Replace", f"Replaced {n} occurrence(s).")

    def _do_add_bookmark(self):
        t = self._current_tab()
        if not t: return
        d = AddBookmarkDialog(t.view.current_page_index(), self)
        if d.exec() != AddBookmarkDialog.Accepted: return
        s = d.settings()
        if not s["title"]: return
        t.doc.add_bookmark(s["title"], s["page"], level=s["level"])
        self.side.bookmarks.load(t.doc)
        self._mark_modified()

    def _do_hyperlink(self):
        self._maybe_pick_link_target()

    # ============== forms ==============
    def _do_forms_fill(self):
        t = self._current_tab()
        if not t: return
        if not t.doc.list_form_fields():
            QMessageBox.information(self, "Forms", "This PDF has no fillable form fields.\n"
                                    "Use 'Add text field' or 'Add checkbox' to create some.")
            return
        d = FormFillDialog(t.doc, self)
        def refresh():
            t.view.reload_all(); self._mark_modified()
        d.fields_updated.connect(refresh)
        d.exec()

    def _add_text_field(self):
        t = self._current_tab()
        if not t: return
        # add a placeholder field at current page top-left
        i = t.view.current_page_index()
        info = t.doc.page_info(i)
        # pick a center-ish rect
        rect = (info.width * 0.2, info.height * 0.2, info.width * 0.6, info.height * 0.2 + 24)
        name, ok = QInputDialog.getText(self, "Field name", "Field name:", text=f"field_{i+1}")
        if not ok or not name: return
        t.doc.add_form_text_field(i, rect, name, value="")
        t.view.reload_all(); self._mark_modified()
        QMessageBox.information(self, "Form field",
                                f"Text field '{name}' added to page {i+1}. Use Fill form fields to enter values.")

    def _add_checkbox(self):
        t = self._current_tab()
        if not t: return
        i = t.view.current_page_index()
        info = t.doc.page_info(i)
        rect = (info.width * 0.2, info.height * 0.3, info.width * 0.2 + 18, info.height * 0.3 + 18)
        name, ok = QInputDialog.getText(self, "Field name", "Checkbox name:", text=f"check_{i+1}")
        if not ok or not name: return
        t.doc.add_form_checkbox(i, rect, name, checked=False)
        t.view.reload_all(); self._mark_modified()

    # ============== export ==============
    def _do_export(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        ExportDialog(t.path, self).exec()

    def _do_export_docx(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save Word", f"{Path(t.path).stem}.docx", "Word (*.docx)")
        if not out: return
        try:
            from .converters import pdf_to_docx
            pdf_to_docx(t.path, out)
            QMessageBox.information(self, "Export", f"Saved to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _do_export_xlsx(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save Excel", f"{Path(t.path).stem}.xlsx", "Excel (*.xlsx)")
        if not out: return
        try:
            from .converters import pdf_to_xlsx
            n = pdf_to_xlsx(t.path, out)
            QMessageBox.information(self, "Export", f"Saved to {out}\nExtracted {n} table(s).")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _do_export_html(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save HTML", f"{Path(t.path).stem}.html", "HTML (*.html)")
        if not out: return
        try:
            from .converters import pdf_to_html
            pdf_to_html(t.path, out)
            QMessageBox.information(self, "Export", f"Saved to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _do_export_png(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        out_dir = QFileDialog.getExistingDirectory(self, "Output folder")
        if not out_dir: return
        try:
            from .pdf_engine import pdf_to_images
            files = pdf_to_images(t.path, out_dir, fmt="png", dpi=200)
            QMessageBox.information(self, "Export", f"Wrote {len(files)} PNG(s) to {out_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _do_export_txt(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save text", f"{Path(t.path).stem}.txt", "Text (*.txt)")
        if not out: return
        try:
            from .pdf_engine import extract_text
            extract_text(t.path, out)
            QMessageBox.information(self, "Export", f"Saved to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def _do_images_to_pdf(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select images", "",
                                                "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not files: return
        out, _ = QFileDialog.getSaveFileName(self, "Save PDF", "images.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            from .pdf_engine import images_to_pdf
            images_to_pdf(files, out)
            if QMessageBox.question(self, "Done", f"Saved to {out}\n\nOpen now?") == QMessageBox.Yes:
                self.load_pdf(out)
        except Exception as e:
            QMessageBox.critical(self, "Convert failed", str(e))

    def _edit_metadata(self):
        if not self._need_doc(): return
        t = self._current_tab()
        m = t.doc.metadata()
        dlg = QDialog(self); dlg.setWindowTitle("Document properties")
        f = QFormLayout(dlg); fields = {}
        for key in ("title", "author", "subject", "keywords", "creator", "producer"):
            le = QLineEdit(str(m.get(key, "") or ""))
            f.addRow(key.capitalize() + ":", le); fields[key] = le
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); f.addRow(bb)
        if dlg.exec() == QDialog.Accepted:
            m.update({k: v.text() for k, v in fields.items()})
            t.doc.set_metadata(m); self._mark_modified()

    # ============== compare / batch / TTS ==============
    def _do_compare(self):
        t = self._current_tab()
        CompareDialog(t.path if t else "", self).exec()

    def _do_batch(self):
        BatchDialog(self).exec()

    def _do_tts(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Read aloud", "Open a PDF first"); return
        if self._tts_dialog is None:
            self._tts_dialog = TtsDialog(self)
        self._tts_dialog.set_text_provider(lambda: [
            (i, t.doc.get_text(i)) for i in range(t.doc.page_count)
            if t.doc.get_text(i).strip()
        ])
        self._tts_dialog.show()
        self._tts_dialog.raise_()
        self._tts_dialog.activateWindow()

    # ============== state ==============
    def _update_enabled(self):
        on = self._current_tab() is not None
        self.tools.set_enabled_all(on)
        for a in (self.act_save, self.act_save_as, self.act_close, self.act_print,
                  self.act_undo, self.act_redo, self.act_find, self.act_find_replace,
                  self.act_zoom_in, self.act_zoom_out, self.act_fit_width,
                  self.act_fit_page, self.act_actual, self.act_prev_page, self.act_next_page,
                  self.act_view_continuous, self.act_view_single, self.act_view_two_page,
                  self.act_reading_mode,
                  self.act_rot_l, self.act_rot_r, self.act_rotate_all,
                  self.act_split, self.act_compress, self.act_encrypt, self.act_ocr,
                  self.act_watermark, self.act_image_wm, self.act_page_numbers,
                  self.act_header_footer, self.act_redact_text, self.act_redact_apply,
                  self.act_sanitize, self.act_insert_blank, self.act_delete_page,
                  self.act_extract, self.act_insert_pages, self.act_replace_page,
                  self.act_reorder_apply, self.act_crop_dialog,
                  self.act_export, self.act_export_docx, self.act_export_xlsx,
                  self.act_export_html, self.act_export_png,
                  self.act_metadata, self.act_add_bookmark, self.act_hyperlink,
                  self.act_forms_fill, self.act_tts,
                  self.act_t_text, self.act_t_edit_text, self.act_t_note,
                  self.act_t_highlight, self.act_t_underline, self.act_t_strike,
                  self.act_t_squiggly, self.act_t_draw, self.act_t_rect, self.act_t_oval,
                  self.act_t_line, self.act_t_arrow, self.act_t_polygon, self.act_t_callout,
                  self.act_t_image, self.act_t_sign, self.act_t_stamp,
                  self.act_t_redact, self.act_t_redact_mark, self.act_t_crop,
                  self.act_t_link, self.act_t_measure_dist, self.act_t_measure_area,
                  self.act_t_text_select, self.act_t_eraser):
            a.setEnabled(on)

    def _about(self):
        QMessageBox.information(self, f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2><p>Version {__version__}</p>"
            "<p>A complete PDF editing suite — view, edit, annotate, sign, "
            "merge, split, compress, OCR, convert, redact, compare, and more.</p>"
            "<p>Built with PySide6, PyMuPDF, pikepdf, python-docx, openpyxl, and pyttsx3.</p>")

    # ============== DnD + close ==============
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(".pdf")
                                          for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(".pdf"): self.load_pdf(p)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._reading_mode_chrome is not None:
            self._toggle_reading_mode(); return
        super().keyPressEvent(e)

    def closeEvent(self, e):
        for i in range(len(self._tabs) - 1, -1, -1):
            self.tabs.setCurrentIndex(i)
            t = self._tabs[i]
            if t.modified:
                r = QMessageBox.question(self, "Unsaved changes",
                                         f"Save changes to {os.path.basename(t.path or 'Untitled.pdf')}?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if r == QMessageBox.Cancel: e.ignore(); return
                if r == QMessageBox.Save: self._save_tab(t)
            t.doc.close()
        if self._tts_dialog: self._tts_dialog.close()
        e.accept()
