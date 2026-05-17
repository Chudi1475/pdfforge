"""Chudi PDF Pro - main window."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal, QTimer, QPoint
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QKeySequence, QPainter, QPixmap, QFont,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSpinBox,
    QStackedWidget, QStatusBar, QVBoxLayout, QWidget, QSplitter, QToolBar,
    QStyle, QComboBox, QToolButton, QMenu,
)

from . import APP_NAME, __version__, icons
from .pdf_engine import PdfDocument
from .pdf_viewer import PdfGraphicsView, Tool, ViewMode
from .top_bar import TopBar
from .mode_tabs import ModeTabsBar
from .mode_panels import (make_all_tools_panel, make_edit_panel,
                          make_convert_panel, make_esign_panel)
from .canvas_container import CanvasContainer
from .right_rail import RightRail
from .ai_assistant import AiAssistantPanel
from .side_panel import SidePanel
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
        self.resize(1600, 1000)
        self.setWindowIcon(icons.app_logo(32))

        self._tabs: list[DocTab] = []
        self._mode = "all"
        self._search_matches: list = []
        self._search_idx = -1
        self._search_options = {"case_sensitive": False, "whole_words": False}
        self._signature_pix: Optional[QPixmap] = None
        self._reading_mode_saved = None
        self._tts_dialog: Optional[TtsDialog] = None
        self._side_panel_key: str = ""

        self._build_top_bar()
        self._build_mode_bar()
        self._build_central()
        self._build_statusbar()
        self._install_shortcuts()

        self.setAcceptDrops(True)
        self._update_enabled()
        self._show_home()

    # ============== top bar (doc tabs + chrome) ==============
    def _build_top_bar(self):
        self.top_bar = TopBar()
        self.top_bar.home_clicked.connect(self._show_home)
        self.top_bar.create_clicked.connect(self._new_blank)
        self.top_bar.tab_clicked.connect(self._switch_to_tab)
        self.top_bar.tab_closed.connect(self._close_tab)
        self.top_bar.menu_action.connect(self._on_menu_action)
        self.top_bar.help_clicked.connect(self._about)
        self.top_bar.notifications_clicked.connect(lambda: self.statusBar().showMessage("No new notifications", 3000))
        self.setMenuWidget(self._wrap_chrome())

    def _wrap_chrome(self) -> QWidget:
        # combine top bar + mode bar in a single chrome widget
        chrome = QWidget()
        v = QVBoxLayout(chrome); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        v.addWidget(self.top_bar)
        # placeholder, mode bar added in _build_mode_bar
        self._chrome_container = v
        return chrome

    # ============== mode tabs row ==============
    def _build_mode_bar(self):
        self.mode_bar = ModeTabsBar()
        self.mode_bar.mode_changed.connect(self._switch_mode)
        self.mode_bar.search_submitted.connect(self._top_search_submit)
        self.mode_bar.save_clicked.connect(self.save)
        self.mode_bar.cloud_clicked.connect(self.save_as)
        self.mode_bar.print_clicked.connect(self.print_pdf)
        self.mode_bar.share_clicked.connect(self._share)
        self.mode_bar.ask_ai_clicked.connect(self._toggle_ai_panel)
        self.mode_bar.ai_button_clicked.connect(self._toggle_ai_panel)
        self._chrome_container.addWidget(self.mode_bar)

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

        # left: mode panel area (stack of 4)
        self.mode_panel_stack = QStackedWidget()
        self.mode_panels = {
            "all":     make_all_tools_panel(),
            "edit":    make_edit_panel(),
            "convert": make_convert_panel(),
            "esign":   make_esign_panel(),
        }
        for key, panel in self.mode_panels.items():
            panel.action.connect(self._execute_tool_action)
            panel.close_requested.connect(self._hide_mode_panel)
            self.mode_panel_stack.addWidget(panel)
        self.mode_panel_wrap = QFrame()
        self.mode_panel_wrap.setObjectName("ModePanel")
        self.mode_panel_wrap.setMinimumWidth(280); self.mode_panel_wrap.setMaximumWidth(380)
        mw = QVBoxLayout(self.mode_panel_wrap); mw.setContentsMargins(0, 0, 0, 0); mw.setSpacing(0)
        mw.addWidget(self.mode_panel_stack, 1)
        # subscribe / hint area
        hint = QLabel("Tip: All edits are saved locally. No cloud upload.")
        hint.setStyleSheet("color:#a3a3a3; padding: 12px 18px; font-size: 11px;")
        hint.setWordWrap(True)
        mw.addWidget(hint)
        eh.addWidget(self.mode_panel_wrap)

        # center: canvas container + ai panel below
        center = QWidget()
        cv = QVBoxLayout(center); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(0)
        # find bar (slides in from top)
        self.search = SearchPanel(); self.search.hide()
        self.search.search_changed.connect(self._on_search_text)
        self.search.next_match.connect(lambda: self._goto_match(+1))
        self.search.prev_match.connect(lambda: self._goto_match(-1))
        self.search.case_changed.connect(lambda v: self._set_search_option("case_sensitive", v))
        self.search.whole_words_changed.connect(lambda v: self._set_search_option("whole_words", v))
        self.search.close_requested.connect(self._close_search)
        cv.addWidget(self.search)

        self.canvas = CanvasContainer()
        self.canvas.tool_selected.connect(self._set_tool)
        self.canvas.page_change.connect(self._goto_page_1)
        self.canvas.page_step.connect(self._step_page)
        self.canvas.zoom_in.connect(lambda: self._on_view(lambda v: v.zoom_in()))
        self.canvas.zoom_out.connect(lambda: self._on_view(lambda v: v.zoom_out()))
        self.canvas.fit_page.connect(lambda: self._on_view(lambda v: v.fit_page()))
        self.canvas.overflow_action.connect(self._page_nav_overflow)
        cv.addWidget(self.canvas, 1)

        self.ai_panel = AiAssistantPanel()
        self.ai_panel.hide()
        self.ai_panel.closed.connect(self._toggle_ai_panel)
        self.ai_panel.set_text_provider(
            get_text_fn=self._ai_current_text,
            get_page_fn=lambda: (self._current_tab().view.current_page_index() if self._current_tab() else 0),
            get_total_fn=lambda: (self._current_tab().doc.page_count if self._current_tab() else 0),
        )
        cv.addWidget(self.ai_panel)

        eh.addWidget(center, 1)

        # right: side panel flyout + right rail
        self.right_flyout = SidePanel()
        self.right_flyout.setMinimumWidth(240)
        self.right_flyout.setMaximumWidth(360)
        self.right_flyout.hide()
        self.right_flyout.page_clicked.connect(self._goto_page_0)
        self.right_flyout.delete_pages_requested.connect(self._delete_pages)
        self.right_flyout.rotate_pages_requested.connect(self._rotate_pages)
        self.right_flyout.duplicate_page_requested.connect(self._duplicate_page)
        self.right_flyout.extract_pages_requested.connect(self._extract_pages_list)
        self.right_flyout.insert_blank_requested.connect(self._insert_blank_after)
        self.right_flyout.pages_reordered.connect(self._mark_modified)
        eh.addWidget(self.right_flyout)

        self.rail = RightRail()
        self.rail.panel_requested.connect(self._on_rail_panel)
        eh.addWidget(self.rail)

        self.stack.addWidget(editor)

    def _build_statusbar(self):
        sb = QStatusBar(); self.setStatusBar(sb)
        self.modified_label = QLabel(""); sb.addWidget(self.modified_label)
        self.redact_label = QLabel(""); sb.addWidget(self.redact_label)
        self.zoom_label = QLabel("—"); sb.addPermanentWidget(self.zoom_label)
        self.tool_label = QLabel("Select"); sb.addPermanentWidget(self.tool_label)
        self.mode_label = QLabel("Continuous"); sb.addPermanentWidget(self.mode_label)

    def _install_shortcuts(self):
        # standard hotkeys
        QShortcut(QKeySequence.Open, self, activated=self.open_file)
        QShortcut(QKeySequence.Save, self, activated=self.save)
        QShortcut(QKeySequence.SaveAs, self, activated=self.save_as)
        QShortcut(QKeySequence.Print, self, activated=self.print_pdf)
        QShortcut(QKeySequence.Find, self, activated=self._toggle_search)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self._do_find_replace)
        QShortcut(QKeySequence.Undo, self, activated=self.undo)
        QShortcut(QKeySequence.Redo, self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._do_add_bookmark)
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._maybe_pick_link_target)
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._on_view(lambda v: v.zoom_in()))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._on_view(lambda v: v.zoom_out()))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=lambda: self._on_view(lambda v: v.fit_page()))
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._on_view(lambda v: v.fit_width()))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._on_view(lambda v: v.set_zoom(1.0)))
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_reading_mode)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, activated=self._do_tts)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self, activated=self._delete_current)
        # tool shortcuts
        QShortcut(QKeySequence("V"), self, activated=lambda: self._set_tool(Tool.SELECT))
        QShortcut(QKeySequence("H"), self, activated=lambda: self._set_tool(Tool.HAND))
        QShortcut(QKeySequence("Shift+T"), self, activated=lambda: self._set_tool(Tool.TEXT))
        QShortcut(QKeySequence("Shift+E"), self, activated=lambda: self._set_tool(Tool.EDIT_TEXT))
        QShortcut(QKeySequence("Shift+H"), self, activated=lambda: self._set_tool(Tool.HIGHLIGHT))
        QShortcut(QKeySequence("Shift+D"), self, activated=lambda: self._set_tool(Tool.DRAW))
        QShortcut(QKeySequence("PgUp"), self, activated=lambda: self._step_page(-1))
        QShortcut(QKeySequence("PgDown"), self, activated=lambda: self._step_page(+1))

    # ============== mode switching ==============
    def _switch_mode(self, key: str):
        self._mode = key
        if key in self.mode_panels:
            self.mode_panel_stack.setCurrentWidget(self.mode_panels[key])
        self.mode_panel_wrap.setVisible(True)
        # pick a sensible default tool for the mode if a doc is open
        if not self._current_tab(): return
        mode_default = {
            "edit":    Tool.EDIT_TEXT,
            "convert": Tool.SELECT,   # Convert mode is about output, not annotation
            "esign":   Tool.SIGNATURE,
            "all":     Tool.SELECT,
        }
        tool = mode_default.get(key)
        if tool is not None:
            # for signature, trigger the picker (which shows the signature dialog if not set)
            if tool == Tool.SIGNATURE:
                # do not auto-prompt; let user click Sign tool themselves
                self._set_tool(Tool.SELECT)
            else:
                self._set_tool(tool)
        # status hint per mode
        hints = {
            "edit": "Edit mode — hover over text to outline it, double-click to edit, or click 'Text' to add new text.",
            "convert": "Convert mode — pick an output format and click Convert.",
            "esign": "E-Sign mode — pick 'Add your signature' or use the fill tools.",
            "all": "All tools — pick an action from the left panel.",
        }
        if key in hints:
            self.statusBar().showMessage(hints[key], 5000)

    def _hide_mode_panel(self):
        self.mode_panel_wrap.setVisible(False)

    def _on_menu_action(self, key: str):
        mapping = {
            "open":       self.open_file,
            "save":       self.save,
            "save_as":    self.save_as,
            "print":      self.print_pdf,
            "properties": self._edit_metadata,
            "preferences":lambda: QMessageBox.information(self, "Preferences", "Preferences coming soon."),
            "about":      self._about,
            "exit":       self.close,
            "recent":     self._show_home,
        }
        fn = mapping.get(key)
        if fn: fn()

    # ============== document lifecycle ==============
    def _current_tab(self) -> Optional[DocTab]:
        v = self.canvas.current_view()
        if not v: return None
        for t in self._tabs:
            if t.view is v: return t
        return None

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
        # already open?
        for i, t in enumerate(self._tabs):
            if t.path and os.path.abspath(t.path) == os.path.abspath(path):
                self._switch_to_tab(i); return
        # show edit hint once per session
        if not getattr(self, "_edit_hint_shown", False):
            self._edit_hint_shown = True
            QTimer.singleShot(1200, lambda: self.statusBar().showMessage(
                "Tip: double-click any text in the page to edit it inline.", 7000))
        try:
            doc = PdfDocument(path)
        except PermissionError:
            pw, ok = QInputDialog.getText(
                self, "Password required",
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
        self._create_tab(doc, None, modified=True)

    def _create_tab(self, doc: PdfDocument, path: Optional[str], *, modified: bool = False):
        view = PdfGraphicsView()
        tab = DocTab(view=view, doc=doc, path=path, modified=modified)
        view.set_document(doc)
        view.page_changed.connect(lambda n, t=tab: self._on_view_page_changed(t, n))
        view.zoom_changed.connect(lambda z, t=tab: self._on_view_zoom_changed(t, z))
        view.document_modified.connect(lambda t=tab: self._on_view_modified(t))
        view.tool_done.connect(self._reset_select_tool)
        view.status.connect(lambda s: self.statusBar().showMessage(s, 5000))

        self._tabs.append(tab)
        self.canvas.add_view(view)
        self._refresh_top_tabs(active_index=len(self._tabs) - 1)
        self._show_editor()
        self._on_tab_switched()

    def _refresh_top_tabs(self, active_index: int):
        labels = []
        for t in self._tabs:
            name = os.path.basename(t.path) if t.path else "Untitled.pdf"
            if t.modified: name = name + " •"
            labels.append(name)
        self.top_bar.set_tabs(labels, active_index)

    def _switch_to_tab(self, idx: int):
        if 0 <= idx < len(self._tabs):
            self.canvas.set_current_view(self._tabs[idx].view)
            self.top_bar.set_active(idx)
            self._on_tab_switched()

    def _close_current_tab(self):
        v = self.canvas.current_view()
        if not v: return
        for i, t in enumerate(self._tabs):
            if t.view is v:
                self._close_tab(i); return

    def _close_tab(self, index: int):
        if index < 0 or index >= len(self._tabs): return
        t = self._tabs[index]
        if t.modified:
            r = QMessageBox.question(
                self, "Unsaved changes",
                f"Save changes to {os.path.basename(t.path or 'Untitled.pdf')}?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel: return
            if r == QMessageBox.Save:
                self._save_tab(t)
                if t.modified: return
        self.canvas.remove_view(t.view)
        t.doc.close()
        del self._tabs[index]
        if not self._tabs:
            self._show_home()
            self.top_bar.set_tabs([], -1)
        else:
            new_idx = min(index, len(self._tabs) - 1)
            self._switch_to_tab(new_idx)

    def _on_tab_switched(self):
        t = self._current_tab()
        if not t: return
        self.right_flyout.load_document(t.doc)
        self.setWindowTitle(f"{APP_NAME} — {os.path.basename(t.path or 'Untitled.pdf')}")
        # update page nav widget
        page = t.view.current_page_index()
        self.canvas.page_nav.set_page(page + 1, t.doc.page_count)
        self._on_view_zoom_changed(t, t.view.zoom)
        self.mode_label.setText(t.view.view_mode.value.replace("_", "-").capitalize())
        self._refresh_redact_label()
        self._update_enabled()

    # ============== save ==============
    def save(self):
        t = self._current_tab()
        if t: self._save_tab(t)

    def _save_tab(self, t: DocTab):
        if not t.path:
            return self._save_as_tab(t)
        try:
            out = t.doc.save()
            t.modified = False
            self._refresh_top_tabs(active_index=self._tabs.index(t))
            self.top_bar.set_active(self._tabs.index(t))
            self.modified_label.setText("")
            self._refresh_redact_label()
            self.statusBar().showMessage(f"Saved {out}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def save_as(self):
        t = self._current_tab()
        if t: self._save_as_tab(t)

    def _save_as_tab(self, t: DocTab):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF as", t.path or "untitled.pdf", "PDF (*.pdf)")
        if not path: return
        # ensure .pdf extension
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            out = t.doc.save(path)
            t.path = path
            t.modified = False
            idx = self._tabs.index(t)
            self._refresh_top_tabs(active_index=idx)
            self.modified_label.setText("")
            self.setWindowTitle(f"{APP_NAME} — {os.path.basename(path)}")
            add_recent(path)
            self.statusBar().showMessage(f"Saved to {out}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save as failed", str(e))

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
                painter.drawPixmap((r.width()-scaled.width())//2,
                                   (r.height()-scaled.height())//2, scaled)
        finally:
            painter.end()
        self.statusBar().showMessage("Printed", 2000)

    def _share(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Share", "Open a PDF first"); return
        if not t.path:
            QMessageBox.information(self, "Share",
                "Save the PDF before sharing."); return
        # On Windows, "share" can open Explorer at the file location
        try:
            os.startfile(os.path.dirname(t.path))
        except Exception:
            pass
        QMessageBox.information(self, "Share",
            f"File location:\n{t.path}\n\nAttach this file to email or upload to a sharing "
            "service of your choice.")

    # ============== view signals ==============
    def _on_view_page_changed(self, tab: DocTab, n: int):
        if tab is not self._current_tab(): return
        self.canvas.page_nav.set_page(n, tab.doc.page_count)

    def _on_view_zoom_changed(self, tab: DocTab, z: float):
        if tab is not self._current_tab(): return
        self.zoom_label.setText(f"{int(z*100)}%")

    def _on_view_modified(self, tab: DocTab):
        tab.modified = True
        idx = self._tabs.index(tab)
        self._refresh_top_tabs(active_index=idx)
        if tab is self._current_tab():
            self.modified_label.setText("●  unsaved changes")
        self._refresh_redact_label()

    def _mark_modified(self):
        t = self._current_tab()
        if t: self._on_view_modified(t)

    def _refresh_redact_label(self):
        t = self._current_tab()
        if t and t.doc.pending_redactions:
            self.redact_label.setText(f" |  {len(t.doc.pending_redactions)} redaction(s) queued — use Apply marked redactions")
        else:
            self.redact_label.setText("")

    # ============== rail panel toggle ==============
    def _on_rail_panel(self, key: str):
        if key == "" or key == self._side_panel_key:
            self._side_panel_key = ""
            self.right_flyout.hide()
            self.rail.clear()
            return
        self._side_panel_key = key
        if key == "ai":
            if not self.ai_panel.isVisible():
                self.ai_panel.show()
            self.right_flyout.hide()
            return
        if key in ("pages", "bookmarks", "comments", "attachments", "search"):
            t = self._current_tab()
            if t:
                self.right_flyout.load_document(t.doc)
            if key == "search":
                self._toggle_search()
                self.right_flyout.hide()
                return
            self.right_flyout.show_panel(key)
            self.right_flyout.show()

    # ============== search ==============
    def _toggle_search(self):
        if self.search.isVisible():
            self._close_search()
        else:
            self.search.show()
            self.search.input.setFocus(); self.search.input.selectAll()

    def _close_search(self):
        self.search.hide(); self._search_matches = []

    def _top_search_submit(self, text: str = ""):
        if not text:
            text = self.mode_bar.find.text()
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

    # ============== page navigation ==============
    def _goto_page_1(self, page_1: int):
        t = self._current_tab()
        if t: t.view.goto_page(max(0, min(t.doc.page_count - 1, page_1 - 1)))

    def _goto_page_0(self, page_0: int):
        t = self._current_tab()
        if t: t.view.goto_page(page_0)

    def _step_page(self, delta: int):
        t = self._current_tab()
        if t: t.view.goto_page(t.view.current_page_index() + delta)

    def _page_nav_overflow(self, key: str):
        mapping = {
            "single":     lambda: self._set_view_mode(ViewMode.SINGLE),
            "continuous": lambda: self._set_view_mode(ViewMode.CONTINUOUS),
            "two_page":   lambda: self._set_view_mode(ViewMode.TWO_PAGE),
            "reading":    self._toggle_reading_mode,
            "rot_cw":     lambda: self._rotate_current(90),
            "rot_ccw":    lambda: self._rotate_current(-90),
        }
        fn = mapping.get(key)
        if fn: fn()

    def _set_view_mode(self, mode: ViewMode):
        t = self._current_tab()
        if t:
            t.view.set_view_mode(mode)
            self.mode_label.setText(mode.value.replace("_", "-").capitalize())

    def _toggle_reading_mode(self):
        toolbars = self.findChildren(QToolBar)
        if self._reading_mode_saved is None:
            self._reading_mode_saved = {
                "menu": self.menuWidget().isVisible() if self.menuWidget() else False,
                "toolbars": [(tb, tb.isVisible()) for tb in toolbars],
                "rail": self.rail.isVisible(),
                "side": self.right_flyout.isVisible(),
                "mode_panel": self.mode_panel_wrap.isVisible(),
                "fullscreen": self.isFullScreen(),
                "ai": self.ai_panel.isVisible(),
            }
            if self.menuWidget(): self.menuWidget().hide()
            for tb in toolbars: tb.hide()
            self.rail.hide()
            self.right_flyout.hide()
            self.mode_panel_wrap.hide()
            self.ai_panel.hide()
            self.showFullScreen()
            self.statusBar().showMessage("Reading mode — F11 or Esc to exit", 4000)
        else:
            if self.menuWidget(): self.menuWidget().setVisible(self._reading_mode_saved["menu"])
            for tb, vis in self._reading_mode_saved["toolbars"]: tb.setVisible(vis)
            self.rail.setVisible(self._reading_mode_saved["rail"])
            self.right_flyout.setVisible(self._reading_mode_saved["side"])
            self.mode_panel_wrap.setVisible(self._reading_mode_saved["mode_panel"])
            self.ai_panel.setVisible(self._reading_mode_saved["ai"])
            if not self._reading_mode_saved["fullscreen"]: self.showNormal()
            self._reading_mode_saved = None

    # ============== undo / redo ==============
    def undo(self):
        t = self._current_tab()
        if t and t.doc.can_undo():
            t.doc.undo(); t.view.reload_all(); self.right_flyout.refresh()
            self._mark_modified()

    def redo(self):
        t = self._current_tab()
        if t and t.doc.can_redo():
            t.doc.redo(); t.view.reload_all(); self.right_flyout.refresh()
            self._mark_modified()

    # ============== tool selection ==============
    def _set_tool(self, tool: Tool):
        t = self._current_tab()
        if t: t.view.set_tool(tool)
        self.tool_label.setText(tool.value.replace("_", " ").capitalize())
        self.canvas.palette.set_active_tool(tool)

    def _reset_select_tool(self):
        self._set_tool(Tool.SELECT)

    # ============== mode-panel tool dispatch ==============
    def _execute_tool_action(self, key: str):
        """Central handler for every tool key emitted by mode panels and other UI."""
        # tool selectors
        tool_map = {
            "add_text":     Tool.TEXT,
            "edit_text":    Tool.EDIT_TEXT,
            "highlight":    Tool.HIGHLIGHT,
            "underline":    Tool.UNDERLINE,
            "strikeout":    Tool.STRIKEOUT,
            "squiggly":     Tool.SQUIGGLY,
            "draw":         Tool.DRAW,
            "rect":         Tool.RECT,
            "oval":         Tool.OVAL,
            "line":         Tool.LINE,
            "arrow":        Tool.ARROW,
            "polygon":      Tool.POLYGON,
            "note":         Tool.NOTE,
            "callout":      Tool.CALLOUT,
            "crop":         Tool.CROP,
            "redact_draw":  Tool.REDACT,
            "redact_mark":  Tool.REDACT_MARK,
            "eraser":       Tool.ERASER,
            "text_select":  Tool.TEXT_SELECT,
            "measure_dist": Tool.MEASURE_DIST,
            "measure_area": Tool.MEASURE_AREA,
            # E-sign quick fill primitives (drag a rectangle / point)
            "sign_x":     Tool.STRIKEOUT,
            "sign_check": Tool.UNDERLINE,
            "sign_dot":   Tool.RECT,
            "sign_box":   Tool.RECT,
            "sign_line":  Tool.LINE,
        }
        if key in tool_map:
            self._set_tool(tool_map[key])
            return

        # Pickers (signature, image, stamp, hyperlink) start a flow then arm a tool
        pickers = {
            "signature":    self._maybe_pick_signature,
            "initials":     self._maybe_pick_signature,
            "insert_image": self._maybe_pick_image,
            "stamp":        self._maybe_pick_stamp,
            "hyperlink":    self._maybe_pick_link_target,
            "link":         self._maybe_pick_link_target,
        }
        if key in pickers:
            pickers[key](); return

        # Dialog-driven document operations
        dispatch = {
            # Pages / organize
            "rotate_left":     lambda: self._rotate_current(-90),
            "rotate_right":    lambda: self._rotate_current(90),
            "rotate_right_one":lambda: self._rotate_current(90),
            "rotate_all":      self._do_rotate_all,
            "insert_blank":    self._insert_blank,
            "duplicate_pg":    self._duplicate_current,
            "delete_page":     self._delete_current,
            "extract_pg":      self._extract_pages_prompt,
            "insert_pages":    self._do_insert_pages,
            "replace_page":    self._do_replace_page,
            "reorder":         self._apply_thumb_order,
            "organize":        self._show_pages_flyout,
            "merge":           self._do_merge,
            "combine":         self._do_merge,
            "split":           self._do_split,

            # Content add
            "header_footer":   self._do_header_footer,
            "watermark":       self._do_watermark,
            "image_wm":        self._do_image_watermark,
            "page_numbers":    self._do_page_numbers,
            "add_bookmark":    self._do_add_bookmark,
            "find_replace":    self._do_find_replace,
            "metadata":        self._edit_metadata,

            # Protect
            "encrypt":         self._do_encrypt,
            "protect":         self._do_encrypt,
            "decrypt":         self._do_decrypt,
            "redact":          self._do_redact_action,
            "redact_apply":    self._apply_pending_redactions,
            "redact_text":     self._do_redact_text,
            "sanitize":        self._do_sanitize,
            "certify":         self._do_encrypt,

            # Convert
            "compress":        self._do_compress,
            "ocr":             self._do_ocr,
            "export":          self._do_export,
            "export_docx":     self._do_export_docx,
            "export_xlsx":     self._do_export_xlsx,
            "export_pptx":     lambda: QMessageBox.information(self, "Export", "PPTX export coming soon — use HTML or PNG for now."),
            "export_html":     self._do_export_html,
            "export_png":      self._do_export_png,
            "export_rtf":      self._do_export_rtf,
            "export_txt":      self._do_export_txt,
            "images_pdf":      self._do_images_to_pdf,
            "convert_pdf":     self._do_images_to_pdf,
            "create":          self._new_blank,
            "compare":         self._do_compare,
            "batch":           self._do_batch,
            "tts":             self._do_tts,
            "ai":              self._toggle_ai_panel,
            "summarize":       self._toggle_ai_panel,

            # Forms / signing
            "forms":           self._do_forms_fill,
            "forms_fill":      self._do_forms_fill,
            "add_field":       self._add_text_field,
            "add_checkbox":    self._add_checkbox,
            "save_certified":  self.save_as,

            # Mode tab shortcuts (clicked from All-tools panel)
            "edit":            lambda: self._switch_mode_and_focus("edit"),
            "esign":           lambda: self._switch_mode_and_focus("esign"),
            "comments":        lambda: self._on_rail_panel("comments"),

            # Measure / advanced
            "measure":         lambda: self._set_tool(Tool.MEASURE_DIST),
            "accessibility":   lambda: QMessageBox.information(self, "Accessibility", "Tag the document by saving the PDF — basic tagging is preserved on save."),
            "standards":       lambda: QMessageBox.information(self, "PDF standards", "Use the Compress tool with high quality preset for PDF/A-style output."),
            "index":           lambda: self.statusBar().showMessage("Search index is built on demand by the Find tool", 4000),
            "javascript":      lambda: QMessageBox.information(self, "JavaScript", "JavaScript actions in PDFs are blocked for safety. Use Sanitize to remove any present."),
            "guided":          self._do_batch,
            "custom_tool":     self._do_batch,
            "media":           self._maybe_pick_image,
        }
        fn = dispatch.get(key)
        if fn:
            fn()
        else:
            self.statusBar().showMessage(f"Unhandled action: {key}", 3000)

    def _show_pages_flyout(self):
        self.rail.select("pages")
        self._on_rail_panel("pages")

    def _switch_mode_and_focus(self, key: str):
        """Activate a mode tab (also picks the matching default tool)."""
        self.mode_bar.set_mode(key)

    # ============== signatures / images / stamps / links ==============
    def _maybe_pick_signature(self):
        if not self._current_tab():
            QMessageBox.information(self, "Sign", "Open a PDF first"); return
        if self._signature_pix is None:
            d = SignatureDialog(self)
            if d.exec() != SignatureDialog.Accepted or d.result_pixmap is None:
                return
            self._signature_pix = d.result_pixmap
        self._current_tab().view.set_signature(self._signature_pix)
        self.statusBar().showMessage("Drag a rectangle to place your signature", 4000)

    def _maybe_pick_image(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Image", "Open a PDF first"); return
        path, _ = QFileDialog.getOpenFileName(self, "Image to insert", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path: return
        t.view.set_image_to_place(path)
        self.statusBar().showMessage("Drag a rectangle to place the image", 4000)

    def _maybe_pick_stamp(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Stamp", "Open a PDF first"); return
        dlg = StampsDialog(self)
        chosen = {"pix": None}
        dlg.chosen.connect(lambda p: chosen.update(pix=p))
        dlg.exec()
        if chosen["pix"] is None: return
        t.view.set_stamp(chosen["pix"])
        self.statusBar().showMessage("Drag a rectangle to place the stamp", 4000)

    def _maybe_pick_link_target(self):
        t = self._current_tab()
        if not t:
            QMessageBox.information(self, "Link", "Open a PDF first"); return
        d = HyperlinkDialog(t.doc.page_count, self)
        if d.exec() != HyperlinkDialog.Accepted: return
        t.view.set_link_target(d.target())
        self.statusBar().showMessage("Drag a rectangle for the clickable area", 4000)

    # ============== page ops ==============
    def _rotate_current(self, deg: int):
        t = self._current_tab()
        if not t: return
        i = t.view.current_page_index()
        t.doc.rotate_page(i, deg)
        t.view.reload_all(); self.right_flyout.thumbs.refresh(i); self._mark_modified()

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
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()

    def _rotate_pages(self, indices: list, deg: int):
        t = self._current_tab()
        if not t: return
        for i in indices: t.doc.rotate_page(i, deg)
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()

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
        t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()

    def _duplicate_current(self):
        t = self._current_tab()
        if t: self._duplicate_page(t.view.current_page_index())

    def _duplicate_page(self, index: int):
        t = self._current_tab()
        if not t: return
        t.doc.duplicate_page(index)
        t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()

    def _insert_blank(self):
        t = self._current_tab()
        if not t: self._new_blank(); return
        i = t.view.current_page_index()
        t.doc.insert_blank_page(i + 1)
        t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()

    def _insert_blank_after(self, index: int):
        t = self._current_tab()
        if not t: return
        t.doc.insert_blank_page(index + 1)
        t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()

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
        order = self.right_flyout.thumbs.get_page_order()
        if order == list(range(t.doc.page_count)):
            self.statusBar().showMessage("No reorder needed", 2000); return
        import fitz
        new = fitz.open()
        for src_idx in order:
            new.insert_pdf(t.doc.doc, from_page=src_idx, to_page=src_idx)
        old = t.doc.doc; t.doc.snapshot(); t.doc.doc = new; old.close()
        t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()

    # ============== document ops ==============
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
        out, _ = QFileDialog.getSaveFileName(
            self, "Save decrypted", f"{Path(path).stem}_decrypted.pdf", "PDF (*.pdf)")
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
        if not self._current_tab(): return
        d = WatermarkDialog(self)
        if d.exec() != WatermarkDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_watermark(s["text"], opacity=s["opacity"], fontsize=s["fontsize"],
                            color=s["color"], rotation=s["rotation"])
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()

    def _do_image_watermark(self):
        if not self._current_tab(): return
        d = ImageWatermarkDialog(self)
        if d.exec() != ImageWatermarkDialog.Accepted: return
        s = d.settings()
        if not os.path.isfile(s["image_path"]):
            QMessageBox.warning(self, "Watermark", "Pick a valid image"); return
        t = self._current_tab()
        try:
            t.doc.add_image_watermark(s["image_path"], opacity=s["opacity"],
                                      scale=s["scale"], rotation=s["rotation"])
            t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()
        except Exception as e:
            QMessageBox.critical(self, "Watermark failed", str(e))

    def _do_page_numbers(self):
        if not self._current_tab(): return
        d = PageNumbersDialog(self)
        if d.exec() != PageNumbersDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_page_numbers(start=s["start"], fontsize=s["fontsize"],
                               position=s["position"], pattern=s["pattern"])
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()

    def _do_header_footer(self):
        if not self._current_tab(): return
        d = HeaderFooterDialog(self)
        if d.exec() != HeaderFooterDialog.Accepted: return
        s = d.settings()
        t = self._current_tab()
        t.doc.add_header_footer(**s)
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()

    def _do_redact_action(self):
        # show a quick prompt - drag tool or text-based
        choice, ok = QInputDialog.getItem(
            self, "Redact", "Redaction method:",
            ["Drag a rectangle (immediate)",
             "Mark areas first (preview before applying)",
             "Redact every occurrence of text"], 0, False)
        if not ok: return
        if choice.startswith("Drag"):
            self._set_tool(Tool.REDACT)
        elif choice.startswith("Mark"):
            self._set_tool(Tool.REDACT_MARK)
        else:
            self._do_redact_text()

    def _do_redact_text(self):
        if not self._current_tab(): return
        d = RedactTextDialog(self)
        if d.exec() != RedactTextDialog.Accepted: return
        terms = d.terms()
        if not terms: return
        t = self._current_tab(); total = 0
        for term in terms:
            total += t.doc.redact_text(term, case_sensitive=d.case.isChecked())
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()
        QMessageBox.information(self, "Redact", f"Redacted {total} occurrence(s).")

    def _apply_pending_redactions(self):
        t = self._current_tab()
        if not t: return
        n = t.view.apply_redact_marks()
        if n == 0:
            QMessageBox.information(self, "Redact",
                "No queued redactions. Use 'Mark for redaction' first.")
        else:
            self.statusBar().showMessage(f"Applied {n} redaction(s)", 4000)
            self.right_flyout.refresh()
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
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()
        QMessageBox.information(self, "Replace", f"Replaced {n} occurrence(s).")

    def _do_add_bookmark(self):
        t = self._current_tab()
        if not t: return
        d = AddBookmarkDialog(t.view.current_page_index(), self)
        if d.exec() != AddBookmarkDialog.Accepted: return
        s = d.settings()
        if not s["title"]: return
        t.doc.add_bookmark(s["title"], s["page"], level=s["level"])
        self.right_flyout.bookmarks.load(t.doc); self._mark_modified()

    def _do_insert_pages(self):
        t = self._current_tab()
        if not t: return
        d = InsertPagesDialog(t.view.current_page_index(), t.doc.page_count, self)
        if d.exec() != InsertPagesDialog.Accepted: return
        s = d.settings()
        if not os.path.isfile(s["source"]):
            QMessageBox.warning(self, "Insert", "Pick a source PDF"); return
        try:
            t.doc.insert_pdf(s["source"], s["at_index"], s["from_page"], s["to_page"])
            t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()
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
            t.view.set_document(t.doc); self.right_flyout.load_document(t.doc); self._mark_modified()
        except Exception as e:
            QMessageBox.critical(self, "Replace failed", str(e))

    def _do_crop_margins(self):
        t = self._current_tab()
        if not t: return
        d = CropDialog(self)
        if d.exec() != CropDialog.Accepted: return
        if d.is_reset():
            t.doc.reset_crop()
        else:
            t.doc.crop_all(d.margins(), mode="margins")
        t.view.reload_all(); self.right_flyout.refresh(); self._mark_modified()

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

    def _do_export_rtf(self):
        t = self._current_tab()
        if not t or not t.path:
            QMessageBox.information(self, "Export", "Save the PDF first"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save RTF", f"{Path(t.path).stem}.rtf", "RTF (*.rtf)")
        if not out: return
        try:
            from .converters import pdf_to_rtf
            pdf_to_rtf(t.path, out)
            QMessageBox.information(self, "Export", f"Saved to {out}")
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
        t = self._current_tab()
        if not t: return
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

    # ============== compare / batch / tts / forms ==============
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
            (i, t.doc.get_text(i)) for i in range(t.doc.page_count) if t.doc.get_text(i).strip()
        ])
        self._tts_dialog.show()
        self._tts_dialog.raise_(); self._tts_dialog.activateWindow()

    def _do_forms_fill(self):
        t = self._current_tab()
        if not t: return
        if not t.doc.list_form_fields():
            QMessageBox.information(self, "Forms",
                "This PDF has no fillable form fields.\n"
                "Use 'Add text field' or 'Add checkbox' under E-Sign to create some."); return
        d = FormFillDialog(t.doc, self)
        d.fields_updated.connect(lambda: (t.view.reload_all(), self._mark_modified()))
        d.exec()

    def _add_text_field(self):
        t = self._current_tab()
        if not t: return
        i = t.view.current_page_index()
        info = t.doc.page_info(i)
        rect = (info.width * 0.2, info.height * 0.2, info.width * 0.6, info.height * 0.2 + 24)
        name, ok = QInputDialog.getText(self, "Field name", "Field name:", text=f"field_{i+1}")
        if not ok or not name: return
        t.doc.add_form_text_field(i, rect, name, value="")
        t.view.reload_all(); self._mark_modified()

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

    def _do_share_for_signing(self):
        QMessageBox.information(self, "Share for signing",
            "Save the document and email it to anyone who needs to sign.\n\n"
            "They can open it in Chudi PDF Pro (or any PDF viewer), use the Sign tool, "
            "and return the signed copy to you.")

    # ============== AI panel ==============
    def _toggle_ai_panel(self):
        if self.ai_panel.isVisible():
            self.ai_panel.hide()
            self.rail.clear()
        else:
            t = self._current_tab()
            if not t:
                QMessageBox.information(self, "AI Assistant", "Open a PDF first")
                return
            self.rail.select("ai")
            self.ai_panel.show()

    def _ai_current_text(self) -> str:
        t = self._current_tab()
        if not t: return ""
        return t.doc.get_text(t.view.current_page_index())

    # ============== state ==============
    def _update_enabled(self):
        on = self._current_tab() is not None
        # mode bar actions
        for btn in (self.mode_bar.save_btn, self.mode_bar.cloud_btn,
                    self.mode_bar.print_btn, self.mode_bar.share_btn,
                    self.mode_bar.ai_btn, self.mode_bar.ask_ai):
            btn.setEnabled(on)
        # mode panel buttons are always shown - tools just show a warning if no doc

    def _about(self):
        QMessageBox.information(self, f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2><p>Version {__version__}</p>"
            "<p>A complete PDF editing suite — view, edit, annotate, sign, "
            "merge, split, compress, OCR, convert, redact, compare, and more.</p>"
            "<p>All edits stay on your machine. No cloud upload.</p>"
            "<p>Built with PySide6, PyMuPDF, pikepdf, python-docx, openpyxl, and pyttsx3.</p>")

    # ============== drag-and-drop ==============
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(".pdf")
                                          for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(".pdf"): self.load_pdf(p)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._reading_mode_saved is not None:
            self._toggle_reading_mode(); return
        super().keyPressEvent(e)

    def closeEvent(self, e):
        for i in range(len(self._tabs) - 1, -1, -1):
            t = self._tabs[i]
            if t.modified:
                self._switch_to_tab(i)
                r = QMessageBox.question(self, "Unsaved changes",
                    f"Save changes to {os.path.basename(t.path or 'Untitled.pdf')}?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if r == QMessageBox.Cancel: e.ignore(); return
                if r == QMessageBox.Save:
                    self._save_tab(t)
                    if t.modified: e.ignore(); return
            t.doc.close()
        if self._tts_dialog: self._tts_dialog.close()
        e.accept()
