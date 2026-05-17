"""Chudi PDF Pro - main window with multi-doc tabs, side panels, and tools pane."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QIcon, QKeySequence, QPainter,
    QPainterPath, QPen, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSizePolicy, QSpinBox, QStackedWidget, QStatusBar,
    QTabWidget, QToolBar, QVBoxLayout, QWidget, QSplitter
)

from . import APP_NAME, __version__, icons
from .pdf_engine import PdfDocument
from .pdf_viewer import PdfGraphicsView, Tool
from .nav_rail import NavRail
from .side_panel import SidePanel
from .tools_panel import ToolsPane
from .home_screen import HomeScreen, add_recent
from .tools.dialogs import (
    MergeDialog, SplitDialog, EncryptDialog, CompressDialog, OcrDialog,
    WatermarkDialog, PageNumbersDialog, RedactTextDialog, SignatureDialog,
    ExportDialog, SearchPanel,
)


# ---------------- per-document tab payload ----------------
@dataclass
class DocTab:
    view: PdfGraphicsView
    doc: PdfDocument
    path: Optional[str]
    modified: bool = False


# ---------------- main window ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1500, 950)
        self.setWindowIcon(icons.app_logo(32))
        self._tabs: list[DocTab] = []
        self._signature_pix: Optional[QPixmap] = None
        self._search_matches: list = []
        self._search_idx = -1

        self._build_actions()
        self._build_central()
        self._build_top_bar()
        self._build_toolbar()
        self._build_property_strip()
        self._build_statusbar()
        self._build_menus()

        self.setAcceptDrops(True)
        self._update_enabled()
        self._show_home()

    # ---------------- central layout ----------------
    def _build_central(self):
        # Stacked: 0 = home, 1 = editor (rail | sidepanel | tabs | tools)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Home screen
        self.home = HomeScreen()
        self.home.open_file.connect(self.open_file)
        self.home.open_path.connect(self.load_pdf)
        self.home.new_blank.connect(self._new_blank)
        self.home.merge_pdfs.connect(self._do_merge)
        self.home.images_to_pdf.connect(self._do_images_to_pdf)
        self.stack.addWidget(self.home)  # 0

        # Editor area
        editor = QWidget()
        eh = QHBoxLayout(editor); eh.setContentsMargins(0, 0, 0, 0); eh.setSpacing(0)

        self.rail = NavRail()
        self.rail.selected.connect(self._on_rail_selected)
        eh.addWidget(self.rail)

        # splitter so user can resize the left panel and tools pane
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)

        self.side = SidePanel()
        self.side.page_clicked.connect(self._side_goto_page)
        self.side.pages_reordered.connect(self._mark_modified)
        self.side.delete_pages_requested.connect(self._delete_pages)
        self.side.rotate_pages_requested.connect(self._rotate_pages)
        self.side.duplicate_page_requested.connect(self._duplicate_page)
        self.side.extract_pages_requested.connect(self._extract_pages_list)
        self.side.insert_blank_requested.connect(self._insert_blank_after)

        # center: search bar + tab widget
        center = QWidget()
        cv = QVBoxLayout(center); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(0)
        self.search = SearchPanel(); self.search.hide()
        self.search.search_changed.connect(self._on_search_text)
        self.search.next_match.connect(lambda: self._goto_match(+1))
        self.search.prev_match.connect(lambda: self._goto_match(-1))
        self.search.close_requested.connect(self._close_search)
        cv.addWidget(self.search)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
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
        self.splitter.setSizes([240, 900, 260])

        eh.addWidget(self.splitter, 1)
        self.stack.addWidget(editor)  # 1

    # ---------------- top bar (brand + tab indicator) ----------------
    def _build_top_bar(self):
        bar = QFrame(); bar.setObjectName("TopBar"); bar.setFixedHeight(38)
        h = QHBoxLayout(bar); h.setContentsMargins(10, 4, 10, 4); h.setSpacing(8)

        logo = QLabel(); logo.setPixmap(icons.app_logo(22).pixmap(22, 22))
        h.addWidget(logo)
        brand1 = QLabel("Chudi"); brand1.setObjectName("Brand")
        brand2 = QLabel("PDF Pro"); brand2.setObjectName("BrandAccent"); brand2.setStyleSheet("color:#e63946; font-weight:700; font-size:14px;")
        h.addWidget(brand1); h.addWidget(brand2)

        h.addStretch(1)

        # top search (jumps to find-in-doc)
        self.top_search = QLineEdit()
        self.top_search.setObjectName("TopSearch")
        self.top_search.setPlaceholderText("Search in document   (Ctrl+F)")
        self.top_search.returnPressed.connect(self._top_search_submit)
        h.addWidget(self.top_search)

        b_home = QPushButton("Home"); b_home.setObjectName("flat")
        b_home.clicked.connect(self._show_home)
        h.addWidget(b_home)

        # set as a menubar widget so it docks above QToolBar
        self.setMenuWidget(bar)

    # ---------------- actions ----------------
    def _build_actions(self):
        A = QAction
        self.act_open = A(icons.folder_icon(), "&Open...", self); self.act_open.setShortcut(QKeySequence.Open)
        self.act_save = A(icons.save_icon(), "&Save", self); self.act_save.setShortcut(QKeySequence.Save)
        self.act_save_as = A(icons.save_icon(), "Save &as...", self); self.act_save_as.setShortcut(QKeySequence.SaveAs)
        self.act_close = A("&Close tab", self); self.act_close.setShortcut("Ctrl+W")
        self.act_quit = A("E&xit", self); self.act_quit.setShortcut("Ctrl+Q")
        self.act_print = A(icons.print_icon(), "&Print...", self); self.act_print.setShortcut(QKeySequence.Print)

        self.act_undo = A(icons.undo_icon(), "&Undo", self); self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo = A(icons.redo_icon(), "&Redo", self); self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_find = A(icons.search_icon(), "&Find", self); self.act_find.setShortcut(QKeySequence.Find)

        self.act_zoom_in = A(icons.zoom_in_icon(), "Zoom in", self); self.act_zoom_in.setShortcut("Ctrl+=")
        self.act_zoom_out = A(icons.zoom_out_icon(), "Zoom out", self); self.act_zoom_out.setShortcut("Ctrl+-")
        self.act_fit_width = A("Fit width", self); self.act_fit_width.setShortcut("Ctrl+1")
        self.act_fit_page = A("Fit page", self); self.act_fit_page.setShortcut("Ctrl+0")
        self.act_actual = A("Actual size", self); self.act_actual.setShortcut("Ctrl+2")
        self.act_prev_page = A("Previous page", self); self.act_prev_page.setShortcut("PgUp")
        self.act_next_page = A("Next page", self); self.act_next_page.setShortcut("PgDown")

        # tool group
        self.tool_group = QActionGroup(self)
        def tool_act(icon_fn, name, tool: Tool, shortcut=None):
            a = A(icon_fn(), name, self); a.setCheckable(True)
            a.triggered.connect(lambda: self._set_tool(tool))
            self.tool_group.addAction(a)
            if shortcut: a.setShortcut(shortcut)
            return a
        self.act_t_select = tool_act(icons.select_icon, "Select", Tool.SELECT, "V")
        self.act_t_select.setChecked(True)
        self.act_t_hand = tool_act(icons.hand_icon, "Hand", Tool.HAND, "H")
        self.act_t_text = tool_act(icons.text_icon, "Add text", Tool.TEXT, "Shift+T")
        self.act_t_note = tool_act(icons.note_icon, "Note", Tool.NOTE)
        self.act_t_highlight = tool_act(icons.highlight_icon, "Highlight", Tool.HIGHLIGHT, "Shift+H")
        self.act_t_underline = tool_act(icons.underline_icon, "Underline", Tool.UNDERLINE)
        self.act_t_strike = tool_act(icons.strike_icon, "Strikeout", Tool.STRIKEOUT)
        self.act_t_draw = tool_act(icons.draw_icon, "Draw", Tool.DRAW, "Shift+D")
        self.act_t_rect = tool_act(icons.rect_icon, "Rectangle", Tool.RECT)
        self.act_t_image = tool_act(icons.image_icon, "Insert image", Tool.IMAGE)
        self.act_t_sign = tool_act(icons.sign_icon, "Sign", Tool.SIGNATURE)
        self.act_t_redact = tool_act(icons.redact_icon, "Redact", Tool.REDACT)

        # rotations
        self.act_rot_l = A(icons.rotate_left_icon(), "Rotate left", self)
        self.act_rot_r = A(icons.rotate_right_icon(), "Rotate right", self)

        # doc ops
        self.act_merge = A(icons.merge_icon(), "Merge files", self)
        self.act_split = A(icons.split_icon(), "Split file", self)
        self.act_compress = A(icons.compress_icon(), "Compress", self)
        self.act_encrypt = A(icons.lock_icon(), "Password protect", self)
        self.act_decrypt = A("Remove password", self)
        self.act_ocr = A(icons.ocr_icon(), "Make searchable (OCR)", self)
        self.act_watermark = A(icons.watermark_icon(), "Watermark", self)
        self.act_page_numbers = A("Page numbers", self)
        self.act_redact_text = A("Redact by text", self)
        self.act_export = A(icons.export_icon(), "Export", self)
        self.act_images_to_pdf = A(icons.image_icon(), "Images to PDF", self)
        self.act_metadata = A("Metadata", self)
        self.act_about = A("About", self)

        # wire
        self.act_open.triggered.connect(self.open_file)
        self.act_save.triggered.connect(self.save)
        self.act_save_as.triggered.connect(self.save_as)
        self.act_close.triggered.connect(self._close_current_tab)
        self.act_quit.triggered.connect(self.close)
        self.act_print.triggered.connect(self.print_pdf)
        self.act_undo.triggered.connect(self.undo)
        self.act_redo.triggered.connect(self.redo)
        self.act_find.triggered.connect(self._toggle_search)
        self.act_zoom_in.triggered.connect(lambda: self._on_view(lambda v: v.zoom_in()))
        self.act_zoom_out.triggered.connect(lambda: self._on_view(lambda v: v.zoom_out()))
        self.act_fit_width.triggered.connect(lambda: self._on_view(lambda v: v.fit_width()))
        self.act_fit_page.triggered.connect(lambda: self._on_view(lambda v: v.fit_page()))
        self.act_actual.triggered.connect(lambda: self._on_view(lambda v: v.set_zoom(1.0)))
        self.act_prev_page.triggered.connect(lambda: self._on_view(lambda v: v.goto_page(v.current_page_index() - 1)))
        self.act_next_page.triggered.connect(lambda: self._on_view(lambda v: v.goto_page(v.current_page_index() + 1)))
        self.act_rot_l.triggered.connect(lambda: self._rotate_current(-90))
        self.act_rot_r.triggered.connect(lambda: self._rotate_current(90))
        self.act_merge.triggered.connect(self._do_merge)
        self.act_split.triggered.connect(self._do_split)
        self.act_compress.triggered.connect(self._do_compress)
        self.act_encrypt.triggered.connect(self._do_encrypt)
        self.act_decrypt.triggered.connect(self._do_decrypt)
        self.act_ocr.triggered.connect(self._do_ocr)
        self.act_watermark.triggered.connect(self._do_watermark)
        self.act_page_numbers.triggered.connect(self._do_page_numbers)
        self.act_redact_text.triggered.connect(self._do_redact_text)
        self.act_export.triggered.connect(self._do_export)
        self.act_images_to_pdf.triggered.connect(self._do_images_to_pdf)
        self.act_metadata.triggered.connect(self._edit_metadata)
        self.act_t_sign.triggered.connect(self._maybe_pick_signature)
        self.act_t_image.triggered.connect(self._maybe_pick_image)
        self.act_about.triggered.connect(self._about)

    # ---------------- toolbar ----------------
    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setIconSize(QSize(22, 22))
        tb.setMovable(False); tb.setFloatable(False)
        self.addToolBar(tb)
        tb.addActions([self.act_open, self.act_save, self.act_print])
        tb.addSeparator()
        tb.addActions([self.act_undo, self.act_redo])
        tb.addSeparator()

        # page nav: prev | page indicator | next
        tb.addAction(self.act_prev_page)
        self.page_indicator = QLineEdit("1"); self.page_indicator.setFixedWidth(46)
        self.page_indicator.setAlignment(Qt.AlignCenter)
        self.page_indicator.returnPressed.connect(self._goto_page_from_indicator)
        tb.addWidget(self.page_indicator)
        self.of_label = QLabel(" / 0"); tb.addWidget(self.of_label)
        tb.addAction(self.act_next_page)
        tb.addSeparator()

        # zoom
        tb.addActions([self.act_zoom_out, self.act_zoom_in])
        self.zoom_combo = QComboBox(); self.zoom_combo.setEditable(True); self.zoom_combo.setMinimumWidth(110)
        for z in ("50%", "75%", "100%", "125%", "150%", "200%", "300%", "Fit width", "Fit page"):
            self.zoom_combo.addItem(z)
        self.zoom_combo.setCurrentText("125%")
        self.zoom_combo.activated.connect(self._on_zoom_combo)
        tb.addWidget(self.zoom_combo)
        tb.addSeparator()

        # rotations
        tb.addActions([self.act_rot_l, self.act_rot_r])
        tb.addSeparator()

        # find
        tb.addAction(self.act_find)

        # spacer
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

    def _build_property_strip(self):
        """Contextual tool selector strip below the main toolbar."""
        strip = QFrame(); strip.setObjectName("PropertyStrip")
        h = QHBoxLayout(strip); h.setContentsMargins(8, 4, 8, 4); h.setSpacing(2)

        for a in (self.act_t_select, self.act_t_hand):
            b = self._make_tool_button(a); h.addWidget(b)
        h.addWidget(self._sep())
        for a in (self.act_t_text, self.act_t_note,
                  self.act_t_highlight, self.act_t_underline, self.act_t_strike):
            h.addWidget(self._make_tool_button(a))
        h.addWidget(self._sep())
        for a in (self.act_t_draw, self.act_t_rect):
            h.addWidget(self._make_tool_button(a))
        h.addWidget(self._sep())
        for a in (self.act_t_image, self.act_t_sign, self.act_t_redact):
            h.addWidget(self._make_tool_button(a))
        h.addWidget(self._sep())

        h.addWidget(QLabel(" Color:"))
        self.color_btn = QPushButton(""); self.color_btn.setFixedSize(28, 22); self.color_btn.setObjectName("flat")
        self.color_btn.clicked.connect(self._pick_color)
        h.addWidget(self.color_btn)

        h.addWidget(QLabel(" Text size:"))
        self.text_size_spin = QSpinBox(); self.text_size_spin.setRange(6, 96); self.text_size_spin.setValue(12)
        self.text_size_spin.setFixedWidth(60)
        self.text_size_spin.valueChanged.connect(self._on_text_size_changed)
        h.addWidget(self.text_size_spin)

        h.addWidget(QLabel(" Stroke:"))
        self.stroke_spin = QSpinBox(); self.stroke_spin.setRange(1, 20); self.stroke_spin.setValue(2)
        self.stroke_spin.setFixedWidth(56)
        self.stroke_spin.valueChanged.connect(self._on_stroke_changed)
        h.addWidget(self.stroke_spin)

        h.addStretch(1)
        self.addToolBarBreak()
        from PySide6.QtWidgets import QToolBar
        wrapper = QToolBar(); wrapper.setObjectName("PropertyStripWrap")
        wrapper.setMovable(False); wrapper.addWidget(strip); wrapper.setContentsMargins(0,0,0,0)
        wrapper.setStyleSheet("QToolBar{background:#2b2b2b; border:none; padding:0;}")
        self.addToolBar(wrapper)

        self._draw_color = QColor("#000000")
        self._refresh_color_btn()

    def _make_tool_button(self, action: QAction):
        from PySide6.QtWidgets import QToolButton
        b = QToolButton(); b.setDefaultAction(action)
        b.setIconSize(QSize(20, 20))
        b.setToolButtonStyle(Qt.ToolButtonIconOnly)
        return b

    def _sep(self):
        s = QFrame(); s.setFrameShape(QFrame.VLine); s.setStyleSheet("color:#404040;"); s.setFixedHeight(20)
        return s

    def _build_statusbar(self):
        sb = QStatusBar(); self.setStatusBar(sb)
        self.modified_label = QLabel(""); sb.addWidget(self.modified_label)
        self.page_label = QLabel("—"); sb.addPermanentWidget(self.page_label)
        self.zoom_label = QLabel("—"); sb.addPermanentWidget(self.zoom_label)
        self.tool_label = QLabel("Select"); sb.addPermanentWidget(self.tool_label)

    def _build_menus(self):
        # we already set top bar via setMenuWidget; menus appear via QMenuBar()
        # but we need to keep menu functionality. Build a normal menubar that
        # the top bar already replaced - so use a popup hamburger instead.
        # For accessibility, hook File menu actions to keyboard shortcuts only
        # (already done via QAction shortcuts). Add a hamburger action.
        pass

    # ---------------- doc tab management ----------------
    def _current_tab(self) -> Optional[DocTab]:
        i = self.tabs.currentIndex()
        if i < 0 or i >= len(self._tabs):
            return None
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
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF (*.pdf)")
        if path:
            self.load_pdf(path)

    def load_pdf(self, path: str):
        # already open? switch to it
        for i, t in enumerate(self._tabs):
            if t.path and os.path.abspath(t.path) == os.path.abspath(path):
                self.tabs.setCurrentIndex(i)
                self._show_editor()
                return
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

        view = PdfGraphicsView()
        tab = DocTab(view=view, doc=doc, path=path, modified=False)
        view.set_document(doc)
        view.page_changed.connect(lambda n, t=tab: self._on_view_page_changed(t, n))
        view.zoom_changed.connect(lambda z, t=tab: self._on_view_zoom_changed(t, z))
        view.document_modified.connect(lambda t=tab: self._on_view_modified(t))

        self._tabs.append(tab)
        idx = self.tabs.addTab(view, os.path.basename(path))
        self.tabs.setTabToolTip(idx, path)
        self.tabs.setCurrentIndex(idx)
        add_recent(path)
        self._show_editor()
        self.statusBar().showMessage(f"Opened {path}", 3000)

    def _new_blank(self):
        doc = PdfDocument()
        doc.insert_blank_page(0)
        view = PdfGraphicsView()
        tab = DocTab(view=view, doc=doc, path=None, modified=True)
        view.set_document(doc)
        view.page_changed.connect(lambda n, t=tab: self._on_view_page_changed(t, n))
        view.zoom_changed.connect(lambda z, t=tab: self._on_view_zoom_changed(t, z))
        view.document_modified.connect(lambda t=tab: self._on_view_modified(t))
        self._tabs.append(tab)
        idx = self.tabs.addTab(view, "Untitled.pdf")
        self.tabs.setCurrentIndex(idx)
        self._show_editor()

    def _close_current_tab(self):
        i = self.tabs.currentIndex()
        if i >= 0:
            self._close_tab(i)

    def _close_tab(self, index: int):
        if index < 0 or index >= len(self._tabs):
            return
        t = self._tabs[index]
        if t.modified:
            r = QMessageBox.question(self, "Unsaved changes",
                                     f"Save changes to {os.path.basename(t.path or 'Untitled.pdf')}?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel: return
            if r == QMessageBox.Save:
                self._save_tab(t)
                if t.modified: return  # save was cancelled
        t.doc.close()
        self.tabs.removeTab(index)
        del self._tabs[index]
        if not self._tabs:
            self._show_home()

    def _on_tab_changed(self, idx: int):
        t = self._current_tab()
        if not t:
            return
        self.side.load_document(t.doc)
        rail_key = "pages"
        for k, btn in self.rail.buttons.items():
            if btn.isChecked():
                rail_key = k
                break
        self.side.show_panel(rail_key)
        self._update_enabled()
        self.setWindowTitle(f"{APP_NAME} — {os.path.basename(t.path or 'Untitled.pdf')}")
        self.of_label.setText(f" / {t.doc.page_count}")
        self.page_indicator.setText(str(t.view.current_page_index() + 1))
        self._on_view_zoom_changed(t, t.view.zoom)

    def save(self):
        t = self._current_tab()
        if t: self._save_tab(t)

    def _save_tab(self, t: DocTab):
        if not t.path:
            return self._save_as_tab(t)
        try:
            t.doc.save()
            t.modified = False
            self.modified_label.setText("")
            i = self._tabs.index(t)
            self.tabs.setTabText(i, os.path.basename(t.path))
            self.statusBar().showMessage("Saved", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def save_as(self):
        t = self._current_tab()
        if t: self._save_as_tab(t)

    def _save_as_tab(self, t: DocTab):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF as",
                                              t.path or "untitled.pdf", "PDF (*.pdf)")
        if not path: return
        try:
            t.doc.save_copy(path)
            t.path = path
            t.doc.path = path
            t.modified = False
            self.modified_label.setText("")
            i = self._tabs.index(t)
            self.tabs.setTabText(i, os.path.basename(path))
            self.tabs.setTabToolTip(i, path)
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
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.Accepted: return
        painter = QPainter(printer)
        try:
            for i in range(t.doc.page_count):
                if i > 0: printer.newPage()
                pix = QPixmap()
                pix.loadFromData(t.doc.render(i, zoom=3))
                if pix.isNull(): continue
                rect = painter.viewport()
                scaled = pix.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap((rect.width()-scaled.width())//2,
                                   (rect.height()-scaled.height())//2, scaled)
        finally:
            painter.end()

    # ---------------- view signals ----------------
    def _on_view_page_changed(self, tab: DocTab, n: int):
        if tab is not self._current_tab(): return
        self.page_label.setText(f"Page {n} of {tab.doc.page_count}")
        self.of_label.setText(f" / {tab.doc.page_count}")
        self.page_indicator.blockSignals(True)
        self.page_indicator.setText(str(n))
        self.page_indicator.blockSignals(False)

    def _on_view_zoom_changed(self, tab: DocTab, z: float):
        if tab is not self._current_tab(): return
        self.zoom_label.setText(f"{int(z*100)}%")
        self.zoom_combo.blockSignals(True)
        self.zoom_combo.setCurrentText(f"{int(z*100)}%")
        self.zoom_combo.blockSignals(False)

    def _on_view_modified(self, tab: DocTab):
        tab.modified = True
        i = self._tabs.index(tab)
        name = os.path.basename(tab.path or "Untitled.pdf")
        self.tabs.setTabText(i, name + " •")
        if tab is self._current_tab():
            self.modified_label.setText("●  unsaved changes")

    def _mark_modified(self):
        t = self._current_tab()
        if t: self._on_view_modified(t)

    # ---------------- search ----------------
    def _toggle_search(self):
        if self.search.isVisible():
            self._close_search()
        else:
            self.search.show()
            self.search.input.setFocus()
            self.search.input.selectAll()

    def _close_search(self):
        self.search.hide()
        self._search_matches = []

    def _top_search_submit(self):
        text = self.top_search.text()
        if not text: return
        self.search.input.setText(text)
        self._on_search_text(text)
        self.search.show()
        self._goto_match(+1)

    def _on_search_text(self, txt: str):
        t = self._current_tab()
        if not t or not txt:
            self._search_matches = []; self._search_idx = -1
            self.search.status.setText("")
            return
        self._search_matches = t.doc.search(txt)
        self._search_idx = -1
        self.search.status.setText(f"{len(self._search_matches)} match(es)")

    def _goto_match(self, delta: int):
        if not self._search_matches: return
        self._search_idx = (self._search_idx + delta) % len(self._search_matches)
        page_idx, _ = self._search_matches[self._search_idx]
        t = self._current_tab()
        if t: t.view.goto_page(page_idx)
        self.search.status.setText(f"{self._search_idx+1} / {len(self._search_matches)}")

    # ---------------- nav rail ----------------
    def _on_rail_selected(self, key: str):
        if not key:
            self.side.setVisible(False)
            return
        self.side.setVisible(True)
        self.side.show_panel(key)

    def _side_goto_page(self, page_index: int):
        t = self._current_tab()
        if t: t.view.goto_page(page_index)

    # ---------------- undo / redo ----------------
    def undo(self):
        t = self._current_tab()
        if t and t.doc.can_undo():
            t.doc.undo()
            t.view.reload_all()
            self.side.refresh()
            self._mark_modified()

    def redo(self):
        t = self._current_tab()
        if t and t.doc.can_redo():
            t.doc.redo()
            t.view.reload_all()
            self.side.refresh()
            self._mark_modified()

    # ---------------- zoom ----------------
    def _on_zoom_combo(self):
        v = self.zoom_combo.currentText().strip()
        t = self._current_tab()
        if not t: return
        if v == "Fit width": t.view.fit_width(); return
        if v == "Fit page": t.view.fit_page(); return
        try:
            t.view.set_zoom(int(v.replace("%", "").strip()) / 100)
        except ValueError:
            pass

    def _goto_page_from_indicator(self):
        t = self._current_tab()
        if not t: return
        try:
            i = int(self.page_indicator.text()) - 1
            t.view.goto_page(max(0, min(t.doc.page_count - 1, i)))
        except ValueError:
            pass

    # ---------------- tools ----------------
    def _set_tool(self, tool: Tool):
        t = self._current_tab()
        if t:
            t.view.set_tool(tool)
        self.tool_label.setText(tool.value.capitalize())

    def _on_text_size_changed(self, v: int):
        for t in self._tabs:
            t.view.text_size = v

    def _on_stroke_changed(self, v: int):
        for t in self._tabs:
            t.view.draw_width = float(v)

    def _pick_color(self):
        c = QColorDialog.getColor(self._draw_color, self, "Pick color")
        if c.isValid():
            self._draw_color = c
            for t in self._tabs:
                t.view.draw_color = c
            self._refresh_color_btn()

    def _refresh_color_btn(self):
        c = self._draw_color
        self.color_btn.setStyleSheet(f"background:{c.name()}; border:1px solid #555; border-radius:3px;")

    def _maybe_pick_signature(self):
        if not self._current_tab():
            QMessageBox.information(self, "Sign", "Open a PDF first")
            self.act_t_select.setChecked(True); return
        if self._signature_pix is None:
            d = SignatureDialog(self)
            if d.exec() != SignatureDialog.Accepted or d.result_pixmap is None:
                self.act_t_select.setChecked(True); return
            self._signature_pix = d.result_pixmap
        self._current_tab().view.set_signature(self._signature_pix)
        self.statusBar().showMessage("Drag a rectangle to place your signature", 4000)

    def _maybe_pick_image(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Image", "Open a PDF first")
            self.act_t_select.setChecked(True); return
        path, _ = QFileDialog.getOpenFileName(self, "Image to insert", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            self.act_t_select.setChecked(True); return
        t.view.set_image_to_place(path)
        self.statusBar().showMessage("Drag a rectangle to place the image", 4000)

    # ---------------- tools panel actions ----------------
    def _on_tool_action(self, key: str):
        mapping = {
            "add_text":     lambda: self._fire_tool(self.act_t_text, Tool.TEXT),
            "highlight":    lambda: self._fire_tool(self.act_t_highlight, Tool.HIGHLIGHT),
            "underline":    lambda: self._fire_tool(self.act_t_underline, Tool.UNDERLINE),
            "strikeout":    lambda: self._fire_tool(self.act_t_strike, Tool.STRIKEOUT),
            "note":         lambda: self._fire_tool(self.act_t_note, Tool.NOTE),
            "draw":         lambda: self._fire_tool(self.act_t_draw, Tool.DRAW),
            "rect":         lambda: self._fire_tool(self.act_t_rect, Tool.RECT),
            "insert_image": self._maybe_pick_image,
            "signature":    self._maybe_pick_signature,
            "rotate_left":  lambda: self._rotate_current(-90),
            "rotate_right": lambda: self._rotate_current(90),
            "insert_blank": self._insert_blank,
            "duplicate_pg": self._duplicate_current,
            "delete_page":  self._delete_current,
            "extract_pg":   self._extract_pages_prompt,
            "reorder":      self._apply_thumb_order,
            "merge":        self._do_merge,
            "split":        self._do_split,
            "export":       self._do_export,
            "images_pdf":   self._do_images_to_pdf,
            "metadata":     self._edit_metadata,
            "compress":     self._do_compress,
            "watermark":    self._do_watermark,
            "page_numbers": self._do_page_numbers,
            "encrypt":      self._do_encrypt,
            "decrypt":      self._do_decrypt,
            "redact_text":  self._do_redact_text,
            "redact_draw":  lambda: self._fire_tool(self.act_t_redact, Tool.REDACT),
            "ocr":          self._do_ocr,
        }
        fn = mapping.get(key)
        if fn:
            fn()

    def _fire_tool(self, action: QAction, tool: Tool):
        action.setChecked(True)
        self._set_tool(tool)

    # ---------------- page ops ----------------
    def _rotate_current(self, deg: int):
        t = self._current_tab()
        if not t: return
        i = t.view.current_page_index()
        t.doc.rotate_page(i, deg)
        t.view.reload_all()
        self.side.thumbs.refresh(i)
        self._mark_modified()

    def _rotate_pages(self, indices: list, deg: int):
        t = self._current_tab()
        if not t: return
        for i in indices:
            t.doc.rotate_page(i, deg)
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
        if QMessageBox.question(self, "Delete", f"Delete {len(indices)} page(s)?") != QMessageBox.Yes:
            return
        t.doc.delete_pages(indices)
        t.view.set_document(t.doc)
        self.side.load_document(t.doc)
        self._mark_modified()

    def _duplicate_current(self):
        t = self._current_tab()
        if not t: return
        self._duplicate_page(t.view.current_page_index())

    def _duplicate_page(self, index: int):
        t = self._current_tab()
        if not t: return
        t.doc.duplicate_page(index)
        t.view.set_document(t.doc)
        self.side.load_document(t.doc)
        self._mark_modified()

    def _insert_blank(self):
        t = self._current_tab()
        if not t:
            self._new_blank(); return
        i = t.view.current_page_index()
        t.doc.insert_blank_page(i + 1)
        t.view.set_document(t.doc)
        self.side.load_document(t.doc)
        self._mark_modified()

    def _insert_blank_after(self, index: int):
        t = self._current_tab()
        if not t: return
        t.doc.insert_blank_page(index + 1)
        t.view.set_document(t.doc)
        self.side.load_document(t.doc)
        self._mark_modified()

    def _extract_pages_prompt(self):
        t = self._current_tab()
        if not t: return
        txt, ok = QInputDialog.getText(self, "Extract pages",
                                       "Page range (e.g. 1-3, 5):")
        if not ok or not txt.strip(): return
        try:
            indices = self._parse_page_list(txt, t.doc.page_count)
        except Exception as e:
            QMessageBox.warning(self, "Extract", f"Bad range: {e}"); return
        self._extract_pages_list(indices)

    def _extract_pages_list(self, indices: list):
        t = self._current_tab()
        if not t: return
        out, _ = QFileDialog.getSaveFileName(self, "Save extracted pages",
                                             "extracted.pdf", "PDF (*.pdf)")
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
        t.doc.snapshot()
        t.doc.doc = new
        old.close()
        t.view.set_document(t.doc)
        self.side.load_document(t.doc)
        self._mark_modified()

    # ---------------- document ops ----------------
    def _need_doc(self) -> bool:
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

    def _do_page_numbers(self):
        if not self._need_doc(): return
        d = PageNumbersDialog(self)
        if d.exec() != PageNumbersDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_page_numbers(start=s["start"], fontsize=s["fontsize"], position=s["position"])
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _do_redact_text(self):
        if not self._need_doc(): return
        d = RedactTextDialog(self)
        if d.exec() != RedactTextDialog.Accepted: return
        terms = d.terms()
        if not terms: return
        t = self._current_tab()
        for term in terms:
            t.doc.redact_text(term)
        t.view.reload_all(); self.side.thumbs.refresh(); self._mark_modified()

    def _do_export(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        ExportDialog(t.path, self).exec()

    def _do_images_to_pdf(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select images", "",
                                                "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not files: return
        out, _ = QFileDialog.getSaveFileName(self, "Save PDF", "images.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            from .pdf_engine import images_to_pdf
            images_to_pdf(files, out)
            if QMessageBox.question(self, "Done", f"Saved to {out}\n\nOpen it now?") == QMessageBox.Yes:
                self.load_pdf(out)
        except Exception as e:
            QMessageBox.critical(self, "Convert failed", str(e))

    def _edit_metadata(self):
        if not self._need_doc(): return
        t = self._current_tab()
        m = t.doc.metadata()
        dlg = QDialog(self); dlg.setWindowTitle("Document Properties")
        f = QFormLayout(dlg)
        fields = {}
        for key in ("title", "author", "subject", "keywords"):
            le = QLineEdit(str(m.get(key, "") or ""))
            f.addRow(key.capitalize() + ":", le); fields[key] = le
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.Accepted:
            m.update({k: v.text() for k, v in fields.items()})
            t.doc.set_metadata(m); self._mark_modified()

    # ---------------- helpers ----------------
    def _update_enabled(self):
        on = self._current_tab() is not None
        self.tools.set_enabled_all(on)
        for a in (self.act_save, self.act_save_as, self.act_close, self.act_print,
                  self.act_undo, self.act_redo, self.act_find,
                  self.act_zoom_in, self.act_zoom_out, self.act_fit_width,
                  self.act_fit_page, self.act_actual, self.act_prev_page, self.act_next_page,
                  self.act_rot_l, self.act_rot_r,
                  self.act_split, self.act_compress, self.act_encrypt, self.act_ocr,
                  self.act_watermark, self.act_page_numbers, self.act_redact_text,
                  self.act_export, self.act_metadata,
                  self.act_t_text, self.act_t_note, self.act_t_highlight,
                  self.act_t_underline, self.act_t_strike, self.act_t_draw,
                  self.act_t_rect, self.act_t_image, self.act_t_sign, self.act_t_redact):
            a.setEnabled(on)

    def _about(self):
        QMessageBox.information(self, f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {__version__}</p>"
            "<p>Professional PDF editing: view, edit, annotate, sign, merge, split, "
            "compress, password protect, OCR, watermark, redact, and convert.</p>"
            "<p>Built with PySide6, PyMuPDF, and pikepdf.</p>")

    # ---------------- DnD + close ----------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(".pdf")
                                          for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(".pdf"):
                self.load_pdf(p)

    def closeEvent(self, e):
        for i in range(len(self._tabs) - 1, -1, -1):
            self.tabs.setCurrentIndex(i)
            t = self._tabs[i]
            if t.modified:
                r = QMessageBox.question(self, "Unsaved changes",
                                         f"Save changes to {os.path.basename(t.path or 'Untitled.pdf')}?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if r == QMessageBox.Cancel:
                    e.ignore(); return
                if r == QMessageBox.Save: self._save_tab(t)
            t.doc.close()
        e.accept()
