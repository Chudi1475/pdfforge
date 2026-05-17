"""Inline text editing/creation widgets used by the canvas."""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import QLineEdit

from .pdf_engine import TextSpan


class InlineTextEditor(QLineEdit):
    """Edits an existing text span. Enter commits, Esc cancels."""
    commit_text = Signal(object, str)  # span, new_text
    cancelled = Signal()

    def __init__(self, span: TextSpan, scene_rect: QRectF,
                 zoom: float = 1.0, parent=None):
        super().__init__(parent)
        self.span = span
        self._committed = False
        self.setText(span.text)
        self.setStyleSheet(
            "QLineEdit{background:#fffacd;border:1.5px solid #e63946;"
            "padding:1px 3px;color:#000;}"
        )
        font_size_px = max(8, int(span.fontsize * zoom))
        f = self.font()
        f.setPixelSize(font_size_px)
        fn = (span.fontname or "").lower()
        if "courier" in fn or "mono" in fn: f.setFamily("Consolas")
        elif "times" in fn or "serif" in fn: f.setFamily("Times New Roman")
        else: f.setFamily("Arial")
        f.setBold(bool(span.flags & 16))
        f.setItalic(bool(span.flags & 2))
        self.setFont(f)
        self.setFixedWidth(int(scene_rect.width() + 80))
        self.setFixedHeight(int(max(font_size_px * 1.4, scene_rect.height() + 4)))
        self.selectAll()

    def _commit(self):
        if self._committed: return
        self._committed = True
        self.commit_text.emit(self.span, self.text())

    def _cancel(self):
        if self._committed: return
        self._committed = True
        self.cancelled.emit()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._commit(); return
        if e.key() == Qt.Key_Escape:
            self._cancel(); return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        self._commit()
        super().focusOutEvent(e)


class InlineTextCreator(QLineEdit):
    """Creates new text at a clicked location. Enter commits, Esc cancels."""
    commit_text = Signal(object, str, float)  # scene_pos (QPointF), text, fontsize
    cancelled = Signal()

    def __init__(self, scene_pos: QPointF, fontsize: int = 14,
                 color: Optional[QColor] = None, zoom: float = 1.0, parent=None):
        super().__init__(parent)
        self.scene_pos = scene_pos
        self.fontsize = fontsize
        self._committed = False
        c = color or QColor("#000000")
        font_px = max(10, int(fontsize * zoom))
        # color text the same color it will print
        self.setStyleSheet(
            f"QLineEdit{{background: rgba(255, 250, 205, 220); "
            f"border:1.5px solid #e63946; padding:2px 6px;"
            f"color:{c.name()};}}"
        )
        f = self.font(); f.setPixelSize(font_px); f.setFamily("Arial"); self.setFont(f)
        self.setPlaceholderText("Type, Enter to place, Esc to cancel")
        # generous default width so users can see what they're typing
        self.setFixedWidth(max(220, int(font_px * 14)))
        self.setFixedHeight(int(font_px * 1.5 + 8))

    def _commit(self):
        if self._committed: return
        self._committed = True
        text = self.text().strip()
        if text:
            self.commit_text.emit(self.scene_pos, text, float(self.fontsize))
        else:
            self.cancelled.emit()

    def _cancel(self):
        if self._committed: return
        self._committed = True
        self.cancelled.emit()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._commit(); return
        if e.key() == Qt.Key_Escape:
            self._cancel(); return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        self._commit()
        super().focusOutEvent(e)
