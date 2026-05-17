"""Wraps a PdfGraphicsView with floating-overlay widgets (palette, page nav)."""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, Signal, QEvent, QPoint
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget, QStackedWidget, QHBoxLayout, QVBoxLayout

from .pdf_viewer import PdfGraphicsView, Tool, ViewMode
from .floating_palette import FloatingPalette
from .page_nav_widget import PageNavWidget


class CanvasContainer(QWidget):
    """Holds a stack of PdfGraphicsViews (one per open document) plus overlays."""
    tool_selected = Signal(object)        # Tool enum
    page_change = Signal(int)             # 1-based
    page_step = Signal(int)               # +1 / -1
    zoom_in = Signal()
    zoom_out = Signal()
    fit_page = Signal()
    overflow_action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#535353;")
        # the view stack fills the whole area
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("background:#535353;")

        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        v.addWidget(self.stack, 1)

        # floating overlays (parented to self so they sit ABOVE the stack visually)
        self.palette = FloatingPalette(self)
        self.palette.tool_selected.connect(self.tool_selected.emit)

        self.page_nav = PageNavWidget(self)
        self.page_nav.page_change.connect(self.page_change.emit)
        self.page_nav.page_step.connect(self.page_step.emit)
        self.page_nav.zoom_in.connect(self.zoom_in.emit)
        self.page_nav.zoom_out.connect(self.zoom_out.emit)
        self.page_nav.reload_clicked.connect(self.fit_page.emit)
        self.page_nav.overflow_action.connect(self.overflow_action.emit)

        # initial positioning - will be updated in resizeEvent
        self._reposition_overlays()

    def add_view(self, view: PdfGraphicsView) -> int:
        idx = self.stack.addWidget(view)
        self.stack.setCurrentIndex(idx)
        self._reposition_overlays()
        return idx

    def remove_view(self, view: PdfGraphicsView):
        idx = self.stack.indexOf(view)
        if idx >= 0:
            self.stack.removeWidget(view)
            view.setParent(None)

    def set_current_view(self, view: PdfGraphicsView):
        idx = self.stack.indexOf(view)
        if idx >= 0:
            self.stack.setCurrentIndex(idx)

    def current_view(self) -> Optional[PdfGraphicsView]:
        w = self.stack.currentWidget()
        return w if isinstance(w, PdfGraphicsView) else None

    def resizeEvent(self, e: QResizeEvent):
        super().resizeEvent(e)
        self._reposition_overlays()

    def _reposition_overlays(self):
        # palette: vertically centered near left edge of canvas
        pw = self.palette.sizeHint().width() or 58
        ph = self.palette.sizeHint().height() or 420
        # actually let it be its own size
        self.palette.adjustSize()
        ph = self.palette.height()
        self.palette.move(16, max(8, (self.height() - ph) // 2))
        self.palette.raise_()

        # page nav: bottom-right corner
        self.page_nav.adjustSize()
        nw = self.page_nav.width()
        nh = self.page_nav.height()
        self.page_nav.move(self.width() - nw - 16, self.height() - nh - 16)
        self.page_nav.raise_()

    def set_palette_visible(self, on: bool): self.palette.setVisible(on)
    def set_page_nav_visible(self, on: bool): self.page_nav.setVisible(on)
