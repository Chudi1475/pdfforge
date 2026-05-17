"""Inline text editor overlay used when the EDIT_TEXT tool is active."""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QKeyEvent
from PySide6.QtWidgets import QLineEdit, QTextEdit, QGraphicsProxyWidget

from .pdf_engine import PdfDocument, TextSpan


class InlineTextEditor(QLineEdit):
    """A line edit positioned over a text span. Press Enter to commit, Esc to cancel."""
    commit_text = Signal(object, str)  # span, new_text
    cancelled = Signal()

    def __init__(self, span: TextSpan, scene_rect: QRectF,
                 zoom: float = 1.0, parent=None):
        super().__init__(parent)
        self.span = span
        self.setText(span.text)
        self.setStyleSheet(
            "QLineEdit{background:#fffacd;border:1.5px solid #e63946;"
            "padding:1px 3px;color:#000;}"
        )
        font_size_px = max(8, int(span.fontsize * zoom))
        f = self.font()
        f.setPixelSize(font_size_px)
        # try to honor font family
        fn = (span.fontname or "").lower()
        if "courier" in fn or "mono" in fn: f.setFamily("Consolas")
        elif "times" in fn or "serif" in fn: f.setFamily("Times New Roman")
        else: f.setFamily("Arial")
        f.setBold(bool(span.flags & 16))
        f.setItalic(bool(span.flags & 2))
        self.setFont(f)
        # width: keep the original span width plus a generous margin
        self.setFixedWidth(int(scene_rect.width() + 80))
        self.setFixedHeight(int(max(font_size_px * 1.4, scene_rect.height() + 4)))
        self.selectAll()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            self.commit_text.emit(self.span, self.text())
            return
        if e.key() == Qt.Key_Escape:
            self.cancelled.emit()
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        # treat losing focus as commit
        self.commit_text.emit(self.span, self.text())
        super().focusOutEvent(e)
