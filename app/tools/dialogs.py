"""All operation dialogs - merge, split, encrypt, compress, OCR, watermark,
   page numbers, redact, signature, export, crop, headers/footers, insert pages,
   replace pages, find-replace, hyperlink, bookmarks, stamps, sanitize, compare,
   image watermark, batch, and TTS.
"""
from __future__ import annotations
import os
import tempfile
import webbrowser
from io import BytesIO
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QPointF, QSize, QThread, Signal, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QImage, QFont, QPainterPath, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QLineEdit, QFormLayout,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QGroupBox, QRadioButton,
    QProgressBar, QWidget, QTabWidget, QPlainTextEdit, QColorDialog, QApplication,
    QScrollArea, QToolButton, QButtonGroup, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QSlider, QFrame, QSplitter, QTextBrowser
)

from .. import pdf_engine as eng
from ..stamps import BUILTIN_STAMPS, render_stamp, render_round_stamp, pixmap_to_png_bytes


# ===================== MERGE =====================
class MergeDialog(QDialog):
    def __init__(self, parent=None, initial_paths: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Combine PDFs")
        self.resize(600, 500)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Add PDFs in the order they should appear:"))
        self.list = QListWidget()
        self.list.setDragDropMode(QListWidget.InternalMove)
        v.addWidget(self.list, 1)
        if initial_paths:
            for p in initial_paths:
                self.list.addItem(QListWidgetItem(p))
        h = QHBoxLayout()
        b_add = QPushButton("Add files...")
        b_rm = QPushButton("Remove"); b_rm.setObjectName("secondary")
        b_up = QPushButton("Up"); b_up.setObjectName("secondary")
        b_dn = QPushButton("Down"); b_dn.setObjectName("secondary")
        for b in (b_add, b_rm, b_up, b_dn): h.addWidget(b)
        h.addStretch()
        v.addLayout(h)
        b_add.clicked.connect(self._add); b_rm.clicked.connect(self._remove)
        b_up.clicked.connect(lambda: self._move(-1)); b_dn.clicked.connect(lambda: self._move(+1))
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Combine"); b_ok.clicked.connect(self._merge)
        h2.addWidget(b_c); h2.addWidget(b_ok); v.addLayout(h2)

    def _add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", "", "PDF (*.pdf)")
        for f in files: self.list.addItem(QListWidgetItem(f))

    def _remove(self):
        for it in self.list.selectedItems(): self.list.takeItem(self.list.row(it))

    def _move(self, delta: int):
        row = self.list.currentRow()
        if row < 0: return
        new = max(0, min(self.list.count() - 1, row + delta))
        if new == row: return
        it = self.list.takeItem(row); self.list.insertItem(new, it); self.list.setCurrentRow(new)

    def _merge(self):
        if self.list.count() < 2:
            QMessageBox.warning(self, "Combine", "Add at least 2 PDFs"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save combined PDF", "combined.pdf", "PDF (*.pdf)")
        if not out: return
        paths = [self.list.item(i).text() for i in range(self.list.count())]
        try:
            eng.merge_pdfs(paths, out)
            QMessageBox.information(self, "Combine", f"Saved to {out}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Combine failed", str(e))


# ===================== SPLIT =====================
class SplitDialog(QDialog):
    def __init__(self, source_path: str, page_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split PDF")
        self.source = source_path; self.page_count = page_count
        self.resize(500, 360)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"Source: {os.path.basename(source_path)} ({page_count} pages)"))
        g = QGroupBox("Split method"); gl = QVBoxLayout(g)
        self.rb_single = QRadioButton("One PDF per page"); self.rb_single.setChecked(True)
        self.rb_ranges = QRadioButton("Custom ranges (e.g. 1-3, 5, 7-10)")
        self.rb_count = QRadioButton("Every N pages")
        self.rb_size = QRadioButton("Maximum file size (KB)")
        gl.addWidget(self.rb_single); gl.addWidget(self.rb_ranges); gl.addWidget(self.rb_count); gl.addWidget(self.rb_size)

        wr = QWidget(); rl = QHBoxLayout(wr); rl.setContentsMargins(20, 0, 0, 0)
        self.ranges_edit = QLineEdit(); self.ranges_edit.setPlaceholderText("1-3, 5, 7-10")
        rl.addWidget(self.ranges_edit); gl.addWidget(wr)

        wc = QWidget(); cl = QHBoxLayout(wc); cl.setContentsMargins(20, 0, 0, 0)
        self.count_spin = QSpinBox(); self.count_spin.setRange(1, 1000); self.count_spin.setValue(5)
        cl.addWidget(QLabel("Pages per file:")); cl.addWidget(self.count_spin); cl.addStretch()
        gl.addWidget(wc)

        ws = QWidget(); sl = QHBoxLayout(ws); sl.setContentsMargins(20, 0, 0, 0)
        self.size_spin = QSpinBox(); self.size_spin.setRange(50, 50000); self.size_spin.setValue(1000); self.size_spin.setSuffix(" KB")
        sl.addWidget(QLabel("Max size:")); sl.addWidget(self.size_spin); sl.addStretch()
        gl.addWidget(ws)
        v.addWidget(g)

        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Split"); b_ok.clicked.connect(self._split)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def _parse_ranges(self, txt: str):
        out = []
        for part in txt.split(","):
            part = part.strip()
            if not part: continue
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = int(a) - 1, int(b) - 1
            else:
                a = b = int(part) - 1
            if a < 0 or b >= self.page_count or a > b:
                raise ValueError(f"Invalid range: {part}")
            out.append((a, b))
        return out

    def _split(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Output folder")
        if not out_dir: return
        try:
            if self.rb_single.isChecked():
                files = eng.split_pdf(self.source, out_dir, mode="single")
            elif self.rb_ranges.isChecked():
                ranges = self._parse_ranges(self.ranges_edit.text())
                if not ranges:
                    QMessageBox.warning(self, "Split", "Enter at least one range"); return
                files = eng.split_pdf(self.source, out_dir, mode="ranges", ranges=ranges)
            elif self.rb_count.isChecked():
                files = eng.split_pdf(self.source, out_dir, mode="by_count",
                                      by_page_count=self.count_spin.value())
            else:
                files = eng.split_pdf(self.source, out_dir, mode="by_size",
                                      by_size_kb=self.size_spin.value())
            QMessageBox.information(self, "Split", f"Wrote {len(files)} file(s) to {out_dir}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Split failed", str(e))


# ===================== ENCRYPT =====================
class EncryptDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password protect PDF")
        self.source = source_path
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.pw = QLineEdit(); self.pw.setEchoMode(QLineEdit.Password)
        self.pw2 = QLineEdit(); self.pw2.setEchoMode(QLineEdit.Password)
        self.owner = QLineEdit(); self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText("optional — defaults to user password")
        form.addRow("Open password:", self.pw)
        form.addRow("Confirm:", self.pw2)
        form.addRow("Owner password:", self.owner)
        v.addLayout(form)
        g = QGroupBox("Permissions"); gl = QVBoxLayout(g)
        self.cb_print = QCheckBox("Allow printing"); self.cb_print.setChecked(True)
        self.cb_copy = QCheckBox("Allow copying text/images"); self.cb_copy.setChecked(True)
        self.cb_modify = QCheckBox("Allow modifying content"); self.cb_modify.setChecked(False)
        self.cb_annotate = QCheckBox("Allow annotations & form filling"); self.cb_annotate.setChecked(False)
        for c in (self.cb_print, self.cb_copy, self.cb_modify, self.cb_annotate):
            gl.addWidget(c)
        v.addWidget(g)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Protect"); b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def _go(self):
        if not self.pw.text():
            QMessageBox.warning(self, "Protect", "Password is required"); return
        if self.pw.text() != self.pw2.text():
            QMessageBox.warning(self, "Protect", "Passwords do not match"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save protected PDF",
                                             f"{Path(self.source).stem}_protected.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            eng.encrypt_pdf(self.source, out, user_pw=self.pw.text(),
                            owner_pw=self.owner.text() or self.pw.text(),
                            allow_print=self.cb_print.isChecked(),
                            allow_copy=self.cb_copy.isChecked(),
                            allow_modify=self.cb_modify.isChecked(),
                            allow_annotate=self.cb_annotate.isChecked())
            QMessageBox.information(self, "Protect", f"Saved to {out}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Protect failed", str(e))


# ===================== COMPRESS =====================
class CompressDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compress PDF")
        self.source = source_path
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Re-save with cleanup and image downsampling."))
        form = QFormLayout()
        self.preset = QComboBox()
        self.preset.addItems(["High quality (95%, max 2000px)",
                              "Standard (75%, max 1500px)",
                              "Small (60%, max 1200px)",
                              "Smallest (40%, max 900px)",
                              "Custom..."])
        self.preset.setCurrentIndex(1)
        self.preset.currentIndexChanged.connect(self._on_preset_change)
        form.addRow("Preset:", self.preset)
        self.quality = QSpinBox(); self.quality.setRange(20, 95); self.quality.setValue(75); self.quality.setSuffix("%")
        form.addRow("JPEG quality:", self.quality)
        self.dim = QSpinBox(); self.dim.setRange(400, 4000); self.dim.setValue(1500); self.dim.setSuffix(" px")
        form.addRow("Max image dimension:", self.dim)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Compress"); b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def _on_preset_change(self, idx: int):
        presets = [(95, 2000), (75, 1500), (60, 1200), (40, 900)]
        if 0 <= idx < len(presets):
            q, d = presets[idx]
            self.quality.setValue(q); self.dim.setValue(d)

    def _go(self):
        out, _ = QFileDialog.getSaveFileName(self, "Save compressed PDF",
                                             f"{Path(self.source).stem}_compressed.pdf", "PDF (*.pdf)")
        if not out: return
        try:
            before = os.path.getsize(self.source)
            eng.compress_pdf(self.source, out, image_quality=self.quality.value(),
                             max_image_dim=self.dim.value())
            after = os.path.getsize(out)
            saved = (1 - after / before) * 100
            QMessageBox.information(self, "Compress",
                                    f"Saved {saved:.1f}%\n{before/1024:.0f} KB → {after/1024:.0f} KB")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Compress failed", str(e))


# ===================== OCR =====================
class OcrWorker(QThread):
    progress = Signal(int, int)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, src, dst, tcmd, lang):
        super().__init__()
        self.src, self.dst, self.tcmd, self.lang = src, dst, tcmd, lang

    def run(self):
        try:
            ok = eng.ocr_pdf(self.src, self.dst, tesseract_cmd=self.tcmd, language=self.lang,
                             progress=lambda i, n: self.progress.emit(i, n))
            if ok: self.finished_ok.emit(self.dst)
            else: self.failed.emit("OCR failed — is Tesseract installed?")
        except Exception as e:
            self.failed.emit(str(e))


class OcrDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Make searchable (OCR)")
        self.source = source_path
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Run OCR to make scanned text searchable."))
        form = QFormLayout()
        self.tess = QLineEdit(eng.find_tesseract() or "")
        self.tess.setPlaceholderText(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        b_br = QPushButton("..."); b_br.clicked.connect(self._browse_tess)
        wt = QWidget(); h = QHBoxLayout(wt); h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.tess, 1); h.addWidget(b_br)
        form.addRow("Tesseract:", wt)
        self.lang = QComboBox()
        self.lang.addItems(["eng", "spa", "fra", "deu", "ita", "por", "rus", "chi_sim", "jpn", "ara", "kor"])
        form.addRow("Language:", self.lang)
        v.addLayout(form)
        self.bar = QProgressBar(); v.addWidget(self.bar)
        v.addWidget(QLabel("No Tesseract? https://github.com/UB-Mannheim/tesseract/wiki"))
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        self.b_ok = QPushButton("Run OCR"); self.b_ok.clicked.connect(self._go)
        h2.addWidget(b_c); h2.addWidget(self.b_ok); v.addLayout(h2)
        self.worker = None

    def _browse_tess(self):
        p, _ = QFileDialog.getOpenFileName(self, "Find tesseract.exe", "", "tesseract.exe")
        if p: self.tess.setText(p)

    def _go(self):
        if not os.path.isfile(self.tess.text()):
            QMessageBox.warning(self, "OCR", "Locate tesseract.exe"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save searchable PDF",
                                             f"{Path(self.source).stem}_ocr.pdf", "PDF (*.pdf)")
        if not out: return
        self.b_ok.setEnabled(False)
        self.worker = OcrWorker(self.source, out, self.tess.text(), self.lang.currentText())
        self.worker.progress.connect(lambda i, n: (self.bar.setMaximum(n), self.bar.setValue(i)))
        self.worker.finished_ok.connect(self._done); self.worker.failed.connect(self._fail)
        self.worker.start()

    def _done(self, path):
        QMessageBox.information(self, "OCR", f"Saved to {path}"); self.accept()

    def _fail(self, msg):
        QMessageBox.critical(self, "OCR failed", msg); self.b_ok.setEnabled(True)


# ===================== WATERMARK (text) =====================
class WatermarkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add watermark")
        self.color = QColor(120, 120, 120)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.text = QLineEdit("DRAFT"); form.addRow("Text:", self.text)
        self.size = QSpinBox(); self.size.setRange(8, 300); self.size.setValue(72); form.addRow("Font size:", self.size)
        self.opacity = QSpinBox(); self.opacity.setRange(5, 100); self.opacity.setValue(25); self.opacity.setSuffix("%"); form.addRow("Opacity:", self.opacity)
        self.rotation = QSpinBox(); self.rotation.setRange(-180, 180); self.rotation.setValue(45); form.addRow("Rotation:", self.rotation)
        self.b_color = QPushButton(""); self.b_color.setObjectName("secondary"); self.b_color.clicked.connect(self._pick)
        form.addRow("Color:", self.b_color)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Apply"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)
        self._refresh_color()

    def _pick(self):
        c = QColorDialog.getColor(self.color, self, "Watermark color")
        if c.isValid(): self.color = c; self._refresh_color()

    def _refresh_color(self):
        self.b_color.setStyleSheet(f"background:{self.color.name()};")

    def settings(self):
        c = self.color
        return dict(text=self.text.text(), fontsize=self.size.value(),
                    opacity=self.opacity.value() / 100, rotation=self.rotation.value(),
                    color=(c.redF(), c.greenF(), c.blueF()))


# ===================== IMAGE WATERMARK =====================
class ImageWatermarkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image watermark")
        self.image_path: str | None = None
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.path_edit = QLineEdit(); b_br = QPushButton("..."); b_br.clicked.connect(self._browse)
        wi = QWidget(); h = QHBoxLayout(wi); h.setContentsMargins(0,0,0,0); h.addWidget(self.path_edit, 1); h.addWidget(b_br)
        form.addRow("Image:", wi)
        self.scale = QSpinBox(); self.scale.setRange(10, 200); self.scale.setValue(50); self.scale.setSuffix("% of page width")
        form.addRow("Scale:", self.scale)
        self.opacity = QSpinBox(); self.opacity.setRange(5, 100); self.opacity.setValue(35); self.opacity.setSuffix("%")
        form.addRow("Opacity:", self.opacity)
        self.rotation = QSpinBox(); self.rotation.setRange(-180, 180); self.rotation.setValue(0)
        form.addRow("Rotation:", self.rotation)
        v.addLayout(form)
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Apply"); b_ok.clicked.connect(self.accept)
        h2.addWidget(b_c); h2.addWidget(b_ok); v.addLayout(h2)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Watermark image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if p: self.path_edit.setText(p); self.image_path = p

    def settings(self):
        return dict(image_path=self.path_edit.text(),
                    scale=self.scale.value() / 100,
                    opacity=self.opacity.value() / 100,
                    rotation=self.rotation.value())


# ===================== PAGE NUMBERS =====================
class PageNumbersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add page numbers")
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.start = QSpinBox(); self.start.setRange(1, 9999); self.start.setValue(1); form.addRow("Start at:", self.start)
        self.size = QSpinBox(); self.size.setRange(6, 36); self.size.setValue(11); form.addRow("Font size:", self.size)
        self.pattern = QLineEdit("{n}"); form.addRow("Format ({n}, {N}):", self.pattern)
        self.position = QComboBox(); self.position.addItems([
            "bottom-center", "bottom-right", "bottom-left",
            "top-center", "top-right", "top-left"]); form.addRow("Position:", self.position)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Apply"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def settings(self):
        return dict(start=self.start.value(), fontsize=self.size.value(),
                    position=self.position.currentText(), pattern=self.pattern.text() or "{n}")


# ===================== HEADERS & FOOTERS =====================
class HeaderFooterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Headers & Footers")
        self.resize(520, 360)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Use {n} for current page, {N} for total."))
        gh = QGroupBox("Header"); fh = QFormLayout(gh)
        self.hl = QLineEdit(); self.hc = QLineEdit(); self.hr = QLineEdit()
        fh.addRow("Left:", self.hl); fh.addRow("Center:", self.hc); fh.addRow("Right:", self.hr)
        v.addWidget(gh)
        gf = QGroupBox("Footer"); ff = QFormLayout(gf)
        self.fl = QLineEdit(); self.fc = QLineEdit(); self.fr = QLineEdit()
        ff.addRow("Left:", self.fl); ff.addRow("Center:", self.fc); ff.addRow("Right:", self.fr)
        v.addWidget(gf)
        form = QFormLayout()
        self.size = QSpinBox(); self.size.setRange(6, 36); self.size.setValue(10)
        form.addRow("Font size:", self.size)
        self.margin = QSpinBox(); self.margin.setRange(8, 80); self.margin.setValue(28); self.margin.setSuffix(" pt")
        form.addRow("Margin:", self.margin)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Apply"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def settings(self):
        return dict(header_left=self.hl.text(), header_center=self.hc.text(), header_right=self.hr.text(),
                    footer_left=self.fl.text(), footer_center=self.fc.text(), footer_right=self.fr.text(),
                    fontsize=self.size.value(), margin=float(self.margin.value()))


# ===================== CROP =====================
class CropDialog(QDialog):
    """Crop all pages by inset margins (in points)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop pages")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Crop margins (in points: 72 pt = 1 inch). "
                           "Use the Crop tool for visual crop on a single page."))
        form = QFormLayout()
        self.left = QSpinBox(); self.left.setRange(0, 800); self.left.setSuffix(" pt"); form.addRow("Left:", self.left)
        self.top = QSpinBox(); self.top.setRange(0, 800); self.top.setSuffix(" pt"); form.addRow("Top:", self.top)
        self.right = QSpinBox(); self.right.setRange(0, 800); self.right.setSuffix(" pt"); form.addRow("Right:", self.right)
        self.bottom = QSpinBox(); self.bottom.setRange(0, 800); self.bottom.setSuffix(" pt"); form.addRow("Bottom:", self.bottom)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_reset = QPushButton("Reset all"); b_reset.setObjectName("secondary"); b_reset.clicked.connect(self._reset_clicked)
        b_ok = QPushButton("Apply to all"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_reset); h.addStretch(); h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)
        self._reset = False

    def _reset_clicked(self):
        self._reset = True; self.accept()

    def is_reset(self) -> bool: return self._reset

    def margins(self):
        return (self.left.value(), self.top.value(), self.right.value(), self.bottom.value())


# ===================== INSERT PAGES =====================
class InsertPagesDialog(QDialog):
    def __init__(self, current_page: int, total_pages: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert pages from another PDF")
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.src = QLineEdit()
        b = QPushButton("..."); b.clicked.connect(self._browse)
        wsrc = QWidget(); h = QHBoxLayout(wsrc); h.setContentsMargins(0,0,0,0); h.addWidget(self.src, 1); h.addWidget(b)
        form.addRow("Source PDF:", wsrc)
        self.from_page = QSpinBox(); self.from_page.setRange(1, 99999); self.from_page.setValue(1); form.addRow("From page:", self.from_page)
        self.to_page = QSpinBox(); self.to_page.setRange(1, 99999); self.to_page.setValue(1); form.addRow("To page:", self.to_page)
        self.position = QComboBox()
        self.position.addItem(f"After current page ({current_page + 1})")
        self.position.addItem(f"Before current page ({current_page + 1})")
        self.position.addItem("At start (before page 1)")
        self.position.addItem(f"At end (after page {total_pages})")
        form.addRow("Insert:", self.position)
        v.addLayout(form)
        self.current_page = current_page; self.total_pages = total_pages
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Insert"); b_ok.clicked.connect(self.accept)
        h2.addWidget(b_c); h2.addWidget(b_ok); v.addLayout(h2)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Source PDF", "", "PDF (*.pdf)")
        if p: self.src.setText(p)

    def at_index(self) -> int:
        i = self.position.currentIndex()
        if i == 0: return self.current_page + 1   # after
        if i == 1: return self.current_page       # before
        if i == 2: return 0                       # start
        return self.total_pages                   # end

    def settings(self):
        return dict(source=self.src.text(),
                    from_page=self.from_page.value() - 1,
                    to_page=self.to_page.value() - 1,
                    at_index=self.at_index())


# ===================== REPLACE PAGE =====================
class ReplacePageDialog(QDialog):
    def __init__(self, current_page: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Replace page {current_page + 1}")
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.src = QLineEdit()
        b = QPushButton("..."); b.clicked.connect(self._browse)
        ws = QWidget(); h = QHBoxLayout(ws); h.setContentsMargins(0,0,0,0); h.addWidget(self.src, 1); h.addWidget(b)
        form.addRow("Source PDF:", ws)
        self.page = QSpinBox(); self.page.setRange(1, 99999); self.page.setValue(1)
        form.addRow("Use page:", self.page)
        v.addLayout(form)
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Replace"); b_ok.clicked.connect(self.accept)
        h2.addWidget(b_c); h2.addWidget(b_ok); v.addLayout(h2)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Source PDF", "", "PDF (*.pdf)")
        if p: self.src.setText(p)

    def settings(self): return dict(source=self.src.text(), page=self.page.value() - 1)


# ===================== FIND & REPLACE =====================
class FindReplaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find and replace")
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.find = QLineEdit(); form.addRow("Find:", self.find)
        self.repl = QLineEdit(); form.addRow("Replace with:", self.repl)
        self.case = QCheckBox("Match case"); form.addRow("", self.case)
        v.addLayout(form)
        v.addWidget(QLabel("⚠ Replace permanently rewrites text. Make a backup first."))
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Replace All"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def settings(self):
        return dict(find=self.find.text(), replace=self.repl.text(),
                    case_sensitive=self.case.isChecked())


# ===================== HYPERLINK =====================
class HyperlinkDialog(QDialog):
    def __init__(self, page_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create hyperlink")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Choose what the link should do, then drag a rectangle on the page."))
        g = QGroupBox(""); gl = QVBoxLayout(g)
        self.rb_uri = QRadioButton("Open a web URL"); self.rb_uri.setChecked(True)
        self.uri_edit = QLineEdit("https://"); self.uri_edit.setPlaceholderText("https://example.com")
        self.rb_page = QRadioButton(f"Go to a page in this document (1-{page_count})")
        self.page_spin = QSpinBox(); self.page_spin.setRange(1, page_count); self.page_spin.setValue(1)
        gl.addWidget(self.rb_uri); gl.addWidget(self.uri_edit)
        gl.addWidget(self.rb_page); gl.addWidget(self.page_spin)
        v.addWidget(g)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("OK"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def target(self) -> dict:
        if self.rb_uri.isChecked():
            return {"kind": "uri", "value": self.uri_edit.text().strip()}
        return {"kind": "page", "value": self.page_spin.value() - 1}


# ===================== BOOKMARK =====================
class AddBookmarkDialog(QDialog):
    def __init__(self, current_page: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add bookmark")
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.title = QLineEdit(); form.addRow("Title:", self.title)
        self.page = QSpinBox(); self.page.setRange(1, 99999); self.page.setValue(current_page + 1); form.addRow("Page:", self.page)
        self.level = QSpinBox(); self.level.setRange(1, 6); self.level.setValue(1); form.addRow("Level (1=top):", self.level)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Add"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def settings(self):
        return dict(title=self.title.text() or "Bookmark", page=self.page.value() - 1, level=self.level.value())


# ===================== STAMPS GALLERY =====================
class StampsDialog(QDialog):
    chosen = Signal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose a stamp")
        self.resize(820, 520)
        v = QVBoxLayout(self)
        tabs = QTabWidget(); tabs.setObjectName("DialogTabs")

        # Built-in tab
        bw = QWidget(); bv = QVBoxLayout(bw)
        bv.addWidget(QLabel("Pick a stamp, then drag a rectangle on the page."))
        grid = QGridLayout()
        for i, (name, color, label, _) in enumerate(BUILTIN_STAMPS):
            pix = render_stamp(label, color, width=320, height=100)
            btn = QPushButton()
            btn.setIcon(pix); btn.setIconSize(QSize(220, 70))
            btn.setMinimumHeight(90)
            btn.setStyleSheet("background:#3d3d3d; border:1px solid #555; border-radius:6px;")
            btn.clicked.connect(lambda _checked=False, p=pix: self._pick(p))
            grid.addWidget(btn, i // 2, i % 2)
        bv.addLayout(grid); bv.addStretch(1)
        tabs.addTab(bw, "Built-in (rectangular)")

        # Round stamps tab
        rw = QWidget(); rv = QVBoxLayout(rw)
        rgrid = QGridLayout()
        for i, (name, color, label, _) in enumerate(BUILTIN_STAMPS[:8]):
            pix = render_round_stamp(label, color, size=200)
            btn = QPushButton(); btn.setIcon(pix); btn.setIconSize(QSize(150, 150))
            btn.setMinimumSize(170, 170)
            btn.setStyleSheet("background:#3d3d3d; border:1px solid #555; border-radius:6px;")
            btn.clicked.connect(lambda _checked=False, p=pix: self._pick(p))
            rgrid.addWidget(btn, i // 4, i % 4)
        rv.addLayout(rgrid); rv.addStretch(1)
        tabs.addTab(rw, "Round")

        # Custom tab
        cw = QWidget(); cv = QVBoxLayout(cw)
        f = QFormLayout()
        self.custom_text = QLineEdit("CUSTOM")
        self.custom_color = QPushButton(""); self.custom_color.setObjectName("secondary")
        self.custom_color._color = QColor("#c62828")
        self.custom_color.setStyleSheet(f"background:{self.custom_color._color.name()};")
        self.custom_color.clicked.connect(self._pick_custom_color)
        self.custom_round = QCheckBox("Round shape")
        f.addRow("Text:", self.custom_text); f.addRow("Color:", self.custom_color); f.addRow("", self.custom_round)
        cv.addLayout(f)
        bmake = QPushButton("Use this stamp"); bmake.clicked.connect(self._pick_custom)
        cv.addWidget(bmake); cv.addStretch(1)
        tabs.addTab(cw, "Custom")

        # Image tab
        iw = QWidget(); iv = QVBoxLayout(iw)
        iv.addWidget(QLabel("Use an image (PNG with transparency works best):"))
        self.img_path = QLineEdit()
        bbr = QPushButton("..."); bbr.clicked.connect(self._browse_img)
        wi = QWidget(); h = QHBoxLayout(wi); h.setContentsMargins(0,0,0,0); h.addWidget(self.img_path, 1); h.addWidget(bbr)
        iv.addWidget(wi)
        bimg = QPushButton("Use this image"); bimg.clicked.connect(self._pick_image)
        iv.addWidget(bimg); iv.addStretch(1)
        tabs.addTab(iw, "From image")

        v.addWidget(tabs)
        b_close = QPushButton("Close"); b_close.setObjectName("secondary"); b_close.clicked.connect(self.reject)
        h2 = QHBoxLayout(); h2.addStretch(); h2.addWidget(b_close); v.addLayout(h2)

    def _pick(self, pix: QPixmap):
        self.chosen.emit(pix); self.accept()

    def _pick_custom_color(self):
        c = QColorDialog.getColor(self.custom_color._color, self, "Stamp color")
        if c.isValid():
            self.custom_color._color = c
            self.custom_color.setStyleSheet(f"background:{c.name()};")

    def _pick_custom(self):
        text = self.custom_text.text() or "STAMP"
        col = self.custom_color._color.name()
        if self.custom_round.isChecked():
            pix = render_round_stamp(text, col, size=240)
        else:
            pix = render_stamp(text, col, width=360, height=110)
        self._pick(pix)

    def _browse_img(self):
        p, _ = QFileDialog.getOpenFileName(self, "Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if p: self.img_path.setText(p)

    def _pick_image(self):
        if not self.img_path.text() or not os.path.isfile(self.img_path.text()):
            QMessageBox.warning(self, "Stamp", "Pick a valid image"); return
        pix = QPixmap(self.img_path.text())
        if pix.isNull():
            QMessageBox.warning(self, "Stamp", "Could not load image"); return
        self._pick(pix)


# ===================== REDACT BY TEXT =====================
class RedactTextDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Redact by text")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Redact (black out) every occurrence of these terms.\nOne per line."))
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("john@example.com\n555-123-4567\nAccount #")
        v.addWidget(self.text)
        self.case = QCheckBox("Match case")
        v.addWidget(self.case)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Redact now"); b_ok.setObjectName("danger"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def terms(self): return [t.strip() for t in self.text.toPlainText().splitlines() if t.strip()]


# ===================== SIGNATURE PAD =====================
class SignaturePad(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(580, 200)
        self.setStyleSheet("background:white; border:1px solid #777; border-radius:6px;")
        self._strokes = []; self._current = []

    def clear(self): self._strokes = []; self._current = []; self.update()
    def is_empty(self): return not self._strokes

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._current = [e.position()]; self.update()
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton: self._current.append(e.position()); self.update()
    def mouseReleaseEvent(self, e):
        if self._current: self._strokes.append(self._current); self._current = []; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), Qt.white)
        pen = QPen(QColor("#0a3a82"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin); p.setPen(pen)
        for stroke in self._strokes:
            for i in range(1, len(stroke)): p.drawLine(stroke[i-1], stroke[i])
        if self._current:
            for i in range(1, len(self._current)): p.drawLine(self._current[i-1], self._current[i])

    def to_pixmap(self) -> QPixmap:
        if not self._strokes: return QPixmap()
        all_pts = [pt for s in self._strokes for pt in s]
        xs = [p.x() for p in all_pts]; ys = [p.y() for p in all_pts]
        pad = 10
        x0, x1 = max(0, min(xs) - pad), min(self.width(), max(xs) + pad)
        y0, y1 = max(0, min(ys) - pad), min(self.height(), max(ys) + pad)
        w, h = int(x1 - x0), int(y1 - y0)
        pix = QPixmap(max(w, 4), max(h, 4)); pix.fill(Qt.transparent)
        p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing); p.translate(-x0, -y0)
        pen = QPen(QColor("#0a3a82"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin); p.setPen(pen)
        for stroke in self._strokes:
            for i in range(1, len(stroke)): p.drawLine(stroke[i-1], stroke[i])
        p.end(); return pix


class SignatureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create signature")
        self.result_pixmap: QPixmap | None = None
        v = QVBoxLayout(self); tabs = QTabWidget(); tabs.setObjectName("DialogTabs")
        # draw
        draw = QWidget(); dl = QVBoxLayout(draw)
        dl.addWidget(QLabel("Sign with your mouse or trackpad:"))
        self.pad = SignaturePad(); dl.addWidget(self.pad)
        bc = QPushButton("Clear"); bc.setObjectName("secondary"); bc.clicked.connect(self.pad.clear)
        dl.addWidget(bc, 0, Qt.AlignLeft); tabs.addTab(draw, "Draw")
        # type
        typ = QWidget(); tl = QVBoxLayout(typ)
        tl.addWidget(QLabel("Type your name:"))
        self.type_name = QLineEdit(); tl.addWidget(self.type_name)
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Brush Script MT", "Lucida Handwriting", "Segoe Script",
                                   "Comic Sans MS", "Pacifico", "Dancing Script", "Edwardian Script ITC"])
        tl.addWidget(QLabel("Font:")); tl.addWidget(self.font_combo)
        self.type_preview = QLabel(); self.type_preview.setFixedHeight(90)
        self.type_preview.setStyleSheet("background:white; border:1px solid #777; border-radius:6px;")
        self.type_preview.setAlignment(Qt.AlignCenter); tl.addWidget(self.type_preview)
        self.type_name.textChanged.connect(self._update_typed)
        self.font_combo.currentTextChanged.connect(self._update_typed)
        tabs.addTab(typ, "Type")
        # image
        img = QWidget(); il = QVBoxLayout(img)
        il.addWidget(QLabel("Use an image of your signature:"))
        self.img_path = QLineEdit(); bload = QPushButton("Browse..."); bload.clicked.connect(self._browse_img)
        wi = QWidget(); h = QHBoxLayout(wi); h.setContentsMargins(0,0,0,0); h.addWidget(self.img_path, 1); h.addWidget(bload); il.addWidget(wi)
        self.img_preview = QLabel(); self.img_preview.setFixedHeight(100)
        self.img_preview.setStyleSheet("background:white; border:1px solid #777; border-radius:6px;")
        self.img_preview.setAlignment(Qt.AlignCenter); il.addWidget(self.img_preview)
        tabs.addTab(img, "Image")
        v.addWidget(tabs); self.tabs = tabs
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Use this signature"); b_ok.clicked.connect(self._ok)
        h2.addWidget(b_c); h2.addWidget(b_ok); v.addLayout(h2)

    def _update_typed(self):
        text = self.type_name.text() or "Your Name"
        pix = QPixmap(560, 80); pix.fill(Qt.white)
        p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        f = QFont(self.font_combo.currentText(), 36); f.setItalic(True)
        p.setFont(f); p.setPen(QColor("#0a3a82"))
        p.drawText(pix.rect(), Qt.AlignCenter, text); p.end()
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
                QMessageBox.warning(self, "Signature", "Draw a signature first"); return
            self.result_pixmap = self.pad.to_pixmap()
        elif idx == 1:
            text = self.type_name.text().strip()
            if not text:
                QMessageBox.warning(self, "Signature", "Type your name"); return
            tmp = QPixmap(900, 140); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setRenderHint(QPainter.Antialiasing)
            f = QFont(self.font_combo.currentText(), 64); f.setItalic(True)
            p.setFont(f); p.setPen(QColor("#0a3a82"))
            p.drawText(tmp.rect(), Qt.AlignCenter, text); p.end()
            self.result_pixmap = tmp
        else:
            if not os.path.isfile(self.img_path.text()):
                QMessageBox.warning(self, "Signature", "Pick a valid image"); return
            self.result_pixmap = QPixmap(self.img_path.text())
        self.accept()


# ===================== EXPORT =====================
class ExportDialog(QDialog):
    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export PDF")
        self.source = source_path; self.resize(440, 380)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Choose a target format:"))
        g = QGroupBox(); gl = QVBoxLayout(g)
        self.rb_docx = QRadioButton("Microsoft Word (.docx)")
        self.rb_xlsx = QRadioButton("Microsoft Excel (.xlsx)")
        self.rb_html = QRadioButton("HTML (.html)")
        self.rb_rtf = QRadioButton("Rich Text (.rtf)")
        self.rb_txt = QRadioButton("Plain text (.txt)")
        self.rb_png = QRadioButton("Images — PNG, one per page"); self.rb_png.setChecked(True)
        self.rb_jpg = QRadioButton("Images — JPEG, one per page")
        self.rb_extract_images = QRadioButton("Extract embedded images")
        for rb in (self.rb_docx, self.rb_xlsx, self.rb_html, self.rb_rtf, self.rb_txt,
                   self.rb_png, self.rb_jpg, self.rb_extract_images):
            gl.addWidget(rb)
        v.addWidget(g)
        form = QFormLayout()
        self.dpi = QSpinBox(); self.dpi.setRange(72, 600); self.dpi.setValue(200); form.addRow("Image DPI:", self.dpi)
        v.addLayout(form)
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Export"); b_ok.clicked.connect(self._go)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)

    def _go(self):
        from .. import converters
        stem = Path(self.source).stem
        try:
            if self.rb_docx.isChecked():
                out, _ = QFileDialog.getSaveFileName(self, "Save Word", f"{stem}.docx", "Word (*.docx)")
                if not out: return
                converters.pdf_to_docx(self.source, out)
            elif self.rb_xlsx.isChecked():
                out, _ = QFileDialog.getSaveFileName(self, "Save Excel", f"{stem}.xlsx", "Excel (*.xlsx)")
                if not out: return
                converters.pdf_to_xlsx(self.source, out)
            elif self.rb_html.isChecked():
                out, _ = QFileDialog.getSaveFileName(self, "Save HTML", f"{stem}.html", "HTML (*.html)")
                if not out: return
                converters.pdf_to_html(self.source, out)
            elif self.rb_rtf.isChecked():
                out, _ = QFileDialog.getSaveFileName(self, "Save RTF", f"{stem}.rtf", "RTF (*.rtf)")
                if not out: return
                converters.pdf_to_rtf(self.source, out)
            elif self.rb_txt.isChecked():
                out, _ = QFileDialog.getSaveFileName(self, "Save text", f"{stem}.txt", "Text (*.txt)")
                if not out: return
                eng.extract_text(self.source, out)
            else:
                out_dir = QFileDialog.getExistingDirectory(self, "Output folder")
                if not out_dir: return
                if self.rb_png.isChecked():
                    eng.pdf_to_images(self.source, out_dir, fmt="png", dpi=self.dpi.value())
                elif self.rb_jpg.isChecked():
                    eng.pdf_to_images(self.source, out_dir, fmt="jpg", dpi=self.dpi.value())
                else:
                    eng.extract_images(self.source, out_dir)
                QMessageBox.information(self, "Export", f"Wrote files to {out_dir}")
                self.accept(); return
            QMessageBox.information(self, "Export", f"Saved to {out}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))


# ===================== COMPARE =====================
class CompareDialog(QDialog):
    def __init__(self, current_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare PDFs")
        self.resize(900, 640)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.a = QLineEdit(current_path or "")
        self.b = QLineEdit()
        ba = QPushButton("..."); ba.clicked.connect(lambda: self._browse(self.a))
        bb = QPushButton("..."); bb.clicked.connect(lambda: self._browse(self.b))
        wa = QWidget(); h1 = QHBoxLayout(wa); h1.setContentsMargins(0,0,0,0); h1.addWidget(self.a, 1); h1.addWidget(ba)
        wb = QWidget(); h2 = QHBoxLayout(wb); h2.setContentsMargins(0,0,0,0); h2.addWidget(self.b, 1); h2.addWidget(bb)
        form.addRow("Original:", wa); form.addRow("Revised:", wb)
        v.addLayout(form)
        self.summary = QLabel("")
        v.addWidget(self.summary)
        self.viewer = QTextBrowser(); self.viewer.setOpenExternalLinks(False)
        v.addWidget(self.viewer, 1)
        h = QHBoxLayout(); h.addStretch()
        b_save = QPushButton("Save report as HTML..."); b_save.setObjectName("secondary"); b_save.clicked.connect(self._save_html)
        b_run = QPushButton("Run comparison"); b_run.clicked.connect(self._run)
        b_c = QPushButton("Close"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.accept)
        h.addWidget(b_save); h.addStretch(); h.addWidget(b_c); h.addWidget(b_run)
        v.addLayout(h)
        self._html = ""

    def _browse(self, edit: QLineEdit):
        p, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if p: edit.setText(p)

    def _run(self):
        if not os.path.isfile(self.a.text()) or not os.path.isfile(self.b.text()):
            QMessageBox.warning(self, "Compare", "Pick two PDFs"); return
        from .. import compare as cmp
        try:
            diffs, add, rem = cmp.compare_text(self.a.text(), self.b.text())
            self.summary.setText(f"+{add} lines added, -{rem} lines removed across {len(diffs)} page(s)")
            self._html = cmp.compare_html(diffs)
            self.viewer.setHtml(self._html)
        except Exception as e:
            QMessageBox.critical(self, "Compare failed", str(e))

    def _save_html(self):
        if not self._html:
            QMessageBox.warning(self, "Compare", "Run comparison first"); return
        out, _ = QFileDialog.getSaveFileName(self, "Save report", "compare.html", "HTML (*.html)")
        if not out: return
        Path(out).write_text(self._html, encoding="utf-8")
        QMessageBox.information(self, "Compare", f"Saved to {out}")


# ===================== TTS =====================
class TtsDialog(QDialog):
    """A small floating control panel for read-aloud."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Read aloud")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        v = QVBoxLayout(self)
        from ..tts import TtsReader
        self.reader = TtsReader(self)
        self.reader.failed.connect(self._fail)
        self.reader.stopped.connect(self._on_stopped)
        self.reader.speaking_page.connect(self._on_page)

        form = QFormLayout()
        self.voice = QComboBox()
        for vid, name in TtsReader.list_voices():
            self.voice.addItem(name, vid)
        form.addRow("Voice:", self.voice)
        self.rate = QSlider(Qt.Horizontal); self.rate.setRange(80, 320); self.rate.setValue(180)
        self.rate_label = QLabel("180 wpm")
        self.rate.valueChanged.connect(lambda v: self.rate_label.setText(f"{v} wpm"))
        rate_w = QWidget(); rl = QHBoxLayout(rate_w); rl.setContentsMargins(0,0,0,0)
        rl.addWidget(self.rate); rl.addWidget(self.rate_label)
        form.addRow("Speed:", rate_w)
        v.addLayout(form)

        self.status = QLabel("Idle")
        v.addWidget(self.status)
        h = QHBoxLayout()
        self.b_play = QPushButton("Play"); self.b_play.clicked.connect(self._play)
        self.b_stop = QPushButton("Stop"); self.b_stop.setObjectName("secondary"); self.b_stop.clicked.connect(self._stop)
        self.b_stop.setEnabled(False)
        h.addWidget(self.b_play); h.addWidget(self.b_stop)
        v.addLayout(h)
        self._provider = None

    def set_text_provider(self, fn):
        """fn() -> list[(page_index, text)]"""
        self._provider = fn

    def _play(self):
        if not self._provider:
            QMessageBox.warning(self, "TTS", "Nothing to read"); return
        pages_text = self._provider()
        if not pages_text:
            QMessageBox.warning(self, "TTS", "Empty document"); return
        vid = self.voice.currentData() or None
        self.reader.start(pages_text, rate=self.rate.value(), voice_id=vid)
        self.b_play.setEnabled(False); self.b_stop.setEnabled(True)
        self.status.setText("Speaking...")

    def _stop(self):
        self.reader.stop()

    def _on_stopped(self):
        self.b_play.setEnabled(True); self.b_stop.setEnabled(False)
        self.status.setText("Idle")

    def _on_page(self, i: int):
        self.status.setText(f"Speaking page {i + 1}")

    def _fail(self, msg: str):
        QMessageBox.critical(self, "TTS failed", msg)
        self._on_stopped()

    def closeEvent(self, e):
        self.reader.stop(); super().closeEvent(e)


# ===================== BATCH =====================
class BatchDialog(QDialog):
    """Apply one of several operations to many PDF files at once."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch processor")
        self.resize(640, 540)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Apply one operation to many PDFs at once."))
        h = QHBoxLayout()
        self.list = QListWidget()
        b_add = QPushButton("Add files..."); b_add.clicked.connect(self._add)
        b_rm = QPushButton("Remove"); b_rm.setObjectName("secondary"); b_rm.clicked.connect(self._remove)
        bv = QVBoxLayout(); bv.addWidget(b_add); bv.addWidget(b_rm); bv.addStretch()
        h.addWidget(self.list, 1); h.addLayout(bv)
        v.addLayout(h, 1)

        form = QFormLayout()
        self.op = QComboBox()
        self.op.addItems(["Compress", "Add page numbers", "Add watermark",
                          "Convert to PNG images", "Convert to Word (.docx)",
                          "Convert to Excel (.xlsx)", "Convert to HTML",
                          "Extract text (.txt)", "Sanitize / strip metadata"])
        form.addRow("Operation:", self.op)
        self.out_dir = QLineEdit()
        b_br = QPushButton("..."); b_br.clicked.connect(self._browse_dir)
        w = QWidget(); ho = QHBoxLayout(w); ho.setContentsMargins(0,0,0,0); ho.addWidget(self.out_dir, 1); ho.addWidget(b_br)
        form.addRow("Output folder:", w)
        v.addLayout(form)

        self.bar = QProgressBar(); v.addWidget(self.bar)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(120)
        v.addWidget(self.log)
        h2 = QHBoxLayout(); h2.addStretch()
        b_c = QPushButton("Close"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        self.b_run = QPushButton("Run"); self.b_run.clicked.connect(self._run)
        h2.addWidget(b_c); h2.addWidget(self.b_run); v.addLayout(h2)

    def _add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDFs", "", "PDF (*.pdf)")
        for f in files: self.list.addItem(QListWidgetItem(f))

    def _remove(self):
        for it in self.list.selectedItems(): self.list.takeItem(self.list.row(it))

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder")
        if d: self.out_dir.setText(d)

    def _run(self):
        if self.list.count() == 0:
            QMessageBox.warning(self, "Batch", "Add some files"); return
        out_dir = self.out_dir.text()
        if not os.path.isdir(out_dir):
            QMessageBox.warning(self, "Batch", "Pick a valid output folder"); return
        from .. import converters
        op = self.op.currentText()
        self.bar.setMaximum(self.list.count()); self.b_run.setEnabled(False)
        ok = fail = 0
        for i in range(self.list.count()):
            src = self.list.item(i).text()
            stem = Path(src).stem
            try:
                if op == "Compress":
                    eng.compress_pdf(src, os.path.join(out_dir, f"{stem}_compressed.pdf"))
                elif op == "Add page numbers":
                    d = eng.PdfDocument(src); d.add_page_numbers(); d.save_copy(os.path.join(out_dir, f"{stem}_numbered.pdf")); d.close()
                elif op == "Add watermark":
                    d = eng.PdfDocument(src); d.add_watermark("DRAFT", opacity=0.25, fontsize=72)
                    d.save_copy(os.path.join(out_dir, f"{stem}_wm.pdf")); d.close()
                elif op == "Convert to PNG images":
                    sub = Path(out_dir) / stem; sub.mkdir(parents=True, exist_ok=True)
                    eng.pdf_to_images(src, str(sub), fmt="png", dpi=200)
                elif op == "Convert to Word (.docx)":
                    converters.pdf_to_docx(src, os.path.join(out_dir, f"{stem}.docx"))
                elif op == "Convert to Excel (.xlsx)":
                    converters.pdf_to_xlsx(src, os.path.join(out_dir, f"{stem}.xlsx"))
                elif op == "Convert to HTML":
                    converters.pdf_to_html(src, os.path.join(out_dir, f"{stem}.html"))
                elif op == "Extract text (.txt)":
                    eng.extract_text(src, os.path.join(out_dir, f"{stem}.txt"))
                elif op == "Sanitize / strip metadata":
                    d = eng.PdfDocument(src); d.sanitize()
                    d.save_copy(os.path.join(out_dir, f"{stem}_sanitized.pdf")); d.close()
                self.log.appendPlainText(f"OK  {stem}")
                ok += 1
            except Exception as e:
                self.log.appendPlainText(f"FAIL {stem}: {e}")
                fail += 1
            self.bar.setValue(i + 1)
            QApplication.processEvents()
        self.b_run.setEnabled(True)
        QMessageBox.information(self, "Batch", f"Done. {ok} succeeded, {fail} failed.")


# ===================== SEARCH PANEL (inline find bar) =====================
class SearchPanel(QWidget):
    next_match = Signal()
    prev_match = Signal()
    search_changed = Signal(str)
    close_requested = Signal()
    case_changed = Signal(bool)
    whole_words_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self); h.setContentsMargins(8, 6, 8, 6); h.setSpacing(6)
        self.input = QLineEdit(); self.input.setPlaceholderText("Find...")
        self.input.textChanged.connect(self.search_changed.emit)
        self.input.returnPressed.connect(self.next_match.emit)
        self.case = QCheckBox("Aa"); self.case.setToolTip("Match case")
        self.case.toggled.connect(self.case_changed.emit)
        self.whole = QCheckBox("|w|"); self.whole.setToolTip("Whole words")
        self.whole.toggled.connect(self.whole_words_changed.emit)
        b_prev = QPushButton("‹"); b_prev.setObjectName("secondary"); b_prev.setFixedWidth(32)
        b_next = QPushButton("›"); b_next.setObjectName("secondary"); b_next.setFixedWidth(32)
        b_close = QPushButton("✕"); b_close.setObjectName("secondary"); b_close.setFixedWidth(32)
        b_prev.clicked.connect(self.prev_match.emit)
        b_next.clicked.connect(self.next_match.emit)
        b_close.clicked.connect(self.close_requested.emit)
        self.status = QLabel("")
        h.addWidget(QLabel("Find:")); h.addWidget(self.input, 1)
        h.addWidget(self.case); h.addWidget(self.whole)
        h.addWidget(self.status); h.addWidget(b_prev); h.addWidget(b_next); h.addWidget(b_close)
        self.setStyleSheet("background:#2b2b2b;")


# ===================== SANITIZE =====================
class SanitizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sanitize document")
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "Sanitize removes:\n"
            "  • All metadata (title, author, keywords, dates)\n"
            "  • Annotations that contain JavaScript\n"
            "  • Hidden text and structure data\n\n"
            "Bookmarks, links and visible content remain."))
        h = QHBoxLayout(); h.addStretch()
        b_c = QPushButton("Cancel"); b_c.setObjectName("secondary"); b_c.clicked.connect(self.reject)
        b_ok = QPushButton("Sanitize"); b_ok.setObjectName("danger"); b_ok.clicked.connect(self.accept)
        h.addWidget(b_c); h.addWidget(b_ok); v.addLayout(h)
