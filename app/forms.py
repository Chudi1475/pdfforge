"""Form fields - listing, filling, and flattening."""
from __future__ import annotations
from typing import Optional, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QComboBox, QScrollArea, QWidget, QFormLayout, QPushButton, QMessageBox,
    QGroupBox
)

from .pdf_engine import PdfDocument


class FormFillDialog(QDialog):
    fields_updated = Signal()

    def __init__(self, doc: PdfDocument, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fill form fields")
        self.resize(540, 600)
        self.doc = doc
        self.widgets: list[tuple[dict, object]] = []

        v = QVBoxLayout(self)
        v.addWidget(QLabel("Fill in the form fields below. "
                           "Choose Apply to write back, or Flatten to make them permanent."))

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); scroll.setWidget(body)
        bv = QVBoxLayout(body)

        fields = doc.list_form_fields()
        if not fields:
            bv.addWidget(QLabel("This PDF has no form fields."))
        by_page: dict[int, list[dict]] = {}
        for f in fields:
            by_page.setdefault(f["page"], []).append(f)
        for page_idx in sorted(by_page):
            grp = QGroupBox(f"Page {page_idx + 1}")
            fl = QFormLayout(grp)
            for f in by_page[page_idx]:
                lbl = f["label"] or f["name"] or "(unnamed)"
                t = (f["type"] or "").lower()
                w = None
                if "checkbox" in t:
                    w = QCheckBox()
                    w.setChecked(bool(f["value"]))
                elif "choice" in t or "combo" in t or "list" in t:
                    w = QComboBox()
                    for opt in (f["options"] or []):
                        w.addItem(str(opt))
                    if f["value"]:
                        w.setCurrentText(str(f["value"]))
                else:
                    w = QLineEdit(str(f["value"] or ""))
                fl.addRow(lbl + ":", w)
                self.widgets.append((f, w))
            bv.addWidget(grp)
        bv.addStretch(1)
        v.addWidget(scroll, 1)

        h = QHBoxLayout(); h.addStretch()
        b_cancel = QPushButton("Cancel"); b_cancel.setObjectName("secondary"); b_cancel.clicked.connect(self.reject)
        b_apply = QPushButton("Apply"); b_apply.clicked.connect(self._apply)
        b_flatten = QPushButton("Flatten"); b_flatten.clicked.connect(self._flatten)
        h.addWidget(b_cancel); h.addWidget(b_apply); h.addWidget(b_flatten)
        v.addLayout(h)

    def _gather(self) -> int:
        n = 0
        for f, w in self.widgets:
            try:
                if isinstance(w, QCheckBox):
                    val = w.isChecked()
                elif isinstance(w, QComboBox):
                    val = w.currentText()
                else:
                    val = w.text()
                if self.doc.set_form_field(f["page"], f["name"], val):
                    n += 1
            except Exception:
                pass
        return n

    def _apply(self):
        n = self._gather()
        self.fields_updated.emit()
        QMessageBox.information(self, "Forms", f"Updated {n} field(s).")
        self.accept()

    def _flatten(self):
        self._gather()
        self.doc.flatten_form_fields()
        self.fields_updated.emit()
        QMessageBox.information(self, "Forms",
                                "Form data was burned into the document.")
        self.accept()
