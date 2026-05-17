"""PDF viewer widget with all editing-tool overlays.

Pages flow vertically (continuous) or are shown one-at-a-time (single) or
side-by-side (two-page). Each tool drives a different interaction on
mouse press / move / release. Edits are committed to the PdfDocument and
the affected page is re-rendered.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PySide6.QtCore import (
    QPointF, QRectF, Qt, Signal, QTimer, QEvent
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QImage, QKeyEvent, QMouseEvent, QPainter, QPen,
    QPixmap, QPolygonF, QWheelEvent, QCursor, QPainterPath
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem, QGraphicsPixmapItem,
    QGraphicsPolygonItem, QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem,
    QGraphicsView, QInputDialog, QMenu, QApplication, QGraphicsLineItem
)

import fitz

from .pdf_engine import PdfDocument, TextSpan


class Tool(Enum):
    SELECT = "select"
    HAND = "hand"
    TEXT = "text"
    EDIT_TEXT = "edit_text"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    SQUIGGLY = "squiggly"
    DRAW = "draw"
    RECT = "rect"
    OVAL = "oval"
    LINE = "line"
    ARROW = "arrow"
    POLYGON = "polygon"
    NOTE = "note"
    CALLOUT = "callout"
    REDACT = "redact"
    REDACT_MARK = "redact_mark"
    IMAGE = "image"
    SIGNATURE = "signature"
    STAMP = "stamp"
    CROP = "crop"
    LINK = "link"
    MEASURE_DIST = "measure_dist"
    MEASURE_AREA = "measure_area"
    TEXT_SELECT = "text_select"
    ERASER = "eraser"


class ViewMode(Enum):
    CONTINUOUS = "continuous"
    SINGLE = "single"
    TWO_PAGE = "two_page"


@dataclass
class PageView:
    index: int
    item: QGraphicsPixmapItem
    bg: QGraphicsRectItem
    rect_in_scene: QRectF
    page_w: float  # PDF points
    page_h: float


class PdfGraphicsView(QGraphicsView):
    page_changed = Signal(int)
    zoom_changed = Signal(float)
    status = Signal(str)
    document_modified = Signal()
    tool_done = Signal()  # emitted after a one-shot tool completes so MainWindow can reset

    PAGE_GAP = 18
    BG_COLOR = QColor("#525252")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setBackgroundBrush(QBrush(self.BG_COLOR))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)  # required for hover-without-press
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.verticalScrollBar().valueChanged.connect(self._emit_current_page)

        self.doc: Optional[PdfDocument] = None
        self.pages: list[PageView] = []
        self.zoom: float = 1.25
        self.view_mode: ViewMode = ViewMode.CONTINUOUS
        self.tool: Tool = Tool.SELECT
        self.draw_color: QColor = QColor("#000000")
        self.highlight_color: QColor = QColor(255, 235, 59)
        self.text_size: int = 12
        self.draw_width: float = 1.5

        # interaction state
        self._press_pos: Optional[QPointF] = None
        self._press_page: Optional[int] = None
        self._preview: Optional[QGraphicsItem] = None
        self._preview_extra: list[QGraphicsItem] = []
        self._draw_points: list[QPointF] = []
        self._draw_path: Optional[QPainterPath] = None
        self._polygon_points: list[QPointF] = []
        self._polygon_page: Optional[int] = None
        self._panning = False
        self._pan_last: Optional[QPointF] = None
        self._signature_pixmap: Optional[QPixmap] = None
        self._image_path: Optional[str] = None
        self._stamp_pixmap: Optional[QPixmap] = None
        self._link_target: Optional[dict] = None  # {"kind":"uri","value":...}
        self._edit_proxy = None  # inline editor proxy widget
        self._redact_marks: list[QGraphicsRectItem] = []  # visual marks for queued redactions
        self._hover_outline: Optional[QGraphicsRectItem] = None  # text span hover indicator

    # ---------------- document ----------------
    def set_document(self, doc: Optional[PdfDocument]):
        self.doc = doc
        self.scene().clear()
        self.pages.clear()
        self._redact_marks.clear()
        if not doc:
            return
        self._layout_pages()
        self._render_visible()
        self.page_changed.emit(1)

    def reload_all(self):
        if not self.doc: return
        cur = self.current_page_index()
        self.scene().clear()
        self.pages.clear()
        self._layout_pages()
        self._render_visible()
        self.goto_page(cur)

    def _layout_pages(self):
        y = 0.0
        max_w = 0.0
        if self.view_mode == ViewMode.TWO_PAGE:
            i = 0
            while i < self.doc.page_count:
                # Pair: (i) and (i+1) if exists. Put first page alone if classical "cover".
                a = self.doc.page_info(i)
                a_w = a.width * self.zoom; a_h = a.height * self.zoom
                row_h = a_h
                if i + 1 < self.doc.page_count:
                    b = self.doc.page_info(i + 1)
                    b_w = b.width * self.zoom; b_h = b.height * self.zoom
                    row_h = max(a_h, b_h)
                    x_a = 0; x_b = a_w + 12
                    self._add_page_to_scene(a, x_a, y, a_w, a_h)
                    self._add_page_to_scene(b, x_b, y, b_w, b_h)
                    max_w = max(max_w, a_w + b_w + 12)
                else:
                    self._add_page_to_scene(a, 0, y, a_w, a_h)
                    max_w = max(max_w, a_w)
                y += row_h + self.PAGE_GAP
                i += 2
        elif self.view_mode == ViewMode.SINGLE:
            info = self.doc.page_info(0)
            w = info.width * self.zoom; h = info.height * self.zoom
            self._add_page_to_scene(info, 0, 0, w, h)
            max_w = w; y = h
        else:  # CONTINUOUS
            for i in range(self.doc.page_count):
                info = self.doc.page_info(i)
                w = info.width * self.zoom; h = info.height * self.zoom
                self._add_page_to_scene(info, 0, y, w, h)
                y += h + self.PAGE_GAP
                max_w = max(max_w, w)
        self.scene().setSceneRect(QRectF(-50, -20, max_w + 100, y + 40))

    def _add_page_to_scene(self, info, x: float, y: float, w: float, h: float):
        bg = QGraphicsRectItem(0, 0, w, h)
        bg.setBrush(QBrush(Qt.white))
        bg.setPen(QPen(QColor("#222"), 0.5))
        bg.setZValue(-1); bg.setPos(x, y)
        item = QGraphicsPixmapItem()
        item.setPos(x, y); item.setZValue(0)
        self.scene().addItem(bg); self.scene().addItem(item)
        rect = QRectF(x, y, w, h)
        self.pages.append(PageView(info.index, item, bg, rect, info.width, info.height))

    def _render_visible(self):
        if not self.doc: return
        vr = self.mapToScene(self.viewport().rect()).boundingRect()
        for pv in self.pages:
            if pv.rect_in_scene.intersects(vr):
                if pv.item.pixmap().isNull():
                    self._render_page(pv)
            else:
                if not pv.item.pixmap().isNull() and abs(pv.rect_in_scene.top() - vr.top()) > 4000:
                    pv.item.setPixmap(QPixmap())

    def _render_page(self, pv: PageView):
        data = self.doc.render(pv.index, zoom=self.zoom * 1.5)
        img = QImage.fromData(data)
        pix = QPixmap.fromImage(img.scaled(
            int(pv.rect_in_scene.width()),
            int(pv.rect_in_scene.height()),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        pv.item.setPixmap(pix)

    def refresh_page(self, page_index: int):
        if not self.doc: return
        for pv in self.pages:
            if pv.index == page_index:
                self._render_page(pv)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._render_visible()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._render_visible()

    # ---------------- view modes ----------------
    def set_view_mode(self, mode: ViewMode):
        if mode == self.view_mode: return
        cur = self.current_page_index()
        self.view_mode = mode
        self.scene().clear()
        self.pages.clear()
        if self.doc:
            self._layout_pages()
            self._render_visible()
            self.goto_page(cur)

    # ---------------- zoom ----------------
    def set_zoom(self, zoom: float):
        zoom = max(0.25, min(zoom, 5.0))
        if abs(zoom - self.zoom) < 0.001: return
        cur = self.current_page_index()
        self.zoom = zoom
        self.scene().clear()
        self.pages.clear()
        if self.doc:
            self._layout_pages()
            self._render_visible()
            self.goto_page(cur)
        self.zoom_changed.emit(self.zoom)

    def zoom_in(self):  self.set_zoom(self.zoom * 1.2)
    def zoom_out(self): self.set_zoom(self.zoom / 1.2)

    def fit_width(self):
        if not self.pages: return
        page = self.pages[min(self.current_page_index(), len(self.pages) - 1)]
        self.set_zoom((self.viewport().width() - 60) / page.page_w)

    def fit_page(self):
        if not self.pages: return
        page = self.pages[min(self.current_page_index(), len(self.pages) - 1)]
        vw = self.viewport().width() - 60
        vh = self.viewport().height() - 60
        self.set_zoom(min(vw / page.page_w, vh / page.page_h))

    # ---------------- nav ----------------
    def goto_page(self, index: int):
        for pv in self.pages:
            if pv.index == index:
                self.centerOn(pv.rect_in_scene.center())
                self.page_changed.emit(index + 1)
                return
        if 0 <= index < (self.doc.page_count if self.doc else 0):
            # not in current layout - rebuild or jump to nearest
            if self.pages:
                self.centerOn(self.pages[0].rect_in_scene.center())
            self.page_changed.emit(index + 1)

    def current_page_index(self) -> int:
        if not self.pages: return 0
        center_y = self.mapToScene(self.viewport().rect().center()).y()
        best = self.pages[0].index
        for pv in self.pages:
            if pv.rect_in_scene.top() <= center_y <= pv.rect_in_scene.bottom():
                return pv.index
            if pv.rect_in_scene.top() < center_y:
                best = pv.index
        return best

    def _emit_current_page(self, *_):
        self.page_changed.emit(self.current_page_index() + 1)
        self._render_visible()

    # ---------------- coordinate conversion ----------------
    def _page_at_scene(self, sp: QPointF) -> Optional[PageView]:
        for pv in self.pages:
            if pv.rect_in_scene.contains(sp):
                return pv
        return None

    def _scene_to_pdf(self, pv: PageView, sp: QPointF) -> tuple[float, float]:
        local_x = sp.x() - pv.rect_in_scene.left()
        local_y = sp.y() - pv.rect_in_scene.top()
        info = self.doc.page_info(pv.index)
        rot = info.rotation
        scale_x = pv.page_w / pv.rect_in_scene.width()
        scale_y = pv.page_h / pv.rect_in_scene.height()
        px = local_x * scale_x
        py = local_y * scale_y
        if rot == 0:   return px, py
        if rot == 90:  return py, pv.page_w - px
        if rot == 180: return pv.page_w - px, pv.page_h - py
        if rot == 270: return pv.page_h - py, px
        return px, py

    def _pdf_to_scene(self, pv: PageView, x: float, y: float) -> QPointF:
        scale_x = pv.rect_in_scene.width() / pv.page_w
        scale_y = pv.rect_in_scene.height() / pv.page_h
        return QPointF(pv.rect_in_scene.left() + x * scale_x,
                       pv.rect_in_scene.top() + y * scale_y)

    # ---------------- tools ----------------
    def set_tool(self, tool: Tool):
        self._cancel_edit()
        self._cancel_polygon()
        self._clear_hover_outline()
        self.tool = tool
        cursors = {
            Tool.SELECT: Qt.ArrowCursor,
            Tool.HAND: Qt.OpenHandCursor,
            Tool.TEXT: Qt.IBeamCursor,
            Tool.EDIT_TEXT: Qt.IBeamCursor,
            Tool.HIGHLIGHT: Qt.CrossCursor,
            Tool.UNDERLINE: Qt.CrossCursor,
            Tool.STRIKEOUT: Qt.CrossCursor,
            Tool.SQUIGGLY: Qt.CrossCursor,
            Tool.DRAW: Qt.CrossCursor,
            Tool.RECT: Qt.CrossCursor,
            Tool.OVAL: Qt.CrossCursor,
            Tool.LINE: Qt.CrossCursor,
            Tool.ARROW: Qt.CrossCursor,
            Tool.POLYGON: Qt.CrossCursor,
            Tool.REDACT: Qt.CrossCursor,
            Tool.REDACT_MARK: Qt.CrossCursor,
            Tool.IMAGE: Qt.CrossCursor,
            Tool.SIGNATURE: Qt.CrossCursor,
            Tool.STAMP: Qt.CrossCursor,
            Tool.NOTE: Qt.CrossCursor,
            Tool.CALLOUT: Qt.CrossCursor,
            Tool.CROP: Qt.CrossCursor,
            Tool.LINK: Qt.CrossCursor,
            Tool.MEASURE_DIST: Qt.CrossCursor,
            Tool.MEASURE_AREA: Qt.CrossCursor,
            Tool.TEXT_SELECT: Qt.IBeamCursor,
            Tool.ERASER: Qt.CrossCursor,
        }
        self.setCursor(cursors.get(tool, Qt.ArrowCursor))

    def set_signature(self, pixmap: QPixmap):
        self._signature_pixmap = pixmap
        self.set_tool(Tool.SIGNATURE)

    def set_image_to_place(self, path: str):
        self._image_path = path
        self.set_tool(Tool.IMAGE)

    def set_stamp(self, pixmap: QPixmap):
        self._stamp_pixmap = pixmap
        self.set_tool(Tool.STAMP)

    def set_link_target(self, target: dict):
        self._link_target = target
        self.set_tool(Tool.LINK)

    # ---------------- events ----------------
    def wheelEvent(self, e: QWheelEvent):
        if e.modifiers() & Qt.ControlModifier:
            if e.angleDelta().y() > 0: self.zoom_in()
            else: self.zoom_out()
            e.accept()
        else:
            super().wheelEvent(e)
            self._render_visible()

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        """Double-click anywhere on a text span jumps straight into inline edit."""
        if e.button() != Qt.LeftButton:
            return super().mouseDoubleClickEvent(e)
        sp = self.mapToScene(e.position().toPoint())
        pv = self._page_at_scene(sp)
        if not pv:
            return super().mouseDoubleClickEvent(e)
        # if we're in a drawing/markup tool that already uses double-click (polygon),
        # let it handle the event
        if self.tool == Tool.POLYGON:
            return super().mouseDoubleClickEvent(e)
        # if the current tool is one that explicitly uses single-click for its action,
        # honor the tool. Otherwise, treat double-click as edit-text.
        if self.tool in (Tool.TEXT, Tool.NOTE, Tool.CALLOUT, Tool.HAND):
            return super().mouseDoubleClickEvent(e)
        # try to edit text under the cursor
        x, y = self._scene_to_pdf(pv, sp)
        span = self.doc.hit_test_text(pv.index, x, y)
        if span:
            # cancel any pending preview so the editor takes over cleanly
            self._end_preview()
            self._press_pos = None
            self._press_page = None
            self._show_inline_editor(pv, span)
            e.accept()
            return
        # No text under cursor - tell the user what to do
        self.status.emit("Double-click on a word to edit it, or pick a tool from the palette.")

    def mousePressEvent(self, e: QMouseEvent):
        # middle-button pan
        if e.button() == Qt.MiddleButton or (self.tool == Tool.HAND and e.button() == Qt.LeftButton):
            self._panning = True
            self._pan_last = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)

        sp = self.mapToScene(e.position().toPoint())
        pv = self._page_at_scene(sp)
        if not pv:
            return super().mousePressEvent(e)

        self._press_pos = sp
        self._press_page = pv.index

        # polygon handling - first click adds vertex, double-click closes
        if self.tool == Tool.POLYGON:
            self._poly_add_point(pv, sp, e.type() == QEvent.MouseButtonDblClick)
            return

        if self.tool == Tool.EDIT_TEXT:
            self._begin_edit_text(pv, sp); return
        if self.tool == Tool.TEXT:
            self._begin_insert_text(pv, sp); return
        if self.tool == Tool.NOTE:
            self._add_note(pv, sp); return
        if self.tool == Tool.CALLOUT:
            self._begin_callout(pv, sp); return
        if self.tool == Tool.ERASER:
            x, y = self._scene_to_pdf(pv, sp)
            if self.doc.delete_annot_at(pv.index, (x, y)):
                self.refresh_page(pv.index); self.document_modified.emit()
            return
        if self.tool == Tool.MEASURE_DIST:
            self._begin_line(sp); return

        if self.tool == Tool.DRAW:
            self._draw_points = [sp]
            self._draw_path = QPainterPath(sp)
            self._preview = QGraphicsPathItem(self._draw_path)
            pen = QPen(self.draw_color, self.draw_width * self.zoom)
            pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
            self._preview.setPen(pen)
            self.scene().addItem(self._preview); return

        if self.tool in (Tool.LINE, Tool.ARROW):
            self._begin_line(sp); return

        if self.tool == Tool.OVAL:
            self._preview = QGraphicsEllipseItem()
            self._preview.setPen(QPen(self._preview_color(), 1.5 * self.zoom, Qt.DashLine))
            fill = QColor(self._preview_color()); fill.setAlpha(40)
            self._preview.setBrush(QBrush(fill))
            self.scene().addItem(self._preview); return

        # rect-style tools
        if self.tool in (Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT, Tool.SQUIGGLY,
                         Tool.RECT, Tool.REDACT, Tool.REDACT_MARK, Tool.IMAGE,
                         Tool.SIGNATURE, Tool.STAMP, Tool.CROP, Tool.LINK,
                         Tool.MEASURE_AREA, Tool.TEXT_SELECT):
            self._preview = QGraphicsRectItem()
            self._preview.setPen(QPen(self._preview_color(), 1.5, Qt.DashLine))
            fill = QColor(self._preview_color()); fill.setAlpha(40)
            self._preview.setBrush(QBrush(fill))
            self.scene().addItem(self._preview); return

    def _preview_color(self) -> QColor:
        if self.tool == Tool.HIGHLIGHT: return self.highlight_color
        if self.tool == Tool.UNDERLINE: return QColor(0, 100, 255)
        if self.tool == Tool.STRIKEOUT: return QColor(220, 50, 50)
        if self.tool == Tool.SQUIGGLY: return QColor(180, 70, 220)
        if self.tool == Tool.REDACT: return QColor(0, 0, 0)
        if self.tool == Tool.REDACT_MARK: return QColor(0, 0, 0)
        if self.tool == Tool.CROP: return QColor(255, 165, 0)
        if self.tool == Tool.LINK: return QColor(0, 150, 200)
        if self.tool == Tool.MEASURE_AREA: return QColor(180, 120, 0)
        if self.tool == Tool.TEXT_SELECT: return QColor(0, 122, 204)
        return self.draw_color

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._panning and self._pan_last is not None:
            d = e.position() - self._pan_last
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            self._pan_last = e.position()
            return

        sp = self.mapToScene(e.position().toPoint())

        if isinstance(self._preview, QGraphicsRectItem) and self._press_pos is not None:
            self._preview.setRect(QRectF(self._press_pos, sp).normalized())
        elif isinstance(self._preview, QGraphicsEllipseItem) and self._press_pos is not None:
            self._preview.setRect(QRectF(self._press_pos, sp).normalized())
        elif isinstance(self._preview, QGraphicsLineItem) and self._press_pos is not None:
            self._preview.setLine(self._press_pos.x(), self._press_pos.y(), sp.x(), sp.y())
        elif self.tool == Tool.DRAW and self._draw_path is not None:
            self._draw_path.lineTo(sp)
            self._preview.setPath(self._draw_path)
            self._draw_points.append(sp)
        else:
            # hover outline when EDIT_TEXT or SELECT (no drag in progress)
            if self.tool in (Tool.EDIT_TEXT, Tool.SELECT) and self._press_page is None:
                self._update_hover_outline(sp)
            else:
                self._clear_hover_outline()
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self._panning:
            self._panning = False
            self._pan_last = None
            self.setCursor(Qt.OpenHandCursor if self.tool == Tool.HAND else Qt.ArrowCursor)
            return
        if e.button() != Qt.LeftButton:
            return super().mouseReleaseEvent(e)
        if self._press_page is None:
            return super().mouseReleaseEvent(e)
        if self.tool == Tool.POLYGON:
            return  # polygon handled on press
        sp = self.mapToScene(e.position().toPoint())
        pv = self.pages[self._find_page_view_index(self._press_page)]

        try:
            if self.tool == Tool.DRAW and self._draw_points and len(self._draw_points) > 1:
                pdf_pts = [self._scene_to_pdf(pv, p) for p in self._draw_points]
                c = self.draw_color
                self.doc.add_freehand(pv.index, [fitz.Point(*pt) for pt in pdf_pts],
                                      color=(c.redF(), c.greenF(), c.blueF()),
                                      width=self.draw_width)
                self.refresh_page(pv.index); self.document_modified.emit()
            elif isinstance(self._preview, QGraphicsLineItem):
                p1 = self._scene_to_pdf(pv, self._preview.line().p1())
                p2 = self._scene_to_pdf(pv, self._preview.line().p2())
                self._commit_line_tool(pv.index, p1, p2)
            elif isinstance(self._preview, QGraphicsEllipseItem):
                r = self._preview.rect()
                if r.width() > 2 and r.height() > 2:
                    x0, y0 = self._scene_to_pdf(pv, r.topLeft())
                    x1, y1 = self._scene_to_pdf(pv, r.bottomRight())
                    rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                    self._commit_oval_tool(pv.index, rect)
            elif isinstance(self._preview, QGraphicsRectItem):
                r = self._preview.rect()
                if r.width() > 2 and r.height() > 2:
                    x0, y0 = self._scene_to_pdf(pv, r.topLeft())
                    x1, y1 = self._scene_to_pdf(pv, r.bottomRight())
                    rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                    scene_rect = QRectF(r)
                    self._commit_rect_tool(pv.index, rect, scene_rect, pv)
        finally:
            self._end_preview()
            self._press_pos = None
            self._press_page = None

    def _find_page_view_index(self, page_idx: int) -> int:
        for i, pv in enumerate(self.pages):
            if pv.index == page_idx: return i
        return 0

    def _end_preview(self):
        if self._preview and self._preview.scene():
            self.scene().removeItem(self._preview)
        self._preview = None
        for extra in self._preview_extra:
            if extra.scene():
                self.scene().removeItem(extra)
        self._preview_extra.clear()
        self._draw_points = []
        self._draw_path = None

    # ---------------- commit helpers ----------------
    def _commit_rect_tool(self, page_idx: int, rect: tuple, scene_rect: QRectF, pv: PageView):
        if self.tool == Tool.HIGHLIGHT:
            q = self._rect_to_quad(rect); self.doc.add_highlight(page_idx, [q])
        elif self.tool == Tool.UNDERLINE:
            q = self._rect_to_quad(rect); self.doc.add_underline(page_idx, [q])
        elif self.tool == Tool.STRIKEOUT:
            q = self._rect_to_quad(rect); self.doc.add_strikeout(page_idx, [q])
        elif self.tool == Tool.SQUIGGLY:
            q = self._rect_to_quad(rect); self.doc.add_squiggly(page_idx, [q])
        elif self.tool == Tool.RECT:
            c = self.draw_color
            self.doc.add_rect(page_idx, rect, color=(c.redF(), c.greenF(), c.blueF()),
                              width=self.draw_width)
        elif self.tool == Tool.REDACT:
            self.doc.redact(page_idx, rect)
        elif self.tool == Tool.REDACT_MARK:
            self.doc.mark_for_redaction(page_idx, rect)
            mark = QGraphicsRectItem(scene_rect)
            mark.setPen(QPen(QColor("#ff5252"), 1.5, Qt.DashLine))
            fill = QColor(0, 0, 0); fill.setAlpha(120)
            mark.setBrush(QBrush(fill))
            mark.setZValue(2)
            self.scene().addItem(mark)
            self._redact_marks.append(mark)
            self.status.emit(f"{len(self.doc.pending_redactions)} redaction(s) queued")
            self.document_modified.emit()
            return
        elif self.tool == Tool.IMAGE and self._image_path:
            self.doc.add_image(page_idx, rect, self._image_path)
            self._image_path = None
            self.tool_done.emit()
        elif self.tool == Tool.SIGNATURE and self._signature_pixmap:
            from io import BytesIO
            buf = BytesIO(); self._signature_pixmap.save(buf, "PNG")
            self.doc.add_image_bytes(page_idx, rect, buf.getvalue())
        elif self.tool == Tool.STAMP and self._stamp_pixmap:
            from io import BytesIO
            buf = BytesIO(); self._stamp_pixmap.save(buf, "PNG")
            self.doc.add_image_bytes(page_idx, rect, buf.getvalue())
            self._stamp_pixmap = None
            self.tool_done.emit()
        elif self.tool == Tool.CROP:
            self.doc.crop_page(page_idx, rect)
            self.reload_all()
            self.tool_done.emit()
            return
        elif self.tool == Tool.LINK and self._link_target:
            if self._link_target.get("kind") == "uri":
                self.doc.add_link_url(page_idx, rect, self._link_target["value"])
            elif self._link_target.get("kind") == "page":
                self.doc.add_link_to_page(page_idx, rect, int(self._link_target["value"]))
            self._link_target = None
            self.tool_done.emit()
        elif self.tool == Tool.MEASURE_AREA:
            # show overlay with area measurement; no PDF change
            w = abs(rect[2] - rect[0])
            h = abs(rect[3] - rect[1])
            area = w * h  # in PDF points sq.
            self.status.emit(f"Area: {area:.1f} pt² ({(area*0.0001384):.2f} in² @ default DPI)")
            return
        elif self.tool == Tool.TEXT_SELECT:
            # copy selected text to clipboard
            try:
                text = self.doc.doc[page_idx].get_textbox(fitz.Rect(*rect))
                if text and text.strip():
                    QApplication.clipboard().setText(text.strip())
                    self.status.emit(f"Copied {len(text)} chars to clipboard")
            except Exception:
                pass
            return
        self.refresh_page(page_idx)
        self.document_modified.emit()

    def _commit_oval_tool(self, page_idx: int, rect: tuple):
        c = self.draw_color
        self.doc.add_oval(page_idx, rect, color=(c.redF(), c.greenF(), c.blueF()),
                          width=self.draw_width)
        self.refresh_page(page_idx); self.document_modified.emit()

    def _commit_line_tool(self, page_idx: int, p1: tuple, p2: tuple):
        if self.tool == Tool.MEASURE_DIST:
            dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
            d_pt = math.hypot(dx, dy)
            d_in = d_pt / 72
            d_cm = d_in * 2.54
            self.status.emit(f"Distance: {d_pt:.1f} pt | {d_in:.2f} in | {d_cm:.2f} cm")
            return
        c = self.draw_color
        if self.tool == Tool.LINE:
            self.doc.add_line(page_idx, p1, p2, color=(c.redF(), c.greenF(), c.blueF()),
                              width=self.draw_width)
        else:
            self.doc.add_arrow(page_idx, p1, p2, color=(c.redF(), c.greenF(), c.blueF()),
                               width=self.draw_width)
        self.refresh_page(page_idx); self.document_modified.emit()

    def _rect_to_quad(self, rect: tuple) -> fitz.Quad:
        x0, y0, x1, y1 = rect
        return fitz.Quad((fitz.Point(x0, y0), fitz.Point(x1, y0),
                          fitz.Point(x0, y1), fitz.Point(x1, y1)))

    # ---------------- line tools ----------------
    def _begin_line(self, sp: QPointF):
        self._preview = QGraphicsLineItem(sp.x(), sp.y(), sp.x(), sp.y())
        pen = QPen(self._preview_color(), self.draw_width * self.zoom, Qt.SolidLine, Qt.RoundCap)
        self._preview.setPen(pen)
        self.scene().addItem(self._preview)

    # ---------------- polygon ----------------
    def _poly_add_point(self, pv: PageView, sp: QPointF, double_click: bool):
        if self._polygon_page is None or self._polygon_page != pv.index:
            self._cancel_polygon()
            self._polygon_page = pv.index
        self._polygon_points.append(sp)
        # redraw preview
        if self._preview:
            self.scene().removeItem(self._preview)
        poly = QPolygonF(self._polygon_points)
        self._preview = QGraphicsPolygonItem(poly)
        self._preview.setPen(QPen(self._preview_color(), 1.5, Qt.DashLine))
        fill = QColor(self._preview_color()); fill.setAlpha(40)
        self._preview.setBrush(QBrush(fill))
        self.scene().addItem(self._preview)
        if double_click or len(self._polygon_points) > 50:
            self._finish_polygon()

    def _finish_polygon(self):
        if not self._polygon_points or self._polygon_page is None:
            self._cancel_polygon(); return
        pv = self.pages[self._find_page_view_index(self._polygon_page)]
        pdf_pts = [self._scene_to_pdf(pv, p) for p in self._polygon_points]
        c = self.draw_color
        try:
            self.doc.add_polygon(pv.index, pdf_pts,
                                 color=(c.redF(), c.greenF(), c.blueF()),
                                 width=self.draw_width)
            self.refresh_page(pv.index)
            self.document_modified.emit()
        finally:
            self._cancel_polygon()

    def _cancel_polygon(self):
        if self._preview and isinstance(self._preview, QGraphicsPolygonItem):
            if self._preview.scene():
                self.scene().removeItem(self._preview)
            self._preview = None
        self._polygon_points = []
        self._polygon_page = None

    def keyPressEvent(self, e: QKeyEvent):
        if self.tool == Tool.POLYGON and e.key() == Qt.Key_Return:
            self._finish_polygon(); return
        if e.key() == Qt.Key_Escape:
            self._cancel_polygon()
            self._cancel_edit()
        if e.key() == Qt.Key_PageDown: self.goto_page(self.current_page_index() + 1)
        elif e.key() == Qt.Key_PageUp: self.goto_page(self.current_page_index() - 1)
        elif e.key() == Qt.Key_Home: self.goto_page(0)
        elif e.key() == Qt.Key_End and self.doc:
            self.goto_page(self.doc.page_count - 1)
        else:
            super().keyPressEvent(e)

    # ---------------- text editing ----------------
    def _begin_insert_text(self, pv: PageView, sp: QPointF):
        """Open an inline editor at the click point. No dialog."""
        self._cancel_edit()
        from .text_editor import InlineTextCreator
        creator = InlineTextCreator(sp, fontsize=self.text_size,
                                    color=self.draw_color, zoom=self.zoom)
        proxy = self.scene().addWidget(creator)
        proxy.setPos(sp.x(), sp.y() - creator.height() / 4)
        proxy.setZValue(100)
        creator.setFocus(Qt.OtherFocusReason)
        creator.commit_text.connect(
            lambda pos, text, fs, p=pv: self._commit_inline_text(p, pos, text, fs))
        creator.cancelled.connect(self._cancel_edit)
        self._edit_proxy = proxy

    def _commit_inline_text(self, pv: PageView, scene_pos: QPointF,
                            text: str, fontsize: float):
        x, y = self._scene_to_pdf(pv, scene_pos)
        c = self.draw_color
        try:
            # offset so the click point is the top of the text, not the baseline
            self.doc.add_text(pv.index, x, y + fontsize, text,
                              fontsize=int(fontsize),
                              color=(c.redF(), c.greenF(), c.blueF()))
            self.refresh_page(pv.index)
            self.document_modified.emit()
        finally:
            self._cancel_edit()

    def _begin_edit_text(self, pv: PageView, sp: QPointF):
        x, y = self._scene_to_pdf(pv, sp)
        span = self.doc.hit_test_text(pv.index, x, y)
        if not span:
            self.status.emit("No text under cursor — try clicking on a word")
            return
        self._show_inline_editor(pv, span)

    def _show_inline_editor(self, pv: PageView, span: TextSpan):
        self._cancel_edit()
        from .text_editor import InlineTextEditor
        scene_rect = QRectF(self._pdf_to_scene(pv, span.bbox[0], span.bbox[1]),
                            self._pdf_to_scene(pv, span.bbox[2], span.bbox[3]))
        editor = InlineTextEditor(span, scene_rect, zoom=self.zoom)
        proxy = self.scene().addWidget(editor)
        proxy.setPos(scene_rect.topLeft())
        proxy.setZValue(100)
        editor.setFocus(Qt.OtherFocusReason)
        editor.commit_text.connect(self._commit_edit)
        editor.cancelled.connect(self._cancel_edit)
        self._edit_proxy = proxy

    def _commit_edit(self, span: TextSpan, new_text: str):
        try:
            if new_text != span.text:
                self.doc.replace_span(span, new_text)
                self.refresh_page(span.page)
                self.document_modified.emit()
        finally:
            self._cancel_edit()

    def _cancel_edit(self):
        if self._edit_proxy is not None:
            try:
                self.scene().removeItem(self._edit_proxy)
            except Exception:
                pass
            self._edit_proxy = None

    def _update_hover_outline(self, sp: QPointF):
        """When hovering with EDIT_TEXT/SELECT, draw a soft outline over text under cursor."""
        pv = self._page_at_scene(sp)
        if not pv or not self.doc:
            self._clear_hover_outline(); return
        x, y = self._scene_to_pdf(pv, sp)
        span = self.doc.hit_test_text(pv.index, x, y)
        if not span:
            self._clear_hover_outline(); return
        # convert span bbox back to scene rect
        tl = self._pdf_to_scene(pv, span.bbox[0], span.bbox[1])
        br = self._pdf_to_scene(pv, span.bbox[2], span.bbox[3])
        rect = QRectF(tl, br).normalized()
        if self._hover_outline is None:
            self._hover_outline = QGraphicsRectItem(rect)
            pen = QPen(QColor("#e63946"), 1.5, Qt.DashLine)
            self._hover_outline.setPen(pen)
            fill = QColor(230, 57, 70); fill.setAlpha(28)
            self._hover_outline.setBrush(QBrush(fill))
            self._hover_outline.setZValue(50)
            self.scene().addItem(self._hover_outline)
        else:
            self._hover_outline.setRect(rect)
            if not self._hover_outline.scene():
                self.scene().addItem(self._hover_outline)

    def _clear_hover_outline(self):
        if self._hover_outline is not None and self._hover_outline.scene():
            try:
                self.scene().removeItem(self._hover_outline)
            except Exception:
                pass
        self._hover_outline = None

    def _add_note(self, pv: PageView, sp: QPointF):
        text, ok = QInputDialog.getMultiLineText(self, "Sticky Note", "Note:")
        if not ok or not text: return
        x, y = self._scene_to_pdf(pv, sp)
        self.doc.add_sticky_note(pv.index, (x, y), text)
        self.refresh_page(pv.index); self.document_modified.emit()

    def _begin_callout(self, pv: PageView, sp: QPointF):
        text, ok = QInputDialog.getMultiLineText(self, "Callout / free text", "Text:")
        if not ok or not text: return
        x, y = self._scene_to_pdf(pv, sp)
        rect = (x, y, x + 180, y + 60)
        self.doc.add_callout(pv.index, rect, (x, y), text, fontsize=self.text_size,
                             color=(self.draw_color.redF(), self.draw_color.greenF(),
                                    self.draw_color.blueF()))
        self.refresh_page(pv.index); self.document_modified.emit()

    # ---------------- redact mark overlay management ----------------
    def clear_redact_marks(self):
        for m in self._redact_marks:
            if m.scene(): self.scene().removeItem(m)
        self._redact_marks.clear()
        if self.doc: self.doc.clear_pending_redactions()

    def apply_redact_marks(self) -> int:
        if not self.doc: return 0
        n = self.doc.apply_pending_redactions()
        for m in self._redact_marks:
            if m.scene(): self.scene().removeItem(m)
        self._redact_marks.clear()
        self.reload_all()
        if n: self.document_modified.emit()
        return n

    # ---------------- context menu ----------------
    def _context_menu(self, pos):
        sp = self.mapToScene(pos)
        pv = self._page_at_scene(sp)
        menu = QMenu(self)
        if pv:
            a_copy_text = menu.addAction("Copy page text")
            a_export_page = menu.addAction("Export this page as image...")
            menu.addSeparator()
            a_rot_l = menu.addAction("Rotate page left 90")
            a_rot_r = menu.addAction("Rotate page right 90")
            menu.addSeparator()
            a_delete = menu.addAction("Delete this page")
            a_dup = menu.addAction("Duplicate page")
            chosen = menu.exec(self.mapToGlobal(pos))
            if chosen == a_copy_text:
                QApplication.clipboard().setText(self.doc.get_text(pv.index))
                self.status.emit("Page text copied")
            elif chosen == a_export_page:
                from PySide6.QtWidgets import QFileDialog
                from pathlib import Path
                src_path = self.doc.path or "page"
                out, _ = QFileDialog.getSaveFileName(self, "Save page image",
                                                    f"{Path(src_path).stem}_page{pv.index+1}.png",
                                                    "PNG (*.png);;JPEG (*.jpg)")
                if out:
                    img = self.doc.render_pil(pv.index, zoom=2.0)
                    img.save(out)
                    self.status.emit(f"Saved {out}")
            elif chosen == a_rot_l:
                self.doc.rotate_page(pv.index, -90); self.reload_all(); self.document_modified.emit()
            elif chosen == a_rot_r:
                self.doc.rotate_page(pv.index, 90); self.reload_all(); self.document_modified.emit()
            elif chosen == a_delete and self.doc.page_count > 1:
                self.doc.delete_pages([pv.index])
                self.set_document(self.doc)
                self.document_modified.emit()
            elif chosen == a_dup:
                self.doc.duplicate_page(pv.index)
                self.set_document(self.doc)
                self.document_modified.emit()
