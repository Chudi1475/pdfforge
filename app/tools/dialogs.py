"""Dialogs for batch operations: merge, split, encrypt, compress, OCR, signature pad."""
from __future__ import annotations
import os
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QPointF, QSize, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QImage, QFont, QPainterPath
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
    QLabel, QFileDialog, QMessageBox, QLineEdit, QFormLayout, QCheckBox,
    QSpinBox, QComboBox, QGroupBox, QRadioButton, QProgressBar, QWidget, QTabWidget,
    QPlainTextEdit, QColorDialog, QApplication, QGridLayout
)

from .. import pdf_engine as eng


# ----------------------------------------------------------------- merge
class MergeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge PDFs")
        self.resize(560, 460)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Add PDFs in the order they should appear in the merged file:"))
        self.list = QListWidget()
        self.list.setDragDropMode(QListWidget.InternalMove)
        v.addWidget(self.list, 1)
        h = QHBoxLayout()
        b_add = QPushButton("Add files...")
        b_rm = QPushButton("Remove"); b_rm.setObjectName("secondary")
        b_up = QPushButton("Up"); b_up.setObjectName("secondary")
        b_dn = QPushButton("Down"); b_dn.setObjectName("secondary")
        for b in (b_add, b_rm, b_up, b_dn):
            h.addWidget(b)
        h.addStretch()
        v.addLayout(h)
        b_add.clicked.connect(self._add)
        b_rm.clicked.connect(self._remove)
        b_up.clicked.connect(lambda: self._move(-1))
        b_dn.clicked.connect(lambda: self._move(+1))

        h2 = QHBoxLayout()
        h2.addStretch()
        b_cancel = QPushButton("Cancel"); b_cancel.setObjectName("secondary")
        b_ok = QPushButton("Merge")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self._merge)
        h2.addWidget(b_cancel); h2.addWidget(b_ok)
        v.addLayout(h2)

    def _add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", "", "PDF (*.pdf)")
        for f in files:
            self.list.addItem(QListWidgetItem(f))

    def _remove(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))

    def _move(self, delta: int):
        row = self.list.currentRow()
        if row < 0:
            return
        new = max(0, min(self.list.count() - 1, row + delta))
        if new == row:
            return
        it = self.list.takeItem(row)
        self.list.insertItem(new, it)
        self.list.setCurrentRow(new)

    def _merge(self):
        if self.list.count() < 2:
            QMessageBox.warning(self, "Merge", "Add at least 2 PDFs")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save merged PDF", "merged.pdf", "PDF (*.pdf)")
        if not out:
            return
        paths = [self.list.item(i).text() for i in range(self.list.count())]
        try:
            eng.merge_pdfs(paths, out)
            QMessageBox.information(self, "Merge", f"Saved to {out}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Merge failed", str(e))


# ----------------------------------------------------------------- split
class SplitDialog(QDialog):
    def __init__(self, source_path: str, page_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split PDF")
        self.source = source_path
        self.page_count = page_count
        self.resize(440, 280)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"Source: {os.path.basename(source_path)} ({page_count} pages)"))
        g = QGroupBox("Method")
        gl = QVBoxLayout(g)
        self.rb_single = QRadioButton("One PDF per page")
        self.rb_ranges = QRadioButton("Custom ranges (e.g. 1-3, 5, 7-10)")
        self.rb_single.setChecked(True)
        gl.addWidget(self.rb_single)
        gl.addWidget(self.rb_ranges)
        self.ranges_edit = QLineEdit()
        self.ranges_edit.setPlaceholderText("1-3, 5, 7-10")
        gl.addWidget(self.ranges_edit)
        v.addWidget(g)

        h = QHBoxLayout()
        h.addStretch()
        b_cancel = QPushButton("Cancel"); b_cancel.setObjectName("secondary")
        b_ok = QPushButton("Split")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self._split)
        h.addWidget(b_cancel); h.addWidget(b_ok)
        v.addLayout(h)

    def _parse_ranges(self, txt: str) -> list[tuple[int, int]]:
        out = []
        for part in txt.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = int(a.strip()) - 1, int(b.strip()) - 1
            else:
                a = b = int(part) - 1
            if a < 0 or b >= self.page_count or a > b:
                raise ValueError(f"Invalid range: {part}")
            out.append((a, b))
        return out

    def _split(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not out_dir:
            return
        try:
            if self.rb_single.isChecked():
                files = eng.split_pdf(self.source, out_dir, mode="single")
            else:
                ranges = self._parse_ranges(self.ranges_edit.text())
                if not ranges:
                    QMessageBox.warning(self, "Split", "Enter at least one range")
                    return
                files = eng.split_pdf(self.source, out_dir, mode="ranges", ranges=ranges)
            QMessageBox.information(self, "Split", f"Wrote {len(files)} file(s) to {out_dir}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Split failed", str(e))


# ----------------------------------------------------------------- encrypt
class EncryptDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Protect PDF")
        self.source = source_path
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.pw = QLineEdit(); self.pw.setEchoMode(QLineEdit.Password)
        self.pw2 = QLineEdit(); self.pw2.setEchoMode(QLineEdit.Password)
        self.owner = QLineEdit(); self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText("(optional, defaults to user password)")
        form.addRow("Password:", self.pw)
        form.addRow("Confirm:", self.pw2)
        form.addRow("Owner password:", self.owner)
        v.addLayout(form)
        g = QGroupBox("Permissions")
        gl = QVBoxLayout(g)
        self.cb_print = QCheckBox("Allow printing"); self.cb_print.setChecked(True)
        self.cb_copy = QCheckBox("Allow copying text"); self.cb_copy.setChecked(True)
        self.cb_modify = QCheckBox("Allow modifying"); self.cb_modify.setChecked(False)
        gl.addWidget(self.cb_print); gl.addWidget(self.cb_copy); gl.addWidget(self.cb_modify)
        v.addWidget(g)

        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Protect"); b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)

    def _go(self):
        if not self.pw.text():
            QMessageBox.warning(self, "Protect", "Password is required")
            return
        if self.pw.text() != self.pw2.text():
            QMessageBox.warning(self, "Protect", "Passwords do not match")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save protected PDF",
                                             f"{Path(self.source).stem}_protected.pdf", "PDF (*.pdf)")
        if not out:
            return
        try:
            eng.encrypt_pdf(self.source, out, user_pw=self.pw.text(),
                            owner_pw=self.owner.text() or self.pw.text(),
                            allow_print=self.cb_print.isChecked(),
                            allow_copy=self.cb_copy.isChecked(),
                            allow_modify=self.cb_modify.isChecked())
            QMessageBox.information(self, "Protect", f"Saved to {out}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Protect failed", str(e))


# ----------------------------------------------------------------- compress
class CompressDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compress PDF")
        self.source = source_path
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Re-saves with cleanup and downsamples large images."))
        form = QFormLayout()
        self.quality = QSpinBox(); self.quality.setRange(20, 95); self.quality.setValue(60)
        self.quality.setSuffix("%")
        form.addRow("JPEG quality:", self.quality)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Compress"); b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)

    def _go(self):
        out, _ = QFileDialog.getSaveFileName(self, "Save compressed PDF",
                                             f"{Path(self.source).stem}_compressed.pdf", "PDF (*.pdf)")
        if not out:
            return
        try:
            before = os.path.getsize(self.source)
            eng.compress_pdf(self.source, out, image_quality=self.quality.value())
            after = os.path.getsize(out)
            saved = (1 - after / before) * 100
            QMessageBox.information(self, "Compress",
                                    f"Saved {saved:.1f}% ({before/1024:.0f} KB -> {after/1024:.0f} KB)")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Compress failed", str(e))


# ----------------------------------------------------------------- OCR worker
class OcrWorker(QThread):
    progress = Signal(int, int)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, src: str, dst: str, tesseract_cmd: str, language: str):
        super().__init__()
        self.src, self.dst, self.tcmd, self.lang = src, dst, tesseract_cmd, language

    def run(self):
        try:
            ok = eng.ocr_pdf(self.src, self.dst, tesseract_cmd=self.tcmd,
                             language=self.lang, progress=lambda i, n: self.progress.emit(i, n))
            if ok:
                self.finished_ok.emit(self.dst)
            else:
                self.failed.emit("Could not run OCR — is Tesseract installed?")
        except Exception as e:
            self.failed.emit(str(e))


class OcrDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Make Searchable (OCR)")
        self.source = source_path
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Run OCR to make a scanned PDF searchable."))
        form = QFormLayout()
        self.tess = QLineEdit(eng.find_tesseract() or "")
        self.tess.setPlaceholderText(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        b_browse = QPushButton("..."); b_browse.clicked.connect(self._browse_tess)
        wt = QWidget(); ht = QHBoxLayout(wt); ht.setContentsMargins(0,0,0,0)
        ht.addWidget(self.tess, 1); ht.addWidget(b_browse)
        form.addRow("Tesseract:", wt)
        self.lang = QComboBox()
        self.lang.addItems(["eng", "spa", "fra", "deu", "ita", "por", "rus", "chi_sim", "jpn"])
        form.addRow("Language:", self.lang)
        v.addLayout(form)
        self.bar = QProgressBar()
        v.addWidget(self.bar)
        v.addWidget(QLabel(
            "Don't have Tesseract? Download from:\n"
            "https://github.com/UB-Mannheim/tesseract/wiki"))

        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        self.b_ok = QPushButton("Run OCR"); self.b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(self.b_ok)
        v.addLayout(h)
        self.worker = None

    def _browse_tess(self):
        p, _ = QFileDialog.getOpenFileName(self, "Find tesseract.exe", "", "tesseract.exe")
        if p:
            self.tess.setText(p)

    def _go(self):
        if not self.tess.text() or not os.path.isfile(self.tess.text()):
            QMessageBox.warning(self, "OCR", "Locate tesseract.exe first")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save searchable PDF",
                                             f"{Path(self.source).stem}_ocr.pdf", "PDF (*.pdf)")
        if not out:
            return
        self.b_ok.setEnabled(False)
        self.worker = OcrWorker(self.source, out, self.tess.text(), self.lang.currentText())
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.failed.connect(self._on_fail)
        self.worker.start()

    def _on_progress(self, i, n):
        self.bar.setMaximum(n); self.bar.setValue(i)

    def _on_done(self, path):
        QMessageBox.information(self, "OCR", f"Saved to {path}")
        self.accept()

    def _on_fail(self, msg):
        QMessageBox.critical(self, "OCR failed", msg)
        self.b_ok.setEnabled(True)


# ----------------------------------------------------------------- watermark
class WatermarkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Watermark")
        self.color = QColor(120, 120, 120)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.text = QLineEdit("DRAFT")
        form.addRow("Text:", self.text)
        self.size = QSpinBox(); self.size.setRange(8, 200); self.size.setValue(60)
        form.addRow("Font size:", self.size)
        self.opacity = QSpinBox(); self.opacity.setRange(5, 100); self.opacity.setValue(25); self.opacity.setSuffix("%")
        form.addRow("Opacity:", self.opacity)
        self.rotation = QSpinBox(); self.rotation.setRange(-180, 180); self.rotation.setValue(45)
        form.addRow("Rotation:", self.rotation)
        self.b_color = QPushButton("Choose color..."); self.b_color.setObjectName("secondary")
        self.b_color.clicked.connect(self._pick_color)
        form.addRow("Color:", self.b_color)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Apply"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)
        self._update_color_btn()

    def _pick_color(self):
        c = QColorDialog.getColor(self.color, self, "Watermark color")
        if c.isValid():
            self.color = c
            self._update_color_btn()

    def _update_color_btn(self):
        self.b_color.setStyleSheet(f"background:{self.color.name()};")

    def settings(self):
        c = self.color
        return dict(
            text=self.text.text(),
            fontsize=self.size.value(),
            opacity=self.opacity.value() / 100,
            rotation=self.rotation.value(),
            color=(c.redF(), c.greenF(), c.blueF()),
        )


# ----------------------------------------------------------------- page numbers
class PageNumbersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Page Numbers")
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.start = QSpinBox(); self.start.setRange(1, 9999); self.start.setValue(1)
        form.addRow("Start at:", self.start)
        self.size = QSpinBox(); self.size.setRange(6, 36); self.size.setValue(11)
        form.addRow("Font size:", self.size)
        self.position = QComboBox()
        self.position.addItems(["bottom-center", "bottom-right", "bottom-left",
                                "top-center", "top-right", "top-left"])
        form.addRow("Position:", self.position)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Apply"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)

    def settings(self):
        return dict(start=self.start.value(), fontsize=self.size.value(),
                    position=self.position.currentText())


# ----------------------------------------------------------------- redact text
class RedactTextDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Redact by Text")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Redact (black out) every occurrence of these terms.\nOne term per line."))
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("john@example.com\n555-123-4567\nAccount #")
        v.addWidget(self.text)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Redact"); b_ok.setObjectName("danger"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)

    def terms(self) -> list[str]:
        return [t.strip() for t in self.text.toPlainText().splitlines() if t.strip()]


# ----------------------------------------------------------------- signature pad
class SignaturePad(QWidget):
    """A small canvas for drawing a signature with the mouse/trackpad."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(560, 200)
        self.setStyleSheet("background:white; border:1px solid #777; border-radius:6px;")
        self._strokes: list[list[QPointF]] = []
        self._current: list[QPointF] = []

    def clear(self):
        self._strokes = []
        self._current = []
        self.update()

    def is_empty(self) -> bool:
        return not self._strokes

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._current = [e.position()]
            self.update()

    def mouseMoveEvent(self, e):
        if self._current is not None and e.buttons() & Qt.LeftButton:
            self._current.append(e.position())
            self.update()

    def mouseReleaseEvent(self, e):
        if self._current:
            self._strokes.append(self._current)
            self._current = []
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), Qt.white)
        pen = QPen(QColor("#0a3a82"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        for stroke in self._strokes:
            for i in range(1, len(stroke)):
                p.drawLine(stroke[i-1], stroke[i])
        if self._current:
            for i in range(1, len(self._current)):
                p.drawLine(self._current[i-1], self._current[i])

    def to_pixmap(self) -> QPixmap:
        # bounding box of strokes, transparent background
        if not self._strokes:
            return QPixmap()
        all_pts = [pt for s in self._strokes for pt in s]
        xs = [p.x() for p in all_pts]; ys = [p.y() for p in all_pts]
        pad = 8
        x0, x1 = max(0, min(xs) - pad), min(self.width(), max(xs) + pad)
        y0, y1 = max(0, min(ys) - pad), min(self.height(), max(ys) + pad)
        w, h = int(x1 - x0), int(y1 - y0)
        pix = QPixmap(max(w, 4), max(h, 4))
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(-x0, -y0)
        pen = QPen(QColor("#0a3a82"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        for stroke in self._strokes:
            for i in range(1, len(stroke)):
                p.drawLine(stroke[i-1], stroke[i])
        p.end()
        return pix


class SignatureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Signature")
        self.result_pixmap: QPixmap | None = None
        v = QVBoxLayout(self)
        tabs = QTabWidget()

        # draw tab
        draw = QWidget(); dl = QVBoxLayout(draw)
        dl.addWidget(QLabel("Sign with your mouse or trackpad below:"))
        self.pad = SignaturePad()
        dl.addWidget(self.pad)
        bclear = QPushButton("Clear"); bclear.setObjectName("secondary")
        bclear.clicked.connect(self.pad.clear)
        dl.addWidget(bclear, 0, Qt.AlignLeft)
        tabs.addTab(draw, "Draw")

        # type tab
        typ = QWidget(); tl = QVBoxLayout(typ)
        tl.addWidget(QLabel("Type your name:"))
        self.type_name = QLineEdit()
        tl.addWidget(self.type_name)
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Brush Script MT", "Lucida Handwriting", "Segoe Script",
                                  "Comic Sans MS", "Pacifico", "Dancing Script"])
        tl.addWidget(QLabel("Font:"))
        tl.addWidget(self.font_combo)
        self.type_preview = QLabel(); self.type_preview.setFixedHeight(80)
        self.type_preview.setStyleSheet("background:white; border:1px solid #777; border-radius:6px;")
        self.type_preview.setAlignment(Qt.AlignCenter)
        tl.addWidget(self.type_preview)
        self.type_name.textChanged.connect(self._update_typed)
        self.font_combo.currentTextChanged.connect(self._update_typed)
        tabs.addTab(typ, "Type")

        # image tab
        img = QWidget(); il = QVBoxLayout(img)
        il.addWidget(QLabel("Use an image of your signature:"))
        self.img_path = QLineEdit()
        bload = QPushButton("Browse..."); bload.clicked.connect(self._browse_img)
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,0,0,0)
        h.addWidget(self.img_path, 1); h.addWidget(bload)
        il.addWidget(w)
        self.img_preview = QLabel(); self.img_preview.setFixedHeight(100)
        self.img_preview.setStyleSheet("background:white; border:1px solid #777; border-radius:6px;")
        self.img_preview.setAlignment(Qt.AlignCenter)
        il.addWidget(self.img_preview)
        tabs.addTab(img, "Image")

        v.addWidget(tabs)
        self.tabs = tabs

        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Use this signature"); b_ok.clicked.connect(self._ok)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)

    def _update_typed(self):
        text = self.type_name.text() or "Your Name"
        pix = QPixmap(560, 80); pix.fill(Qt.white)
        p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        f = QFont(self.font_combo.currentText(), 36)
        f.setItalic(True)
        p.setFont(f); p.setPen(QColor("#0a3a82"))
        p.drawText(pix.rect(), Qt.AlignCenter, text)
        p.end()
        self.type_preview.setPixmap(pix)

    def _browse_img(self):
        p, _ = QFileDialog.getOpenFileName(self, "Signature image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if p:
            self.img_path.setText(p)
            self.img_preview.setPixmap(QPixmap(p).scaledToHeight(98, Qt.SmoothTransformation))

    def _ok(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            if self.pad.is_empty():
                QMessageBox.warning(self, "Signature", "Draw a signature first")
                return
            self.result_pixmap = self.pad.to_pixmap()
        elif idx == 1:
            text = self.type_name.text().strip()
            if not text:
                QMessageBox.warning(self, "Signature", "Type your name")
                return
            # render transparent pixmap with text
            tmp = QPixmap(800, 120); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setRenderHint(QPainter.Antialiasing)
            f = QFont(self.font_combo.currentText(), 56); f.setItalic(True)
            p.setFont(f); p.setPen(QColor("#0a3a82"))
            p.drawText(tmp.rect(), Qt.AlignCenter, text)
            p.end()
            self.result_pixmap = tmp
        else:
            if not self.img_path.text() or not os.path.isfile(self.img_path.text()):
                QMessageBox.warning(self, "Signature", "Pick a valid image")
                return
            self.result_pixmap = QPixmap(self.img_path.text())
        self.accept()


# ----------------------------------------------------------------- export tab
class ExportDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export PDF")
        self.source = source_path
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Choose what to export:"))
        g = QGroupBox()
        gl = QVBoxLayout(g)
        self.rb_images = QRadioButton("Images (PNG, one per page)"); self.rb_images.setChecked(True)
        self.rb_jpg = QRadioButton("Images (JPEG, one per page)")
        self.rb_text = QRadioButton("Plain text (.txt)")
        self.rb_extract_images = QRadioButton("Extract embedded images")
        for rb in (self.rb_images, self.rb_jpg, self.rb_text, self.rb_extract_images):
            gl.addWidget(rb)
        v.addWidget(g)
        form = QFormLayout()
        self.dpi = QSpinBox(); self.dpi.setRange(72, 600); self.dpi.setValue(200)
        form.addRow("Image DPI:", self.dpi)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Export"); b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(b_ok)
        v.addLayout(h)

    def _go(self):
        if self.rb_text.isChecked():
            out, _ = QFileDialog.getSaveFileName(self, "Save text",
                                                 f"{Path(self.source).stem}.txt", "Text (*.txt)")
            if not out: return
            try:
                eng.extract_text(self.source, out)
                QMessageBox.information(self, "Export", f"Saved to {out}")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Export failed", str(e))
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Output folder")
        if not out_dir: return
        try:
            if self.rb_images.isChecked():
                files = eng.pdf_to_images(self.source, out_dir, fmt="png", dpi=self.dpi.value())
            elif self.rb_jpg.isChecked():
                files = eng.pdf_to_images(self.source, out_dir, fmt="jpg", dpi=self.dpi.value())
            else:
                files = eng.extract_images(self.source, out_dir)
            QMessageBox.information(self, "Export", f"Wrote {len(files)} file(s)")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))


# ----------------------------------------------------------------- find/search
class SearchPanel(QWidget):
    next_match = Signal()
    prev_match = Signal()
    search_changed = Signal(str)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self); h.setContentsMargins(8, 6, 8, 6)
        self.input = QLineEdit(); self.input.setPlaceholderText("Search... (Enter for next)")
        self.input.textChanged.connect(self.search_changed.emit)
        self.input.returnPressed.connect(self.next_match.emit)
        b_prev = QPushButton("Prev"); b_prev.setObjectName("secondary")
        b_next = QPushButton("Next"); b_next.setObjectName("secondary")
        b_close = QPushButton("x"); b_close.setObjectName("secondary"); b_close.setFixedWidth(32)
        b_prev.clicked.connect(self.prev_match.emit)
        b_next.clicked.connect(self.next_match.emit)
        b_close.clicked.connect(self.close_requested.emit)
        self.status = QLabel("")
        h.addWidget(QLabel("Find:"))
        h.addWidget(self.input, 1)
        h.addWidget(self.status)
        h.addWidget(b_prev); h.addWidget(b_next); h.addWidget(b_close)
        self.setStyleSheet("background:#2d2d30;")
