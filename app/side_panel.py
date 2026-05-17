"""Left side panel - switches between Pages, Bookmarks, Comments, Attachments."""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QStackedWidget, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QWidget, QPushButton, QPlainTextEdit
)

from .pdf_engine import PdfDocument
from .thumbnails import ThumbnailList


class _EmptyState(QWidget):
    def __init__(self, msg: str, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.addStretch(1)
        l = QLabel(msg); l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("color:#888; padding: 16px;")
        l.setWordWrap(True)
        v.addWidget(l)
        v.addStretch(2)


class BookmarksPanel(QWidget):
    goto_page = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("background:#323232; color:#f0f0f0; border:none; padding:6px;")
        self.tree.itemActivated.connect(self._on_activated)
        self.tree.itemClicked.connect(self._on_activated)
        v.addWidget(self.tree)

    def load(self, doc: Optional[PdfDocument]):
        self.tree.clear()
        if not doc:
            return
        try:
            toc = doc.doc.get_toc()
        except Exception:
            toc = []
        if not toc:
            it = QTreeWidgetItem([" (no bookmarks in this PDF)"])
            it.setDisabled(True)
            self.tree.addTopLevelItem(it)
            return
        stack = [(0, None)]  # (level, parent)
        for level, title, page in toc:
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else None
            it = QTreeWidgetItem([title])
            it.setData(0, Qt.UserRole, page - 1)  # 0-indexed
            if parent is None:
                self.tree.addTopLevelItem(it)
            else:
                parent.addChild(it)
            stack.append((level, it))
        self.tree.expandAll()

    def _on_activated(self, item: QTreeWidgetItem, _col: int = 0):
        page = item.data(0, Qt.UserRole)
        if isinstance(page, int) and page >= 0:
            self.goto_page.emit(page)


class CommentsPanel(QWidget):
    goto_page = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_clicked)
        v.addWidget(self.list, 1)

    def load(self, doc: Optional[PdfDocument]):
        self.list.clear()
        if not doc:
            return
        for i in range(doc.page_count):
            page = doc.doc[i]
            for annot in page.annots() or []:
                text = (annot.info.get("content") or "").strip()
                t = annot.type[1] if annot.type else "annot"
                label = f"Page {i+1} — {t}"
                if text:
                    label += f"\n  {text[:120]}"
                it = QListWidgetItem(label)
                it.setData(Qt.UserRole, i)
                self.list.addItem(it)
        if self.list.count() == 0:
            it = QListWidgetItem(" (no comments)")
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)

    def _on_clicked(self, item):
        page = item.data(Qt.UserRole)
        if isinstance(page, int):
            self.goto_page.emit(page)


class AttachmentsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        self.list = QListWidget()
        v.addWidget(self.list, 1)

    def load(self, doc: Optional[PdfDocument]):
        self.list.clear()
        if not doc:
            return
        try:
            names = doc.doc.embfile_names()
        except Exception:
            names = []
        if not names:
            it = QListWidgetItem(" (no attachments)")
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)
            return
        for n in names:
            self.list.addItem(QListWidgetItem(n))


class SidePanel(QFrame):
    """Stacks pages/bookmarks/comments/attachments views."""
    page_clicked = Signal(int)
    pages_reordered = Signal()
    delete_pages_requested = Signal(list)
    rotate_pages_requested = Signal(list, int)
    duplicate_page_requested = Signal(int)
    extract_pages_requested = Signal(list)
    insert_blank_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidePanel")
        self.setMinimumWidth(220); self.setMaximumWidth(360)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        self.title = QLabel("PAGES"); self.title.setObjectName("PanelTitle")
        outer.addWidget(self.title)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        self.thumbs = ThumbnailList()
        self.thumbs.page_clicked.connect(self.page_clicked.emit)
        self.thumbs.delete_requested.connect(self.delete_pages_requested.emit)
        self.thumbs.rotate_requested.connect(self.rotate_pages_requested.emit)
        self.thumbs.duplicate_requested.connect(self.duplicate_page_requested.emit)
        self.thumbs.extract_requested.connect(self.extract_pages_requested.emit)
        self.thumbs.insert_blank_requested.connect(self.insert_blank_requested.emit)
        self.thumbs.pages_reordered.connect(self.pages_reordered.emit)
        self.stack.addWidget(self.thumbs)              # 0

        self.bookmarks = BookmarksPanel()
        self.bookmarks.goto_page.connect(self.page_clicked.emit)
        self.stack.addWidget(self.bookmarks)           # 1

        self.comments = CommentsPanel()
        self.comments.goto_page.connect(self.page_clicked.emit)
        self.stack.addWidget(self.comments)            # 2

        self.attachments = AttachmentsPanel()
        self.stack.addWidget(self.attachments)         # 3

    def show_panel(self, key: str):
        mapping = {"pages": (0, "PAGES"), "bookmarks": (1, "BOOKMARKS"),
                   "comments": (2, "COMMENTS"), "attachments": (3, "ATTACHMENTS")}
        if key not in mapping:
            return
        idx, title = mapping[key]
        self.stack.setCurrentIndex(idx)
        self.title.setText(title)

    def load_document(self, doc):
        self.thumbs.load(doc)
        self.bookmarks.load(doc)
        self.comments.load(doc)
        self.attachments.load(doc)

    def refresh(self):
        self.thumbs.refresh()
