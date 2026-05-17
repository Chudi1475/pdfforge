"""PDFForge main window."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPainterPath,
    QPen, QPixmap, QFont, QFontDatabase, QImage
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDockWidget, QFileDialog, QInputDialog,
    QLabel, QMainWindow, QMessageBox, QSpinBox, QStatusBar, QToolBar, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton, QSizePolicy
)

from . import __version__
from .pdf_engine import PdfDocument
from .pdf_viewer import PdfGraphicsView, Tool
from .thumbnails import ThumbnailList
from .tools.dialogs import (
    MergeDialog, SplitDialog, EncryptDialog, CompressDialog, OcrDialog,
    WatermarkDialog, PageNumbersDialog, RedactTextDialog, SignatureDialog,
    ExportDialog, SearchPanel,
)


def make_icon(symbol: str, color: str = "#d4d4d4", bg: str = "transparent",
              size: int = 24) -> QIcon:
    """Render a unicode glyph into a QIcon — no external assets required."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    if bg != "transparent":
        p.setBrush(QColor(bg))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, size, size, 4, 4)
    f = QFont("Segoe UI Symbol", int(size * 0.6))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(pix.rect(), Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDFForge")
        self.resize(1500, 950)
        self.setWindowIcon(make_icon("◈", "#0a84ff"))
        self.doc: Optional[PdfDocument] = None
        self._modified = False
        self._search_matches: list = []
        self._search_idx = -1
        self._signature_pix: Optional[QPixmap] = None

        self.view = PdfGraphicsView()
        self.setCentralWidget(self._wrap_central())

        self.view.page_changed.connect(self._on_page_changed)
        self.view.zoom_changed.connect(self._on_zoom_changed)
        self.view.document_modified.connect(self._mark_modified)

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_sidebar()
        self._build_statusbar()
        self.setAcceptDrops(True)
        self._update_actions_enabled()

    # ----- layout -----
    def _wrap_central(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        self.search = SearchPanel()
        self.search.hide()
        self.search.search_changed.connect(self._on_search_text)
        self.search.next_match.connect(lambda: self._goto_match(+1))
        self.search.prev_match.connect(lambda: self._goto_match(-1))
        self.search.close_requested.connect(self._close_search)
        v.addWidget(self.search)
        v.addWidget(self.view, 1)
        return w

    # ----- actions -----
    def _build_actions(self):
        A = QAction
        self.act_open = A(make_icon("📂"), "&Open...", self); self.act_open.setShortcut(QKeySequence.Open)
        self.act_save = A(make_icon("💾"), "&Save", self); self.act_save.setShortcut(QKeySequence.Save)
        self.act_save_as = A(make_icon("💾"), "Save &as...", self); self.act_save_as.setShortcut(QKeySequence.SaveAs)
        self.act_close = A("&Close", self); self.act_close.setShortcut(QKeySequence.Close)
        self.act_quit = A("E&xit", self); self.act_quit.setShortcut("Ctrl+Q")
        self.act_print = A(make_icon("🖨"), "&Print...", self); self.act_print.setShortcut(QKeySequence.Print)

        self.act_undo = A(make_icon("↶"), "&Undo", self); self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo = A(make_icon("↷"), "&Redo", self); self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_find = A(make_icon("🔍"), "&Find...", self); self.act_find.setShortcut(QKeySequence.Find)

        self.act_zoom_in = A(make_icon("➕"), "Zoom &in", self); self.act_zoom_in.setShortcut("Ctrl++")
        self.act_zoom_out = A(make_icon("➖"), "Zoom &out", self); self.act_zoom_out.setShortcut("Ctrl+-")
        self.act_fit_width = A("Fit &width", self); self.act_fit_width.setShortcut("Ctrl+1")
        self.act_fit_page = A("Fit &page", self); self.act_fit_page.setShortcut("Ctrl+0")
        self.act_actual = A("&Actual size", self); self.act_actual.setShortcut("Ctrl+2")

        # tools (mutually exclusive)
        self.tool_group = QActionGroup(self)
        def tool_act(symbol, name, tool: Tool, shortcut=None):
            a = A(make_icon(symbol), name, self); a.setCheckable(True)
            a.triggered.connect(lambda: self.view.set_tool(tool))
            self.tool_group.addAction(a)
            if shortcut:
                a.setShortcut(shortcut)
            return a
        self.act_t_select = tool_act("↖", "Select", Tool.SELECT, "V")
        self.act_t_select.setChecked(True)
        self.act_t_hand = tool_act("✋", "Hand (pan)", Tool.HAND, "H")
        self.act_t_text = tool_act("T", "Add text", Tool.TEXT, "Shift+T")
        self.act_t_note = tool_act("🗨", "Sticky note", Tool.NOTE)
        self.act_t_highlight = tool_act("🖍", "Highlight", Tool.HIGHLIGHT, "Shift+H")
        self.act_t_underline = tool_act("U̲", "Underline", Tool.UNDERLINE)
        self.act_t_strike = tool_act("S̶", "Strikeout", Tool.STRIKEOUT)
        self.act_t_draw = tool_act("✎", "Draw", Tool.DRAW, "Shift+D")
        self.act_t_rect = tool_act("▭", "Rectangle", Tool.RECT)
        self.act_t_image = tool_act("🖼", "Insert image", Tool.IMAGE)
        self.act_t_sign = tool_act("✍", "Sign", Tool.SIGNATURE)
        self.act_t_redact = tool_act("█", "Redact (drag)", Tool.REDACT)

        # page ops
        self.act_rot_l = A(make_icon("↶"), "Rotate left", self)
        self.act_rot_r = A(make_icon("↷"), "Rotate right", self)
        self.act_insert_blank = A("Insert blank page", self)
        self.act_delete_page = A("Delete current page", self)
        self.act_extract = A("Extract pages...", self)
        self.act_reorder_apply = A("Apply thumbnail order", self)

        # document ops
        self.act_merge = A(make_icon("⊕"), "Merge PDFs...", self)
        self.act_split = A("Split this PDF...", self)
        self.act_compress = A(make_icon("⇩"), "Compress...", self)
        self.act_encrypt = A(make_icon("🔒"), "Password protect...", self)
        self.act_decrypt = A("Remove password...", self)
        self.act_ocr = A("Make searchable (OCR)...", self)
        self.act_watermark = A(make_icon("✦"), "Add watermark...", self)
        self.act_page_numbers = A("Add page numbers...", self)
        self.act_redact_text = A(make_icon("█"), "Redact by text...", self)
        self.act_export = A("Export...", self)
        self.act_images_to_pdf = A("Build PDF from images...", self)
        self.act_metadata = A("Metadata...", self)

        self.act_about = A("&About", self)

        # wire
        self.act_open.triggered.connect(self.open_file)
        self.act_save.triggered.connect(self.save)
        self.act_save_as.triggered.connect(self.save_as)
        self.act_close.triggered.connect(self.close_doc)
        self.act_quit.triggered.connect(self.close)
        self.act_print.triggered.connect(self.print_pdf)
        self.act_undo.triggered.connect(self.undo)
        self.act_redo.triggered.connect(self.redo)
        self.act_find.triggered.connect(self._toggle_search)
        self.act_zoom_in.triggered.connect(self.view.zoom_in)
        self.act_zoom_out.triggered.connect(self.view.zoom_out)
        self.act_fit_width.triggered.connect(self.view.fit_width)
        self.act_fit_page.triggered.connect(self.view.fit_page)
        self.act_actual.triggered.connect(lambda: self.view.set_zoom(1.0))
        self.act_rot_l.triggered.connect(lambda: self._rotate_current(-90))
        self.act_rot_r.triggered.connect(lambda: self._rotate_current(90))
        self.act_insert_blank.triggered.connect(self._insert_blank)
        self.act_delete_page.triggered.connect(self._delete_current)
        self.act_extract.triggered.connect(self._extract_pages)
        self.act_reorder_apply.triggered.connect(self._apply_thumb_order)
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
        self.act_t_sign.triggered.connect(self._on_sign_tool)
        self.act_t_image.triggered.connect(self._on_image_tool)
        self.act_about.triggered.connect(self._about)

    def _build_menus(self):
        m = self.menuBar()
        f = m.addMenu("&File")
        f.addActions([self.act_open]); f.addSeparator()
        f.addActions([self.act_save, self.act_save_as]); f.addSeparator()
        f.addAction(self.act_images_to_pdf)
        f.addAction(self.act_export)
        f.addSeparator()
        f.addAction(self.act_print); f.addSeparator()
        f.addActions([self.act_close, self.act_quit])

        e = m.addMenu("&Edit")
        e.addActions([self.act_undo, self.act_redo]); e.addSeparator()
        e.addAction(self.act_find); e.addSeparator()
        e.addAction(self.act_metadata)

        v = m.addMenu("&View")
        v.addActions([self.act_zoom_in, self.act_zoom_out]); v.addSeparator()
        v.addActions([self.act_fit_width, self.act_fit_page, self.act_actual])

        t = m.addMenu("&Tools")
        for a in (self.act_t_select, self.act_t_hand, self.act_t_text, self.act_t_note,
                  self.act_t_highlight, self.act_t_underline, self.act_t_strike,
                  self.act_t_draw, self.act_t_rect, self.act_t_image,
                  self.act_t_sign, self.act_t_redact):
            t.addAction(a)

        p = m.addMenu("&Pages")
        p.addActions([self.act_rot_l, self.act_rot_r]); p.addSeparator()
        p.addActions([self.act_insert_blank, self.act_delete_page, self.act_extract])
        p.addSeparator()
        p.addAction(self.act_reorder_apply)

        d = m.addMenu("&Document")
        d.addActions([self.act_merge, self.act_split]); d.addSeparator()
        d.addActions([self.act_compress, self.act_watermark, self.act_page_numbers])
        d.addSeparator()
        d.addActions([self.act_encrypt, self.act_decrypt])
        d.addSeparator()
        d.addActions([self.act_ocr, self.act_redact_text])

        h = m.addMenu("&Help")
        h.addAction(self.act_about)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setIconSize(QSize(22, 22))
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addActions([self.act_open, self.act_save, self.act_print])
        tb.addSeparator()
        tb.addActions([self.act_undo, self.act_redo])
        tb.addSeparator()
        tb.addActions([self.act_zoom_out, self.act_zoom_in])

        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True); self.zoom_combo.setMinimumWidth(90)
        for z in ("50%", "75%", "100%", "125%", "150%", "200%", "Fit width", "Fit page"):
            self.zoom_combo.addItem(z)
        self.zoom_combo.setCurrentText("125%")
        self.zoom_combo.activated.connect(self._on_zoom_combo)
        tb.addWidget(self.zoom_combo)
        tb.addSeparator()
        tb.addActions([self.act_rot_l, self.act_rot_r])
        tb.addSeparator()

        # tools row
        tools_tb = QToolBar("Tools")
        tools_tb.setIconSize(QSize(22, 22))
        tools_tb.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(tools_tb)
        for a in (self.act_t_select, self.act_t_hand):
            tools_tb.addAction(a)
        tools_tb.addSeparator()
        for a in (self.act_t_text, self.act_t_note, self.act_t_highlight,
                  self.act_t_underline, self.act_t_strike):
            tools_tb.addAction(a)
        tools_tb.addSeparator()
        for a in (self.act_t_draw, self.act_t_rect):
            tools_tb.addAction(a)
        tools_tb.addSeparator()
        for a in (self.act_t_image, self.act_t_sign, self.act_t_redact):
            tools_tb.addAction(a)
        tools_tb.addSeparator()

        # color + size
        self.color_btn = QPushButton("Color")
        self.color_btn.setFixedWidth(70)
        self.color_btn.clicked.connect(self._pick_color)
        self._refresh_color_btn()
        tools_tb.addWidget(self.color_btn)
        tools_tb.addWidget(QLabel(" Text size:"))
        self.text_size_spin = QSpinBox(); self.text_size_spin.setRange(6, 96); self.text_size_spin.setValue(12)
        self.text_size_spin.valueChanged.connect(lambda v: setattr(self.view, "text_size", v))
        tools_tb.addWidget(self.text_size_spin)
        tools_tb.addWidget(QLabel(" Stroke:"))
        self.stroke_spin = QSpinBox(); self.stroke_spin.setRange(1, 20); self.stroke_spin.setValue(2)
        self.stroke_spin.valueChanged.connect(lambda v: setattr(self.view, "draw_width", float(v)))
        tools_tb.addWidget(self.stroke_spin)

        # spacer
        s = QWidget(); s.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tools_tb.addWidget(s)

        # quick ops
        tools_tb.addActions([self.act_merge, self.act_compress, self.act_encrypt, self.act_watermark])
        tools_tb.addAction(self.act_find)

    def _build_sidebar(self):
        dock = QDockWidget("Pages", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.thumbs = ThumbnailList()
        dock.setWidget(self.thumbs)
        dock.setMinimumWidth(220)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.thumbs.page_clicked.connect(self.view.goto_page)
        self.thumbs.delete_requested.connect(self._delete_pages)
        self.thumbs.rotate_requested.connect(self._rotate_pages)
        self.thumbs.duplicate_requested.connect(self._duplicate_page)
        self.thumbs.extract_requested.connect(self._extract_pages_list)
        self.thumbs.insert_blank_requested.connect(self._insert_blank_after)
        self.thumbs.pages_reordered.connect(self._mark_modified)

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.page_label = QLabel("—"); sb.addPermanentWidget(self.page_label)
        self.zoom_label = QLabel("—"); sb.addPermanentWidget(self.zoom_label)
        self.modified_label = QLabel(""); sb.addWidget(self.modified_label)

    # ---------------- file ops ----------------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF (*.pdf)")
        if path:
            self.load_pdf(path)

    def load_pdf(self, path: str):
        try:
            doc = PdfDocument(path)
        except PermissionError:
            pw, ok = QInputDialog.getText(self, "Password required",
                                          "This PDF is encrypted. Enter password:",
                                          echo=2)
            if not ok:
                return
            try:
                doc = PdfDocument(path, password=pw)
            except Exception as e:
                QMessageBox.critical(self, "Open failed", str(e))
                return
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))
            return
        if self.doc:
            self.doc.close()
        self.doc = doc
        self.view.set_document(doc)
        self.thumbs.load(doc)
        self._modified = False
        self.setWindowTitle(f"PDFForge — {os.path.basename(path)}")
        self.statusBar().showMessage(f"Opened {path}", 4000)
        self._update_actions_enabled()

    def save(self):
        if not self.doc: return
        if not self.doc.path:
            return self.save_as()
        try:
            self.doc.save()
            self._modified = False
            self.modified_label.setText("")
            self.statusBar().showMessage("Saved", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def save_as(self):
        if not self.doc: return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF as",
                                              self.doc.path or "untitled.pdf", "PDF (*.pdf)")
        if not path: return
        try:
            self.doc.save_copy(path)
            self._modified = False
            self.modified_label.setText("")
            self.setWindowTitle(f"PDFForge — {os.path.basename(path)}")
            self.statusBar().showMessage(f"Saved to {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def close_doc(self):
        if not self._confirm_discard(): return
        if self.doc:
            self.doc.close()
        self.doc = None
        self.view.set_document(None)
        self.thumbs.load(None)
        self.setWindowTitle("PDFForge")
        self._update_actions_enabled()

    def print_pdf(self):
        if not self.doc: return
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.Accepted:
            return
        painter = QPainter(printer)
        try:
            first = True
            for i in range(self.doc.page_count):
                if not first:
                    printer.newPage()
                first = False
                pix = QPixmap()
                pix.loadFromData(self.doc.render(i, zoom=3))
                if pix.isNull():
                    continue
                rect = painter.viewport()
                scaled = pix.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = (rect.width() - scaled.width()) // 2
                y = (rect.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
        finally:
            painter.end()

    # ---------------- edit ----------------
    def undo(self):
        if self.doc and self.doc.can_undo():
            self.doc.undo()
            self.view.reload_all()
            self.thumbs.refresh()

    def redo(self):
        if self.doc and self.doc.can_redo():
            self.doc.redo()
            self.view.reload_all()
            self.thumbs.refresh()

    # ---------------- view ----------------
    def _on_page_changed(self, n: int):
        if not self.doc: return
        self.page_label.setText(f"Page {n} / {self.doc.page_count}")

    def _on_zoom_changed(self, z: float):
        self.zoom_label.setText(f"{int(z*100)}%")
        self.zoom_combo.blockSignals(True)
        self.zoom_combo.setCurrentText(f"{int(z*100)}%")
        self.zoom_combo.blockSignals(False)

    def _on_zoom_combo(self):
        v = self.zoom_combo.currentText().strip()
        if v == "Fit width":
            self.view.fit_width(); return
        if v == "Fit page":
            self.view.fit_page(); return
        v = v.replace("%", "").strip()
        try:
            self.view.set_zoom(int(v) / 100)
        except ValueError:
            pass

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

    def _on_search_text(self, txt: str):
        if not self.doc or not txt:
            self._search_matches = []; self._search_idx = -1
            self.search.status.setText("")
            return
        self._search_matches = self.doc.search(txt)
        self._search_idx = -1
        self.search.status.setText(f"{len(self._search_matches)} match(es)")

    def _goto_match(self, delta: int):
        if not self._search_matches: return
        self._search_idx = (self._search_idx + delta) % len(self._search_matches)
        page_idx, _quad = self._search_matches[self._search_idx]
        self.view.goto_page(page_idx)
        self.search.status.setText(f"{self._search_idx+1} / {len(self._search_matches)}")

    # ---------------- page ops ----------------
    def _rotate_current(self, deg: int):
        if not self.doc: return
        i = self.view.current_page_index()
        self.doc.rotate_page(i, deg)
        self.view.reload_all()
        self.thumbs.refresh(i)
        self._mark_modified()

    def _rotate_pages(self, indices: list, deg: int):
        if not self.doc: return
        for i in indices:
            self.doc.rotate_page(i, deg)
        self.view.reload_all()
        self.thumbs.refresh()
        self._mark_modified()

    def _delete_current(self):
        if not self.doc: return
        if self.doc.page_count <= 1:
            QMessageBox.warning(self, "Delete", "Cannot delete the only page")
            return
        i = self.view.current_page_index()
        self._delete_pages([i])

    def _delete_pages(self, indices: list):
        if not self.doc or not indices: return
        if len(indices) >= self.doc.page_count:
            QMessageBox.warning(self, "Delete", "Cannot delete all pages")
            return
        if QMessageBox.question(self, "Delete", f"Delete {len(indices)} page(s)?") != QMessageBox.Yes:
            return
        self.doc.delete_pages(indices)
        self.view.set_document(self.doc)
        self.thumbs.load(self.doc)
        self._mark_modified()

    def _duplicate_page(self, index: int):
        if not self.doc: return
        self.doc.duplicate_page(index)
        self.view.set_document(self.doc)
        self.thumbs.load(self.doc)
        self._mark_modified()

    def _insert_blank(self):
        if not self.doc:
            self.doc = PdfDocument()
        i = self.view.current_page_index() if self.doc.page_count else 0
        self.doc.insert_blank_page(i + 1)
        self.view.set_document(self.doc)
        self.thumbs.load(self.doc)
        self._mark_modified()

    def _insert_blank_after(self, index: int):
        if not self.doc: return
        self.doc.insert_blank_page(index + 1)
        self.view.set_document(self.doc)
        self.thumbs.load(self.doc)
        self._mark_modified()

    def _extract_pages(self):
        if not self.doc: return
        txt, ok = QInputDialog.getText(self, "Extract pages",
                                       "Page range (e.g. 1-3, 5):")
        if not ok or not txt.strip(): return
        try:
            indices = self._parse_page_list(txt, self.doc.page_count)
        except Exception as e:
            QMessageBox.warning(self, "Extract", f"Bad range: {e}")
            return
        self._extract_pages_list(indices)

    def _extract_pages_list(self, indices: list):
        if not self.doc: return
        out, _ = QFileDialog.getSaveFileName(self, "Save extracted pages",
                                             "extracted.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            self.doc.extract_pages(indices, out)
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
        if not self.doc: return
        order = self.thumbs.get_page_order()
        if order == list(range(self.doc.page_count)):
            self.statusBar().showMessage("No reorder needed", 2000); return
        import fitz
        new = fitz.open()
        for src_idx in order:
            new.insert_pdf(self.doc.doc, from_page=src_idx, to_page=src_idx)
        old = self.doc.doc
        self.doc.snapshot()
        self.doc.doc = new
        old.close()
        self.view.set_document(self.doc)
        self.thumbs.load(self.doc)
        self._mark_modified()

    # ---------------- document ops ----------------
    def _need_doc(self) -> bool:
        if not self.doc:
            QMessageBox.information(self, "PDFForge", "Open a PDF first")
            return False
        return True

    def _do_merge(self):
        MergeDialog(self).exec()

    def _do_split(self):
        if not self._need_doc(): return
        if not self.doc.path:
            QMessageBox.information(self, "Split", "Save the PDF first"); return
        SplitDialog(self.doc.path, self.doc.page_count, self).exec()

    def _do_compress(self):
        if not self._need_doc(): return
        if not self.doc.path:
            QMessageBox.information(self, "Compress", "Save the PDF first"); return
        CompressDialog(self.doc.path, self).exec()

    def _do_encrypt(self):
        if not self._need_doc(): return
        if not self.doc.path:
            QMessageBox.information(self, "Protect", "Save the PDF first"); return
        EncryptDialog(self.doc.path, self).exec()

    def _do_decrypt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Encrypted PDF", "", "PDF (*.pdf)")
        if not path: return
        pw, ok = QInputDialog.getText(self, "Password", "Password:", echo=2)
        if not ok: return
        out, _ = QFileDialog.getSaveFileName(self, "Save decrypted PDF",
                                             f"{Path(path).stem}_decrypted.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            from .pdf_engine import decrypt_pdf
            decrypt_pdf(path, out, pw)
            QMessageBox.information(self, "Decrypt", f"Saved to {out}")
        except Exception as e:
            QMessageBox.critical(self, "Decrypt failed", str(e))

    def _do_ocr(self):
        if not self._need_doc(): return
        if not self.doc.path:
            QMessageBox.information(self, "OCR", "Save the PDF first"); return
        OcrDialog(self.doc.path, self).exec()

    def _do_watermark(self):
        if not self._need_doc(): return
        d = WatermarkDialog(self)
        if d.exec() != WatermarkDialog.Accepted: return
        s = d.settings()
        self.doc.add_watermark(s["text"], opacity=s["opacity"], fontsize=s["fontsize"],
                               color=s["color"], rotation=s["rotation"])
        self.view.reload_all(); self.thumbs.refresh(); self._mark_modified()

    def _do_page_numbers(self):
        if not self._need_doc(): return
        d = PageNumbersDialog(self)
        if d.exec() != PageNumbersDialog.Accepted: return
        s = d.settings()
        self.doc.add_page_numbers(start=s["start"], fontsize=s["fontsize"], position=s["position"])
        self.view.reload_all(); self.thumbs.refresh(); self._mark_modified()

    def _do_redact_text(self):
        if not self._need_doc(): return
        d = RedactTextDialog(self)
        if d.exec() != RedactTextDialog.Accepted: return
        terms = d.terms()
        if not terms: return
        for t in terms:
            self.doc.redact_text(t)
        self.view.reload_all(); self.thumbs.refresh(); self._mark_modified()

    def _do_export(self):
        if not self._need_doc(): return
        if not self.doc.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        ExportDialog(self.doc.path, self).exec()

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
            QMessageBox.critical(self, "Export failed", str(e))

    def _edit_metadata(self):
        if not self._need_doc(): return
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit
        m = self.doc.metadata()
        dlg = QDialog(self); dlg.setWindowTitle("Metadata")
        f = QFormLayout(dlg)
        fields = {}
        for key in ("title", "author", "subject", "keywords"):
            le = QLineEdit(str(m.get(key, "") or ""))
            f.addRow(key.capitalize() + ":", le)
            fields[key] = le
        from PySide6.QtWidgets import QDialogButtonBox
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.Accepted:
            new = {k: v.text() for k, v in fields.items()}
            # preserve format-required fields
            m.update(new)
            self.doc.set_metadata(m)
            self._mark_modified()

    # ---------------- tool callbacks ----------------
    def _pick_color(self):
        c = QColorDialog.getColor(self.view.draw_color, self, "Pick color")
        if c.isValid():
            self.view.draw_color = c
            self._refresh_color_btn()

    def _refresh_color_btn(self):
        c = self.view.draw_color
        fg = "#000" if (c.red() + c.green() + c.blue()) > 380 else "#fff"
        self.color_btn.setStyleSheet(f"background:{c.name()}; color:{fg};")

    def _on_sign_tool(self):
        if not self.doc:
            QMessageBox.information(self, "Sign", "Open a PDF first")
            self.act_t_select.setChecked(True); self.view.set_tool(Tool.SELECT); return
        if self._signature_pix is None:
            d = SignatureDialog(self)
            if d.exec() != SignatureDialog.Accepted or d.result_pixmap is None:
                self.act_t_select.setChecked(True); self.view.set_tool(Tool.SELECT); return
            self._signature_pix = d.result_pixmap
        self.view.set_signature(self._signature_pix)
        self.statusBar().showMessage("Drag a rectangle where you want the signature", 5000)

    def _on_image_tool(self):
        if not self.doc:
            QMessageBox.information(self, "Image", "Open a PDF first")
            self.act_t_select.setChecked(True); self.view.set_tool(Tool.SELECT); return
        path, _ = QFileDialog.getOpenFileName(self, "Image to insert", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            self.act_t_select.setChecked(True); self.view.set_tool(Tool.SELECT); return
        self.view.set_image_to_place(path)
        self.statusBar().showMessage("Drag a rectangle to place the image", 5000)

    # ---------------- state ----------------
    def _mark_modified(self):
        self._modified = True
        self.modified_label.setText("● modified")

    def _confirm_discard(self) -> bool:
        if not self._modified: return True
        r = QMessageBox.question(self, "Unsaved changes",
                                 "You have unsaved changes. Save before closing?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Cancel: return False
        if r == QMessageBox.Save: self.save()
        return True

    def _update_actions_enabled(self):
        on = self.doc is not None
        for a in (self.act_save, self.act_save_as, self.act_close, self.act_print,
                  self.act_undo, self.act_redo, self.act_find,
                  self.act_zoom_in, self.act_zoom_out, self.act_fit_width,
                  self.act_fit_page, self.act_actual,
                  self.act_rot_l, self.act_rot_r, self.act_insert_blank,
                  self.act_delete_page, self.act_extract, self.act_reorder_apply,
                  self.act_split, self.act_compress, self.act_encrypt, self.act_ocr,
                  self.act_watermark, self.act_page_numbers, self.act_redact_text,
                  self.act_export, self.act_metadata,
                  self.act_t_text, self.act_t_note, self.act_t_highlight,
                  self.act_t_underline, self.act_t_strike, self.act_t_draw,
                  self.act_t_rect, self.act_t_image, self.act_t_sign, self.act_t_redact):
            a.setEnabled(on)

    def _about(self):
        QMessageBox.information(self, "About PDFForge",
            f"<h3>PDFForge {__version__}</h3>"
            "<p>A free, open-source PDF editor.</p>"
            "<p>View, edit, annotate, sign, merge, split, compress,"
            " password protect, OCR, watermark, redact, and convert PDFs.</p>"
            "<p>Built with PySide6, PyMuPDF, and pikepdf.</p>")

    # ---------------- DnD ----------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(".pdf")
                                          for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(".pdf"):
                self.load_pdf(p); return

    def closeEvent(self, e):
        if self._confirm_discard():
            e.accept()
        else:
            e.ignore()
