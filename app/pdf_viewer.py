"""PDF viewer widget with editing-tool overlays.

Uses QGraphicsView so pages flow vertically. Each page renders to a pixmap
item; edit tools draw temporary previews and commit operations to the
PdfDocument, which then triggers a re-render of the affected page.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PySide6.QtCore import (
    QPointF, QRectF, Qt, Signal, QEvent
)
from PySide6.QtGui import (
    QBrush, QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap,
    QPolygonF, QWheelEvent, QCursor, QFont
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsView, QInputDialog, QGraphicsTextItem, QGraphicsPolygonItem,
    QGraphicsPathItem, QApplication
)
from PySide6.QtGui import QPainterPath

import fitz

from .pdf_engine import PdfDocument


class Tool(Enum):
    SELECT = "select"
    HAND = "hand"
    TEXT = "text"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    DRAW = "draw"
    RECT = "rect"
    REDACT = "redact"
    ERASER = "eraser"
    IMAGE = "image"
    SIGNATURE = "signature"
    NOTE = "note"


@dataclass
class PageView:
    index: int
    item: QGraphicsPixmapItem
    rect_in_scene: QRectF
    page_w: float  # PDF points
    page_h: float


class PdfGraphicsView(QGraphicsView):
    page_changed = Signal(int)         # current page (1-based)
    zoom_changed = Signal(float)       # 1.0 = 100%
    selection_changed = Signal(object) # tuple(page_idx, rect_in_pdf) | None
    status = Signal(str)
    document_modified = Signal()

    PAGE_GAP = 18
    BG_COLOR = QColor("#3c3c3c")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setBackgroundBrush(QBrush(self.BG_COLOR))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.verticalScrollBar().valueChanged.connect(self._emit_current_page)

        self.doc: Optional[PdfDocument] = None
        self.pages: list[PageView] = []
        self.zoom: float = 1.25
        self.tool: Tool = Tool.SELECT
        self.draw_color: QColor = QColor("#000000")
        self.highlight_color: QColor = QColor(255, 235, 59)
        self.text_size: int = 12
        self.draw_width: float = 1.5

        # interaction state
        self._press_pos: Optional[QPointF] = None
        self._press_page: Optional[int] = None
        self._preview: Optional[QGraphicsItem] = None
        self._draw_points: list[QPointF] = []  # scene coords
        self._draw_path: Optional[QPainterPath] = None
        self._panning = False
        self._pan_last: Optional[QPointF] = None
        self._signature_pixmap: Optional[QPixmap] = None
        self._image_path: Optional[str] = None

    # ---------- document ----------
    def set_document(self, doc: Optional[PdfDocument]):
        self.doc = doc
        self.scene().clear()
        self.pages.clear()
        if not doc:
            return
        self._layout_pages()
        self._render_visible()
        self.page_changed.emit(1)

    def reload_all(self):
        if not self.doc:
            return
        self.scene().clear()
        self.pages.clear()
        self._layout_pages()
        self._render_visible()

    def _layout_pages(self):
        y = 0.0
        max_w = 0.0
        for i in range(self.doc.page_count):
            info = self.doc.page_info(i)
            w = info.width * self.zoom
            h = info.height * self.zoom
            item = QGraphicsPixmapItem()
            # bg sheet
            bg = QGraphicsRectItem(0, 0, w, h)
            bg.setBrush(QBrush(Qt.white))
            bg.setPen(QPen(QColor("#888"), 0.5))
            bg.setZValue(-1)
            x = 0
            bg.setPos(x, y)
            item.setPos(x, y)
            item.setZValue(0)
            self.scene().addItem(bg)
            self.scene().addItem(item)
            rect = QRectF(x, y, w, h)
            self.pages.append(PageView(i, item, rect, info.width, info.height))
            y += h + self.PAGE_GAP
            max_w = max(max_w, w)
        self.scene().setSceneRect(QRectF(-50, -20, max_w + 100, y + 40))

    def _render_visible(self):
        if not self.doc:
            return
        vr = self.mapToScene(self.viewport().rect()).boundingRect()
        for pv in self.pages:
            if pv.rect_in_scene.intersects(vr):
                if pv.item.pixmap().isNull():
                    data = self.doc.render(pv.index, zoom=self.zoom * 1.5)  # supersample for crisp
                    img = QImage.fromData(data)
                    pix = QPixmap.fromImage(img.scaled(
                        int(pv.rect_in_scene.width()),
                        int(pv.rect_in_scene.height()),
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    ))
                    pv.item.setPixmap(pix)
            else:
                if not pv.item.pixmap().isNull() and abs(pv.rect_in_scene.top() - vr.top()) > 3000:
                    pv.item.setPixmap(QPixmap())  # free far-away pages

    def refresh_page(self, page_index: int):
        if not self.doc:
            return
        for pv in self.pages:
            if pv.index == page_index:
                data = self.doc.render(pv.index, zoom=self.zoom * 1.5)
                img = QImage.fromData(data)
                pix = QPixmap.fromImage(img.scaled(
                    int(pv.rect_in_scene.width()),
                    int(pv.rect_in_scene.height()),
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation,
                ))
                pv.item.setPixmap(pix)
                return

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._render_visible()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._render_visible()

    # ---------- zoom ----------
    def set_zoom(self, zoom: float):
        self.zoom = max(0.25, min(zoom, 5.0))
        # remember current page
        cur = self.current_page_index()
        self.scene().clear()
        self.pages.clear()
        if self.doc:
            self._layout_pages()
            self._render_visible()
            self.goto_page(cur)
        self.zoom_changed.emit(self.zoom)

    def zoom_in(self):
        self.set_zoom(self.zoom * 1.2)

    def zoom_out(self):
        self.set_zoom(self.zoom / 1.2)

    def fit_width(self):
        if not self.pages:
            return
        vw = self.viewport().width() - 60
        page = self.pages[self.current_page_index()]
        new_zoom = vw / page.page_w
        self.set_zoom(new_zoom)

    def fit_page(self):
        if not self.pages:
            return
        vw = self.viewport().width() - 60
        vh = self.viewport().height() - 60
        page = self.pages[self.current_page_index()]
        new_zoom = min(vw / page.page_w, vh / page.page_h)
        self.set_zoom(new_zoom)

    # ---------- nav ----------
    def goto_page(self, index: int):
        if 0 <= index < len(self.pages):
            self.centerOn(self.pages[index].rect_in_scene.center())
            self.page_changed.emit(index + 1)

    def current_page_index(self) -> int:
        if not self.pages:
            return 0
        center_y = self.mapToScene(self.viewport().rect().center()).y()
        best = 0
        for pv in self.pages:
            if pv.rect_in_scene.top() <= center_y <= pv.rect_in_scene.bottom():
                return pv.index
            if pv.rect_in_scene.top() < center_y:
                best = pv.index
        return best

    def _emit_current_page(self, *_):
        self.page_changed.emit(self.current_page_index() + 1)
        self._render_visible()

    # ---------- coord conversion ----------
    def _page_at_scene(self, sp: QPointF) -> Optional[PageView]:
        for pv in self.pages:
            if pv.rect_in_scene.contains(sp):
                return pv
        return None

    def _scene_to_pdf(self, pv: PageView, sp: QPointF) -> tuple[float, float]:
        local_x = sp.x() - pv.rect_in_scene.left()
        local_y = sp.y() - pv.rect_in_scene.top()
        # account for page rotation
        info = self.doc.page_info(pv.index)
        rot = info.rotation
        scale_x = pv.page_w / pv.rect_in_scene.width()
        scale_y = pv.page_h / pv.rect_in_scene.height()
        px = local_x * scale_x
        py = local_y * scale_y
        # rotation handling for click->pdf coords
        if rot == 0:
            return px, py
        if rot == 90:
            return py, pv.page_w - px
        if rot == 180:
            return pv.page_w - px, pv.page_h - py
        if rot == 270:
            return pv.page_h - py, px
        return px, py

    # ---------- tools ----------
    def set_tool(self, tool: Tool):
        self.tool = tool
        cursors = {
            Tool.SELECT: Qt.ArrowCursor,
            Tool.HAND: Qt.OpenHandCursor,
            Tool.TEXT: Qt.IBeamCursor,
            Tool.HIGHLIGHT: Qt.CrossCursor,
            Tool.UNDERLINE: Qt.CrossCursor,
            Tool.STRIKEOUT: Qt.CrossCursor,
            Tool.DRAW: Qt.CrossCursor,
            Tool.RECT: Qt.CrossCursor,
            Tool.REDACT: Qt.CrossCursor,
            Tool.ERASER: Qt.CrossCursor,
            Tool.IMAGE: Qt.CrossCursor,
            Tool.SIGNATURE: Qt.CrossCursor,
            Tool.NOTE: Qt.CrossCursor,
        }
        self.setCursor(cursors.get(tool, Qt.ArrowCursor))

    def set_signature(self, pixmap: QPixmap):
        self._signature_pixmap = pixmap
        self.set_tool(Tool.SIGNATURE)

    def set_image_to_place(self, path: str):
        self._image_path = path
        self.set_tool(Tool.IMAGE)

    # ---------- events ----------
    def wheelEvent(self, e: QWheelEvent):
        if e.modifiers() & Qt.ControlModifier:
            if e.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            e.accept()
        else:
            super().wheelEvent(e)
            self._render_visible()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MiddleButton or (self.tool == Tool.HAND and e.button() == Qt.LeftButton):
            self._panning = True
            self._pan_last = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            return
        sp = self.mapToScene(e.position().toPoint())
        pv = self._page_at_scene(sp)
        if not pv or e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        self._press_pos = sp
        self._press_page = pv.index
        if self.tool == Tool.TEXT:
            self._begin_text(pv, sp)
            return
        if self.tool == Tool.NOTE:
            self._add_note(pv, sp)
            return
        if self.tool == Tool.DRAW:
            self._draw_points = [sp]
            self._draw_path = QPainterPath(sp)
            self._preview = QGraphicsPathItem(self._draw_path)
            pen = QPen(self.draw_color, self.draw_width * self.zoom)
            pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
            self._preview.setPen(pen)
            self.scene().addItem(self._preview)
            return
        if self.tool in (Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT,
                         Tool.RECT, Tool.REDACT, Tool.ERASER, Tool.IMAGE, Tool.SIGNATURE):
            self._preview = QGraphicsRectItem()
            color = self._preview_color()
            self._preview.setPen(QPen(color.darker(120), 1.5, Qt.DashLine))
            fill = QColor(color); fill.setAlpha(60)
            self._preview.setBrush(QBrush(fill))
            self.scene().addItem(self._preview)
            return

    def _preview_color(self) -> QColor:
        if self.tool == Tool.HIGHLIGHT:
            return self.highlight_color
        if self.tool == Tool.UNDERLINE:
            return QColor(0, 100, 255)
        if self.tool == Tool.STRIKEOUT:
            return QColor(220, 50, 50)
        if self.tool == Tool.REDACT:
            return QColor(0, 0, 0)
        if self.tool == Tool.RECT:
            return self.draw_color
        if self.tool == Tool.ERASER:
            return QColor(255, 100, 100)
        return QColor(0, 200, 100)

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._panning and self._pan_last is not None:
            d = e.position() - self._pan_last
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            self._pan_last = e.position()
            return
        sp = self.mapToScene(e.position().toPoint())
        if self._preview and self._press_pos is not None and isinstance(self._preview, QGraphicsRectItem):
            r = QRectF(self._press_pos, sp).normalized()
            self._preview.setRect(r)
        elif self.tool == Tool.DRAW and self._draw_path is not None:
            self._draw_path.lineTo(sp)
            self._preview.setPath(self._draw_path)
            self._draw_points.append(sp)
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self._panning:
            self._panning = False
            self._pan_last = None
            self.setCursor(Qt.OpenHandCursor if self.tool == Tool.HAND else Qt.ArrowCursor)
            return
        if e.button() != Qt.LeftButton or self._press_page is None:
            return super().mouseReleaseEvent(e)
        sp = self.mapToScene(e.position().toPoint())
        pv = self.pages[self._press_page]

        try:
            if self.tool == Tool.DRAW and self._draw_points and len(self._draw_points) > 1:
                pdf_points = [self._scene_to_pdf(pv, p) for p in self._draw_points]
                c = self.draw_color
                color = (c.redF(), c.greenF(), c.blueF())
                self.doc.add_freehand(pv.index, [fitz.Point(*pt) for pt in pdf_points],
                                      color=color, width=self.draw_width)
                self.refresh_page(pv.index)
                self.document_modified.emit()
            elif isinstance(self._preview, QGraphicsRectItem):
                r = self._preview.rect()
                if r.width() > 2 and r.height() > 2:
                    x0, y0 = self._scene_to_pdf(pv, r.topLeft())
                    x1, y1 = self._scene_to_pdf(pv, r.bottomRight())
                    rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                    self._commit_rect_tool(pv.index, rect)
        finally:
            if self._preview:
                self.scene().removeItem(self._preview)
                self._preview = None
            self._draw_points = []
            self._draw_path = None
            self._press_pos = None
            self._press_page = None

    def _commit_rect_tool(self, page_idx: int, rect: tuple):
        if self.tool == Tool.HIGHLIGHT:
            q = fitz.Quad((fitz.Point(rect[0], rect[1]),
                           fitz.Point(rect[2], rect[1]),
                           fitz.Point(rect[0], rect[3]),
                           fitz.Point(rect[2], rect[3])))
            self.doc.add_highlight(page_idx, [q])
        elif self.tool == Tool.UNDERLINE:
            q = fitz.Quad((fitz.Point(rect[0], rect[1]),
                           fitz.Point(rect[2], rect[1]),
                           fitz.Point(rect[0], rect[3]),
                           fitz.Point(rect[2], rect[3])))
            self.doc.add_underline(page_idx, [q])
        elif self.tool == Tool.STRIKEOUT:
            q = fitz.Quad((fitz.Point(rect[0], rect[1]),
                           fitz.Point(rect[2], rect[1]),
                           fitz.Point(rect[0], rect[3]),
                           fitz.Point(rect[2], rect[3])))
            self.doc.add_strikeout(page_idx, [q])
        elif self.tool == Tool.RECT:
            c = self.draw_color
            self.doc.add_rect(page_idx, rect, color=(c.redF(), c.greenF(), c.blueF()),
                              width=self.draw_width)
        elif self.tool == Tool.REDACT:
            self.doc.redact(page_idx, rect)
        elif self.tool == Tool.IMAGE and self._image_path:
            self.doc.add_image(page_idx, rect, self._image_path)
        elif self.tool == Tool.SIGNATURE and self._signature_pixmap:
            from io import BytesIO
            buf = BytesIO()
            self._signature_pixmap.save(buf, "PNG")
            self.doc.add_image_bytes(page_idx, rect, buf.getvalue())
        self.refresh_page(page_idx)
        self.document_modified.emit()

    def _begin_text(self, pv: PageView, sp: QPointF):
        text, ok = QInputDialog.getMultiLineText(self, "Insert Text", "Text:")
        if not ok or not text:
            return
        x, y = self._scene_to_pdf(pv, sp)
        c = self.draw_color
        # baseline-y so add some offset for fontsize
        self.doc.add_text(pv.index, x, y + self.text_size, text,
                          fontsize=self.text_size,
                          color=(c.redF(), c.greenF(), c.blueF()))
        self.refresh_page(pv.index)
        self.document_modified.emit()

    def _add_note(self, pv: PageView, sp: QPointF):
        text, ok = QInputDialog.getMultiLineText(self, "Sticky Note", "Note:")
        if not ok or not text:
            return
        x, y = self._scene_to_pdf(pv, sp)
        page = self.doc.doc[pv.index]
        self.doc.snapshot()
        annot = page.add_text_annot(fitz.Point(x, y), text)
        annot.update()
        self.refresh_page(pv.index)
        self.document_modified.emit()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key_PageDown:
            self.goto_page(self.current_page_index() + 1)
        elif e.key() == Qt.Key_PageUp:
            self.goto_page(self.current_page_index() - 1)
        elif e.key() == Qt.Key_Home:
            self.goto_page(0)
        elif e.key() == Qt.Key_End:
            self.goto_page(len(self.pages) - 1)
        else:
            super().keyPressEvent(e)
