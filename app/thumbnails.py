"""Sidebar thumbnails list - click to jump, drag to reorder, right-click for ops."""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QApplication
)

from .pdf_engine import PdfDocument


class ThumbnailList(QListWidget):
    page_clicked = Signal(int)
    pages_reordered = Signal()
    delete_requested = Signal(list)
    rotate_requested = Signal(list, int)
    duplicate_requested = Signal(int)
    extract_requested = Signal(list)
    insert_blank_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(160, 200))
        self.setSpacing(6)
        self.setUniformItemSizes(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setMovement(QListWidget.Snap)
        self.setResizeMode(QListWidget.Adjust)
        self.setViewMode(QListWidget.IconMode)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.itemClicked.connect(self._on_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.model().rowsMoved.connect(lambda *_: self.pages_reordered.emit())
        self.doc: Optional[PdfDocument] = None

    def load(self, doc: Optional[PdfDocument]):
        self.doc = doc
        self.clear()
        if not doc:
            return
        for i in range(doc.page_count):
            self._add_item(i)

    def _add_item(self, index: int):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, index)
        item.setText(f"{index + 1}")
        item.setTextAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        try:
            data = self.doc.thumbnail(index, max_dim=160)
            img = QImage.fromData(data)
            pix = QPixmap.fromImage(img)
            item.setIcon(QIcon(pix))
            item.setSizeHint(QSize(pix.width() + 16, pix.height() + 30))
        except Exception:
            item.setSizeHint(QSize(160, 200))
        self.addItem(item)

    def refresh(self, index: Optional[int] = None):
        if not self.doc:
            return
        if index is not None and 0 <= index < self.count():
            item = self.item(index)
            try:
                data = self.doc.thumbnail(index, max_dim=160)
                img = QImage.fromData(data)
                pix = QPixmap.fromImage(img)
                item.setIcon(QIcon(pix))
            except Exception:
                pass
        else:
            self.load(self.doc)

    def get_page_order(self) -> list[int]:
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]

    def _on_clicked(self, item: QListWidgetItem):
        self.page_clicked.emit(item.data(Qt.UserRole))

    def selected_page_indices(self) -> list[int]:
        return sorted(it.data(Qt.UserRole) for it in self.selectedItems())

    def _show_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        if not item:
            return
        idx = item.data(Qt.UserRole)
        sel = self.selected_page_indices() or [idx]
        menu = QMenu(self)
        a_go = menu.addAction("Go to page")
        menu.addSeparator()
        a_rot_l = menu.addAction("Rotate 90 left")
        a_rot_r = menu.addAction("Rotate 90 right")
        a_rot_180 = menu.addAction("Rotate 180")
        menu.addSeparator()
        a_insert = menu.addAction("Insert blank page after")
        a_dup = menu.addAction("Duplicate page")
        a_extract = menu.addAction("Extract to new PDF...")
        menu.addSeparator()
        a_del = menu.addAction("Delete page(s)")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == a_go:
            self.page_clicked.emit(idx)
        elif chosen == a_rot_l:
            self.rotate_requested.emit(sel, -90)
        elif chosen == a_rot_r:
            self.rotate_requested.emit(sel, 90)
        elif chosen == a_rot_180:
            self.rotate_requested.emit(sel, 180)
        elif chosen == a_insert:
            self.insert_blank_requested.emit(idx)
        elif chosen == a_dup:
            self.duplicate_requested.emit(idx)
        elif chosen == a_extract:
            self.extract_requested.emit(sel)
        elif chosen == a_del:
            self.delete_requested.emit(sel)
