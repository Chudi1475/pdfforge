"""Original icon factory - renders shapes with QPainter so we ship zero assets."""
from __future__ import annotations
from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QIcon, QFont, QBrush


_DEFAULT_FG = "#e8e8e8"


def _new(size: int = 22) -> QPixmap:
    p = QPixmap(size, size)
    p.fill(Qt.transparent)
    return p


def _painter(pix: QPixmap, color: str) -> QPainter:
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing | QPainter.TextAntialiasing)
    p.setPen(QPen(QColor(color), 1.6))
    p.setBrush(Qt.NoBrush)
    return p


def folder_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size)
    p = _painter(pix, color)
    s = size
    path = QPainterPath()
    path.moveTo(s*0.1, s*0.30)
    path.lineTo(s*0.42, s*0.30)
    path.lineTo(s*0.50, s*0.38)
    path.lineTo(s*0.90, s*0.38)
    path.lineTo(s*0.90, s*0.78)
    path.lineTo(s*0.10, s*0.78)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def save_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.16, s*0.16, s*0.68, s*0.68))
    p.fillRect(QRectF(s*0.28, s*0.16, s*0.44, s*0.20), QColor(color))
    p.drawRect(QRectF(s*0.28, s*0.52, s*0.44, s*0.30))
    p.end()
    return QIcon(pix)


def print_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.20, s*0.20, s*0.60, s*0.20))
    p.drawRect(QRectF(s*0.10, s*0.40, s*0.80, s*0.30))
    p.drawRect(QRectF(s*0.22, s*0.55, s*0.56, s*0.25))
    p.end()
    return QIcon(pix)


def undo_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawArc(QRectF(s*0.18, s*0.18, s*0.64, s*0.64), 30*16, 220*16)
    path = QPainterPath()
    path.moveTo(s*0.20, s*0.32); path.lineTo(s*0.20, s*0.50); path.lineTo(s*0.38, s*0.50)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def redo_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawArc(QRectF(s*0.18, s*0.18, s*0.64, s*0.64), 330*16, -220*16)
    path = QPainterPath()
    path.moveTo(s*0.80, s*0.32); path.lineTo(s*0.80, s*0.50); path.lineTo(s*0.62, s*0.50)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def zoom_in_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawEllipse(QRectF(s*0.16, s*0.16, s*0.50, s*0.50))
    p.drawLine(QPointF(s*0.60, s*0.60), QPointF(s*0.84, s*0.84))
    p.drawLine(QPointF(s*0.32, s*0.40), QPointF(s*0.50, s*0.40))
    p.drawLine(QPointF(s*0.41, s*0.31), QPointF(s*0.41, s*0.49))
    p.end()
    return QIcon(pix)


def zoom_out_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawEllipse(QRectF(s*0.16, s*0.16, s*0.50, s*0.50))
    p.drawLine(QPointF(s*0.60, s*0.60), QPointF(s*0.84, s*0.84))
    p.drawLine(QPointF(s*0.32, s*0.40), QPointF(s*0.50, s*0.40))
    p.end()
    return QIcon(pix)


def search_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawEllipse(QRectF(s*0.18, s*0.18, s*0.48, s*0.48))
    p.drawLine(QPointF(s*0.58, s*0.58), QPointF(s*0.82, s*0.82))
    p.end()
    return QIcon(pix)


def select_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    path = QPainterPath()
    path.moveTo(s*0.25, s*0.18); path.lineTo(s*0.25, s*0.70)
    path.lineTo(s*0.38, s*0.58); path.lineTo(s*0.48, s*0.82)
    path.lineTo(s*0.58, s*0.78); path.lineTo(s*0.48, s*0.54)
    path.lineTo(s*0.65, s*0.50); path.closeSubpath()
    p.setBrush(QBrush(QColor(color))); p.drawPath(path)
    p.end()
    return QIcon(pix)


def hand_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRoundedRect(QRectF(s*0.30, s*0.18, s*0.10, s*0.50), 3, 3)
    p.drawRoundedRect(QRectF(s*0.42, s*0.14, s*0.10, s*0.50), 3, 3)
    p.drawRoundedRect(QRectF(s*0.54, s*0.18, s*0.10, s*0.50), 3, 3)
    p.drawRoundedRect(QRectF(s*0.66, s*0.26, s*0.10, s*0.42), 3, 3)
    p.drawRoundedRect(QRectF(s*0.25, s*0.50, s*0.55, s*0.30), 6, 6)
    p.end()
    return QIcon(pix)


def text_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size)
    p = _painter(pix, color)
    f = QFont("Segoe UI", int(size * 0.62)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color))
    p.drawText(pix.rect(), Qt.AlignCenter, "T")
    p.end()
    return QIcon(pix)


def highlight_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.fillRect(QRectF(s*0.18, s*0.50, s*0.64, s*0.16), QColor("#ffd54f"))
    p.setPen(QPen(QColor(color), 1.6))
    p.drawLine(QPointF(s*0.20, s*0.66), QPointF(s*0.80, s*0.66))
    p.end()
    return QIcon(pix)


def underline_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    f = QFont("Segoe UI", int(size * 0.50)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color))
    p.drawText(QRectF(0, 0, s, s*0.82), Qt.AlignCenter, "U")
    p.drawLine(QPointF(s*0.28, s*0.82), QPointF(s*0.72, s*0.82))
    p.end()
    return QIcon(pix)


def strike_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    f = QFont("Segoe UI", int(size * 0.50)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color))
    p.drawText(pix.rect(), Qt.AlignCenter, "S")
    p.drawLine(QPointF(s*0.20, s*0.50), QPointF(s*0.80, s*0.50))
    p.end()
    return QIcon(pix)


def note_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    path = QPainterPath()
    path.addRoundedRect(QRectF(s*0.18, s*0.20, s*0.64, s*0.50), 6, 6)
    path.moveTo(s*0.30, s*0.70); path.lineTo(s*0.30, s*0.84); path.lineTo(s*0.46, s*0.70)
    p.drawPath(path)
    p.drawLine(QPointF(s*0.28, s*0.36), QPointF(s*0.72, s*0.36))
    p.drawLine(QPointF(s*0.28, s*0.48), QPointF(s*0.66, s*0.48))
    p.end()
    return QIcon(pix)


def draw_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    path = QPainterPath()
    path.moveTo(s*0.70, s*0.18); path.lineTo(s*0.82, s*0.30)
    path.lineTo(s*0.34, s*0.78); path.lineTo(s*0.18, s*0.82)
    path.lineTo(s*0.22, s*0.66); path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def rect_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.20, s*0.26, s*0.60, s*0.48))
    p.end()
    return QIcon(pix)


def image_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.16, s*0.20, s*0.68, s*0.60))
    p.drawEllipse(QRectF(s*0.28, s*0.30, s*0.14, s*0.14))
    path = QPainterPath()
    path.moveTo(s*0.20, s*0.74); path.lineTo(s*0.40, s*0.54)
    path.lineTo(s*0.58, s*0.70); path.lineTo(s*0.70, s*0.58); path.lineTo(s*0.80, s*0.74)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def sign_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawLine(QPointF(s*0.14, s*0.78), QPointF(s*0.86, s*0.78))
    pen = QPen(QColor(color), 1.8); p.setPen(pen)
    path = QPainterPath()
    path.moveTo(s*0.22, s*0.62)
    path.cubicTo(s*0.32, s*0.32, s*0.48, s*0.74, s*0.58, s*0.40)
    path.cubicTo(s*0.66, s*0.20, s*0.72, s*0.60, s*0.80, s*0.50)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def redact_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.fillRect(QRectF(s*0.16, s*0.36, s*0.68, s*0.12), QColor(color))
    p.fillRect(QRectF(s*0.16, s*0.56, s*0.50, s*0.12), QColor(color))
    p.end()
    return QIcon(pix)


def rotate_left_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawArc(QRectF(s*0.16, s*0.16, s*0.66, s*0.66), 90*16, 220*16)
    path = QPainterPath()
    path.moveTo(s*0.18, s*0.32); path.lineTo(s*0.18, s*0.50); path.lineTo(s*0.36, s*0.50)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def rotate_right_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawArc(QRectF(s*0.16, s*0.16, s*0.66, s*0.66), 90*16, -220*16)
    path = QPainterPath()
    path.moveTo(s*0.82, s*0.32); path.lineTo(s*0.82, s*0.50); path.lineTo(s*0.64, s*0.50)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def merge_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.12, s*0.16, s*0.30, s*0.42))
    p.drawRect(QRectF(s*0.58, s*0.16, s*0.30, s*0.42))
    p.drawRect(QRectF(s*0.30, s*0.62, s*0.40, s*0.24))
    p.drawLine(QPointF(s*0.27, s*0.58), QPointF(s*0.40, s*0.62))
    p.drawLine(QPointF(s*0.73, s*0.58), QPointF(s*0.60, s*0.62))
    p.end()
    return QIcon(pix)


def split_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.32, s*0.14, s*0.36, s*0.30))
    p.drawRect(QRectF(s*0.12, s*0.58, s*0.30, s*0.28))
    p.drawRect(QRectF(s*0.58, s*0.58, s*0.30, s*0.28))
    p.drawLine(QPointF(s*0.40, s*0.48), QPointF(s*0.27, s*0.56))
    p.drawLine(QPointF(s*0.60, s*0.48), QPointF(s*0.73, s*0.56))
    p.end()
    return QIcon(pix)


def compress_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.20, s*0.16, s*0.60, s*0.68))
    path = QPainterPath()
    path.moveTo(s*0.50, s*0.30); path.lineTo(s*0.50, s*0.46)
    path.moveTo(s*0.40, s*0.40); path.lineTo(s*0.50, s*0.46); path.lineTo(s*0.60, s*0.40)
    path.moveTo(s*0.50, s*0.70); path.lineTo(s*0.50, s*0.54)
    path.moveTo(s*0.40, s*0.60); path.lineTo(s*0.50, s*0.54); path.lineTo(s*0.60, s*0.60)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def lock_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawArc(QRectF(s*0.28, s*0.20, s*0.44, s*0.34), 0, 180*16)
    p.drawRect(QRectF(s*0.22, s*0.44, s*0.56, s*0.40))
    p.setBrush(QBrush(QColor(color)))
    p.drawEllipse(QRectF(s*0.45, s*0.58, s*0.10, s*0.10))
    p.end()
    return QIcon(pix)


def watermark_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.20, s*0.16, s*0.60, s*0.68))
    p.save()
    p.translate(s*0.50, s*0.50); p.rotate(-30)
    f = QFont("Segoe UI", int(size * 0.20)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color))
    p.drawText(QRectF(-s*0.4, -s*0.1, s*0.8, s*0.2), Qt.AlignCenter, "WM")
    p.restore()
    p.end()
    return QIcon(pix)


def export_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.20, s*0.30, s*0.60, s*0.54))
    path = QPainterPath()
    path.moveTo(s*0.50, s*0.16); path.lineTo(s*0.50, s*0.50)
    path.moveTo(s*0.36, s*0.30); path.lineTo(s*0.50, s*0.16); path.lineTo(s*0.64, s*0.30)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def ocr_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.16, s*0.16, s*0.68, s*0.68))
    f = QFont("Segoe UI", int(size * 0.34)); f.setBold(True)
    p.setFont(f); p.setPen(QColor(color))
    p.drawText(pix.rect(), Qt.AlignCenter, "A")
    p.end()
    return QIcon(pix)


def pages_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    p.drawRect(QRectF(s*0.18, s*0.14, s*0.40, s*0.52))
    p.drawRect(QRectF(s*0.40, s*0.34, s*0.40, s*0.52))
    p.end()
    return QIcon(pix)


def bookmark_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    path = QPainterPath()
    path.moveTo(s*0.28, s*0.14); path.lineTo(s*0.72, s*0.14)
    path.lineTo(s*0.72, s*0.82); path.lineTo(s*0.50, s*0.66)
    path.lineTo(s*0.28, s*0.82); path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def comment_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    path = QPainterPath()
    path.addRoundedRect(QRectF(s*0.14, s*0.18, s*0.72, s*0.52), 6, 6)
    p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(s*0.36, s*0.70); path2.lineTo(s*0.36, s*0.84); path2.lineTo(s*0.52, s*0.70)
    p.drawPath(path2)
    p.drawLine(QPointF(s*0.26, s*0.34), QPointF(s*0.74, s*0.34))
    p.drawLine(QPointF(s*0.26, s*0.46), QPointF(s*0.60, s*0.46))
    p.end()
    return QIcon(pix)


def attach_icon(color: str = _DEFAULT_FG, size: int = 22) -> QIcon:
    pix = _new(size); p = _painter(pix, color); s = size
    path = QPainterPath()
    path.moveTo(s*0.68, s*0.20); path.cubicTo(s*0.86, s*0.30, s*0.86, s*0.60, s*0.50, s*0.74)
    path.cubicTo(s*0.20, s*0.84, s*0.10, s*0.50, s*0.34, s*0.30)
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def app_logo(size: int = 32) -> QIcon:
    """Chudi PDF Pro logo - red shield with C monogram."""
    pix = _new(size); p = _painter(pix, "#e63946"); s = size
    p.setBrush(QBrush(QColor("#e63946")))
    p.setPen(Qt.NoPen)
    path = QPainterPath()
    path.moveTo(s*0.50, s*0.08)
    path.lineTo(s*0.86, s*0.20)
    path.lineTo(s*0.86, s*0.56)
    path.cubicTo(s*0.86, s*0.78, s*0.68, s*0.90, s*0.50, s*0.94)
    path.cubicTo(s*0.32, s*0.90, s*0.14, s*0.78, s*0.14, s*0.56)
    path.lineTo(s*0.14, s*0.20)
    path.closeSubpath()
    p.drawPath(path)
    f = QFont("Segoe UI", int(size * 0.42)); f.setBold(True)
    p.setFont(f); p.setPen(QColor("white"))
    p.drawText(QRectF(0, s*0.10, s, s*0.80), Qt.AlignCenter, "C")
    p.end()
    return QIcon(pix)
