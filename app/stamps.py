"""Built-in stamps - all rendered at runtime with QPainter, no asset files."""
from __future__ import annotations
from io import BytesIO

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QBrush, QPainterPath


# (name, accent color, label, sublabel)
BUILTIN_STAMPS = [
    ("Approved",      "#2e7d32", "APPROVED",      None),
    ("Confidential",  "#c62828", "CONFIDENTIAL",  None),
    ("Draft",         "#1565c0", "DRAFT",         None),
    ("Final",         "#2e7d32", "FINAL",         None),
    ("Reviewed",      "#6a1b9a", "REVIEWED",      None),
    ("Rejected",      "#b71c1c", "REJECTED",      None),
    ("Void",          "#424242", "VOID",          None),
    ("Paid",          "#2e7d32", "PAID",          None),
    ("Received",      "#1565c0", "RECEIVED",      None),
    ("For Comment",   "#ef6c00", "FOR COMMENT",   None),
    ("Top Secret",    "#b71c1c", "TOP SECRET",    None),
    ("Sample",        "#6a1b9a", "SAMPLE",        None),
    ("Original",      "#2e7d32", "ORIGINAL",      None),
    ("Copy",          "#424242", "COPY",          None),
    ("Urgent",        "#ef6c00", "URGENT",        None),
    ("Not Approved",  "#b71c1c", "NOT APPROVED",  None),
]


def render_stamp(label: str, color: str = "#c62828",
                 width: int = 360, height: int = 110,
                 bordered: bool = True) -> QPixmap:
    """Render a transparent rectangular stamp."""
    pix = QPixmap(width, height)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    c = QColor(color)
    pen = QPen(c, 4)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if bordered:
        path = QPainterPath()
        path.addRoundedRect(QRectF(8, 8, width - 16, height - 16), 8, 8)
        p.drawPath(path)
        # inner border
        pen2 = QPen(c, 1.5)
        p.setPen(pen2)
        p.drawRoundedRect(QRectF(14, 14, width - 28, height - 28), 5, 5)
    f = QFont("Arial Black", int(height * 0.36))
    f.setBold(True)
    p.setFont(f)
    p.setPen(c)
    p.drawText(pix.rect(), Qt.AlignCenter, label)
    p.end()
    return pix


def render_round_stamp(label: str, color: str = "#1565c0",
                       sublabel: str = "", size: int = 220) -> QPixmap:
    """Circular stamp with inner ring and centered text."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    c = QColor(color)
    pen = QPen(c, 4); p.setPen(pen); p.setBrush(Qt.NoBrush)
    margin = 10
    p.drawEllipse(QRectF(margin, margin, size - 2*margin, size - 2*margin))
    p.setPen(QPen(c, 1.2))
    p.drawEllipse(QRectF(margin + 12, margin + 12, size - 2*(margin+12), size - 2*(margin+12)))
    f = QFont("Arial Black", int(size * 0.16)); f.setBold(True)
    p.setFont(f); p.setPen(c)
    p.drawText(pix.rect(), Qt.AlignCenter, label)
    p.end()
    return pix


def pixmap_to_png_bytes(pix: QPixmap) -> bytes:
    buf = BytesIO()
    pix.save(buf, "PNG")
    return buf.getvalue()
