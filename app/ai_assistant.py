"""Local 'AI Assistant' panel - heuristic document analysis without external API calls.

Provides quick answers for common questions like 'Simplify the document for me',
'Summarize this page', 'List all dates', 'Find amounts and totals', etc.
"""
from __future__ import annotations
import os
import re
from collections import Counter
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser,
    QToolButton, QWidget, QSizePolicy
)


SUGGESTIONS = [
    ("Simplify the document for me", "simplify"),
    ("Summarize this page",          "summarize_page"),
    ("Key dates and deadlines",      "find_dates"),
    ("Find all amounts & totals",    "find_amounts"),
    ("List all emails & phones",     "find_contacts"),
    ("Extract addresses",            "find_addresses"),
    ("Word & page counts",           "stats"),
]


def _analyze(text: str, question: str, page_index: int, page_count: int) -> str:
    """Return an HTML answer to a question about the text. No network calls."""
    q = (question or "").lower().strip()
    if not text:
        return "<p>The document has no extractable text on this page.</p>"

    # Common patterns
    DATE = re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{4}-\d{2}-\d{2}"
        r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
        r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+\d{1,2}(?:,\s*\d{4})?)\b", re.I)
    MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d{1,2})?\b|\b[\d,]+(?:\.\d{1,2})?\s*(?:USD|EUR|GBP)\b", re.I)
    EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
    PHONE = re.compile(r"\b(?:\+?\d{1,3}[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")
    ADDR = re.compile(r"\b\d{1,5}\s+\w[\w\s.,#-]+?,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b")

    if "simpl" in q:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if 4 <= len(s.split()) <= 60]
        out = sentences[:8]
        if not out:
            return "<p>Not enough sentence-like content to simplify.</p>"
        bullets = "".join(f"<li>{_escape(s)}</li>" for s in out)
        return f"<p><b>Key points from page {page_index + 1}:</b></p><ul>{bullets}</ul>"

    if "summar" in q:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text)
        if not words:
            return "<p>No words to summarize.</p>"
        stop = set("""this that with from have been they were what when where who which
                      will would could should into them their there about other than then
                      these those some most also more very much such only just both either
                      because while during through without between among under above""".split())
        counter = Counter(w.lower() for w in words if w.lower() not in stop)
        top = counter.most_common(10)
        topics = ", ".join(f"<b>{_escape(w)}</b> ({n})" for w, n in top)
        first = " ".join(text.split()[:60])
        return (f"<p><b>Page {page_index + 1} summary</b></p>"
                f"<p>{_escape(first)}…</p>"
                f"<p><b>Most frequent terms:</b> {topics}</p>")

    if "date" in q or "deadline" in q or "when" in q:
        dates = list(dict.fromkeys(DATE.findall(text)))
        if not dates:
            return "<p>No dates found on this page.</p>"
        return "<p><b>Dates found:</b></p><ul>" + "".join(f"<li>{_escape(d)}</li>" for d in dates[:30]) + "</ul>"

    if "amount" in q or "total" in q or "money" in q or "$" in q or "price" in q or "cost" in q:
        amounts = MONEY.findall(text)
        if not amounts:
            return "<p>No monetary amounts found.</p>"
        # Sort by numeric value descending
        def to_num(s):
            try: return float(re.sub(r"[^\d.]", "", s) or "0")
            except ValueError: return 0
        amounts_sorted = sorted(set(amounts), key=to_num, reverse=True)
        return ("<p><b>Amounts on page " + str(page_index + 1) + ":</b></p><ul>"
                + "".join(f"<li>{_escape(a)}</li>" for a in amounts_sorted[:30]) + "</ul>")

    if "email" in q or "phone" in q or "contact" in q:
        emails = EMAIL.findall(text)
        phones = PHONE.findall(text)
        parts = []
        if emails: parts.append("<p><b>Emails:</b></p><ul>" + "".join(f"<li>{_escape(e)}</li>" for e in set(emails)) + "</ul>")
        if phones: parts.append("<p><b>Phones:</b></p><ul>" + "".join(f"<li>{_escape(p)}</li>" for p in set(phones)) + "</ul>")
        return "".join(parts) or "<p>No contact info found on this page.</p>"

    if "address" in q:
        addrs = ADDR.findall(text)
        if not addrs:
            return "<p>No US-style addresses detected on this page.</p>"
        return "<p><b>Addresses:</b></p><ul>" + "".join(f"<li>{_escape(a)}</li>" for a in addrs) + "</ul>"

    if "stat" in q or "count" in q or "word" in q:
        words = re.findall(r"\b\w+\b", text)
        chars = len(text)
        lines = text.count("\n") + 1
        return (f"<p><b>Statistics for page {page_index + 1}</b></p>"
                f"<ul><li>Pages in document: {page_count}</li>"
                f"<li>Words on this page: {len(words):,}</li>"
                f"<li>Characters: {chars:,}</li>"
                f"<li>Lines: {lines:,}</li></ul>")

    # default: keyword search
    keywords = [w for w in re.findall(r"\b\w{3,}\b", q) if w.isalpha()]
    if keywords:
        hits = []
        for kw in keywords:
            for match in re.finditer(r"\b" + re.escape(kw) + r"\b", text, re.I):
                s = max(0, match.start() - 40); e = min(len(text), match.end() + 60)
                hits.append("…" + text[s:e].replace("\n", " ") + "…")
                if len(hits) >= 8: break
        if hits:
            return "<p><b>Found:</b></p><ul>" + "".join(f"<li>{_escape(h)}</li>" for h in hits[:8]) + "</ul>"
    return "<p>I couldn't find a specific answer. Try one of the suggested prompts below.</p>"


def _escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class AiAssistantPanel(QFrame):
    """A bottom-attached or right-side panel that takes a question and shows a result."""
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AiPanel")
        self.setFixedHeight(220)
        self._get_text: Optional[callable] = None
        self._get_page: Optional[callable] = None
        self._get_total: Optional[callable] = None

        v = QVBoxLayout(self); v.setContentsMargins(12, 8, 12, 8); v.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel(" ✦  AI Assistant"); title.setObjectName("AiTitle")
        title.setStyleSheet("color:#a855f7; font-weight:600;")
        top.addWidget(title)
        top.addStretch(1)
        close = QToolButton(); close.setText("✕"); close.setStyleSheet(
            "QToolButton{background:transparent; color:#a3a3a3; border:none; padding:4px;}"
            "QToolButton:hover{background:#363636; border-radius:3px; color:#f5f5f5;}")
        close.clicked.connect(self.closed.emit)
        top.addWidget(close)
        v.addLayout(top)

        # suggestion chips
        chip_row = QHBoxLayout(); chip_row.setSpacing(6)
        for label, _ in SUGGESTIONS[:5]:
            b = QPushButton(label); b.setObjectName("AiSuggestion")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, t=label: self._ask(t))
            chip_row.addWidget(b)
        chip_row.addStretch(1)
        v.addLayout(chip_row)

        # output area
        self.output = QTextBrowser(); self.output.setObjectName("AiOutput")
        self.output.setOpenExternalLinks(False)
        self.output.setHtml("<p style='color:#a3a3a3;'>Ask a question about this document, "
                            "or click one of the suggestions above.</p>")
        v.addWidget(self.output, 1)

        # input row
        h = QHBoxLayout(); h.setSpacing(6)
        self.input = QLineEdit(); self.input.setObjectName("AiInput")
        self.input.setPlaceholderText("Simplify the document for me")
        self.input.returnPressed.connect(self._submit)
        h.addWidget(self.input, 1)
        send = QPushButton("Send"); send.setObjectName("AiSubmit")
        send.clicked.connect(self._submit)
        h.addWidget(send)
        v.addLayout(h)

    def set_text_provider(self, get_text_fn, get_page_fn, get_total_fn):
        """fn() returns: text-of-current-page / 0-indexed page / total pages."""
        self._get_text = get_text_fn
        self._get_page = get_page_fn
        self._get_total = get_total_fn

    def _submit(self):
        q = self.input.text().strip()
        if q: self._ask(q)
        self.input.clear()

    def _ask(self, question: str):
        if not self._get_text:
            return
        try:
            text = self._get_text() or ""
            page = self._get_page() or 0
            total = self._get_total() or 1
        except Exception:
            text, page, total = "", 0, 1
        self.output.setHtml(_analyze(text, question, page, total))
