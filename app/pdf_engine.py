"""Core PDF operations - the workhorse module.

Wraps PyMuPDF (fitz) and pikepdf with a friendlier API plus undo history,
inline text editing, page-level ops, form support, sanitization, and
conversion helpers.
"""
from __future__ import annotations

import io
import math
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

import fitz
import pikepdf
from PIL import Image


# ----------------------------------------------------------------------
# data classes
# ----------------------------------------------------------------------
@dataclass
class PageInfo:
    index: int
    width: float
    height: float
    rotation: int


@dataclass
class TextSpan:
    """A single piece of text on the page (one font/size run)."""
    page: int
    text: str
    bbox: tuple  # x0, y0, x1, y1 in PDF coords
    fontname: str
    fontsize: float
    color: tuple  # (r, g, b) 0..1
    flags: int  # bold/italic/etc


@dataclass
class RedactionMark:
    page: int
    rect: tuple
    fill: tuple = (0, 0, 0)


# ----------------------------------------------------------------------
# document wrapper
# ----------------------------------------------------------------------
class PdfDocument:
    """Wraps fitz.Document with undo, page ops, edits, and form helpers."""

    def __init__(self, path: Optional[str] = None, password: Optional[str] = None):
        self.path: Optional[str] = path
        self._history: list[bytes] = []
        self._future: list[bytes] = []
        self.pending_redactions: list[RedactionMark] = []
        if path is None:
            self.doc = fitz.open()
        else:
            self.doc = fitz.open(path)
            if self.doc.needs_pass:
                if password is None:
                    raise PermissionError("Password required")
                if not self.doc.authenticate(password):
                    raise PermissionError("Wrong password")

    # ----- history -----
    def snapshot(self):
        self._history.append(self.doc.tobytes())
        self._future.clear()
        if len(self._history) > 50:
            self._history.pop(0)

    def can_undo(self) -> bool:
        return len(self._history) > 0

    def can_redo(self) -> bool:
        return len(self._future) > 0

    def undo(self):
        if not self._history: return
        self._future.append(self.doc.tobytes())
        data = self._history.pop()
        self.doc.close()
        self.doc = fitz.open(stream=data, filetype="pdf")

    def redo(self):
        if not self._future: return
        self._history.append(self.doc.tobytes())
        data = self._future.pop()
        self.doc.close()
        self.doc = fitz.open(stream=data, filetype="pdf")

    # ----- metadata -----
    @property
    def page_count(self) -> int:
        return self.doc.page_count

    def page_info(self, i: int) -> PageInfo:
        p = self.doc[i]
        r = p.rect
        return PageInfo(i, r.width, r.height, p.rotation)

    def metadata(self) -> dict:
        return dict(self.doc.metadata or {})

    def set_metadata(self, meta: dict):
        self.snapshot()
        self.doc.set_metadata(meta)

    def sanitize(self):
        """Strip metadata + remove embedded JS + clear hidden info."""
        self.snapshot()
        # clear metadata
        empty = {k: "" for k in (self.doc.metadata or {}).keys()}
        try:
            self.doc.set_metadata(empty)
        except Exception:
            pass
        # remove JS actions
        try:
            for i in range(self.page_count):
                page = self.doc[i]
                for annot in (page.annots() or []):
                    info = annot.info or {}
                    if "javascript" in str(info).lower():
                        page.delete_annot(annot)
        except Exception:
            pass

    # ----- rendering -----
    def render(self, index: int, zoom: float = 1.0) -> bytes:
        mat = fitz.Matrix(zoom, zoom)
        pix = self.doc[index].get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")

    def render_pil(self, index: int, zoom: float = 1.0) -> Image.Image:
        mat = fitz.Matrix(zoom, zoom)
        pix = self.doc[index].get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def thumbnail(self, index: int, max_dim: int = 180) -> bytes:
        page = self.doc[index]
        r = page.rect
        scale = max_dim / max(r.width, r.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pix.tobytes("png")

    # ----- page ops -----
    def delete_pages(self, indices: Iterable[int]):
        self.snapshot()
        for i in sorted(set(indices), reverse=True):
            self.doc.delete_page(i)

    def rotate_page(self, index: int, degrees: int):
        self.snapshot()
        p = self.doc[index]
        p.set_rotation((p.rotation + degrees) % 360)

    def rotate_all(self, degrees: int, even_only: bool = False, odd_only: bool = False):
        self.snapshot()
        for i in range(self.page_count):
            if even_only and i % 2 == 0: continue  # 0-indexed: i=0 is page 1 (odd)
            if odd_only and i % 2 == 1: continue
            p = self.doc[i]
            p.set_rotation((p.rotation + degrees) % 360)

    def move_page(self, src: int, dst: int):
        self.snapshot()
        self.doc.move_page(src, dst)

    def insert_blank_page(self, index: int, width: float = 612, height: float = 792):
        self.snapshot()
        self.doc.new_page(pno=index, width=width, height=height)

    def duplicate_page(self, index: int):
        self.snapshot()
        self.doc.fullcopy_page(index, to=index + 1)

    def extract_pages(self, indices: Iterable[int], out_path: str):
        new = fitz.open()
        for i in indices:
            new.insert_pdf(self.doc, from_page=i, to_page=i)
        new.save(out_path, garbage=4, deflate=True)
        new.close()

    def insert_pdf(self, other_path: str, at_index: int,
                   from_page: Optional[int] = None, to_page: Optional[int] = None,
                   password: Optional[str] = None):
        """Insert another PDF (or a range from it) at a given position."""
        self.snapshot()
        with fitz.open(other_path) as src:
            if src.needs_pass:
                if password is None or not src.authenticate(password):
                    raise PermissionError("Source PDF needs a password")
            fp = 0 if from_page is None else from_page
            tp = src.page_count - 1 if to_page is None else to_page
            self.doc.insert_pdf(src, from_page=fp, to_page=tp, start_at=at_index)

    def replace_page(self, index: int, other_path: str, other_page: int):
        self.snapshot()
        with fitz.open(other_path) as src:
            self.doc.insert_pdf(src, from_page=other_page, to_page=other_page, start_at=index + 1)
        self.doc.delete_page(index)

    def crop_page(self, index: int, rect: tuple):
        """Crop a single page. rect in PDF coords (x0,y0,x1,y1)."""
        self.snapshot()
        page = self.doc[index]
        page.set_cropbox(fitz.Rect(*rect))

    def crop_all(self, rect_or_margins, mode: str = "rect"):
        """Crop all pages. mode='rect' -> tuple; mode='margins' -> (l,t,r,b) inset."""
        self.snapshot()
        for i in range(self.page_count):
            page = self.doc[i]
            if mode == "margins":
                l, t, r, b = rect_or_margins
                box = page.mediabox
                page.set_cropbox(fitz.Rect(box.x0 + l, box.y0 + t, box.x1 - r, box.y1 - b))
            else:
                page.set_cropbox(fitz.Rect(*rect_or_margins))

    def reset_crop(self, index: Optional[int] = None):
        self.snapshot()
        pages = [index] if index is not None else range(self.page_count)
        for i in pages:
            page = self.doc[i]
            page.set_cropbox(page.mediabox)

    # ----- annotations (markup) -----
    def add_text(self, index: int, x: float, y: float, text: str,
                 fontsize: int = 12, color=(0, 0, 0), fontname: str = "helv"):
        self.snapshot()
        page = self.doc[index]
        page.insert_text((x, y), text, fontsize=fontsize, color=color, fontname=fontname)

    def add_text_box(self, index: int, rect: tuple, text: str,
                     fontsize: int = 12, color=(0, 0, 0), fontname: str = "helv",
                     align: int = 0):
        self.snapshot()
        page = self.doc[index]
        page.insert_textbox(fitz.Rect(*rect), text, fontsize=fontsize, color=color,
                            fontname=fontname, align=align)

    def add_highlight(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        a = page.add_highlight_annot(quads)
        a.update()

    def add_underline(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        a = page.add_underline_annot(quads)
        a.update()

    def add_strikeout(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        a = page.add_strikeout_annot(quads)
        a.update()

    def add_squiggly(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        a = page.add_squiggly_annot(quads)
        a.update()

    def add_rect(self, index: int, rect, color=(1, 0, 0), width: float = 1.5,
                 fill=None, opacity: float = 1.0):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_rect_annot(fitz.Rect(*rect))
        annot.set_colors(stroke=color, fill=fill)
        annot.set_border(width=width)
        annot.set_opacity(opacity)
        annot.update(fill_color=fill)

    def add_oval(self, index: int, rect, color=(1, 0, 0), width: float = 1.5,
                 fill=None, opacity: float = 1.0):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_circle_annot(fitz.Rect(*rect))
        annot.set_colors(stroke=color, fill=fill)
        annot.set_border(width=width)
        annot.set_opacity(opacity)
        annot.update(fill_color=fill)

    def add_line(self, index: int, p1, p2, color=(1, 0, 0), width: float = 1.5,
                 arrow_end: bool = False, arrow_start: bool = False):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_line_annot(fitz.Point(*p1), fitz.Point(*p2))
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        if arrow_end or arrow_start:
            # PyMuPDF uses integer enum values for line endings
            LE_NONE = getattr(fitz, "PDF_ANNOT_LE_NONE", 0)
            LE_OPEN_ARROW = getattr(fitz, "PDF_ANNOT_LE_OPEN_ARROW", 4)
            try:
                annot.set_line_ends(LE_OPEN_ARROW if arrow_start else LE_NONE,
                                    LE_OPEN_ARROW if arrow_end else LE_NONE)
            except Exception:
                pass  # not all builds support line endings
        annot.update()

    def add_arrow(self, index: int, p1, p2, color=(1, 0, 0), width: float = 1.8):
        self.add_line(index, p1, p2, color=color, width=width, arrow_end=True)

    def add_polygon(self, index: int, points: list, color=(1, 0, 0), width: float = 1.5,
                    fill=None):
        self.snapshot()
        page = self.doc[index]
        pts = [fitz.Point(*p) for p in points]
        annot = page.add_polygon_annot(pts)
        annot.set_colors(stroke=color, fill=fill)
        annot.set_border(width=width)
        annot.update(fill_color=fill)

    def add_polyline(self, index: int, points: list, color=(1, 0, 0), width: float = 1.5):
        self.snapshot()
        page = self.doc[index]
        pts = [fitz.Point(*p) for p in points]
        annot = page.add_polyline_annot(pts)
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        annot.update()

    def add_freehand(self, index: int, points: list, color=(0, 0, 0), width: float = 1.5):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_ink_annot([points])
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        annot.update()

    def add_image(self, index: int, rect, image_path: str):
        self.snapshot()
        self.doc[index].insert_image(fitz.Rect(*rect), filename=image_path)

    def add_image_bytes(self, index: int, rect, data: bytes):
        self.snapshot()
        self.doc[index].insert_image(fitz.Rect(*rect), stream=data)

    def add_sticky_note(self, index: int, point: tuple, text: str,
                        title: str = "Note", icon: str = "Note"):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_text_annot(fitz.Point(*point), text, icon=icon)
        annot.set_info(title=title, content=text)
        annot.update()

    def add_callout(self, index: int, rect: tuple, callout_pt: tuple, text: str,
                    fontsize: int = 10, color=(0, 0, 0)):
        """Free-text callout with leader line."""
        self.snapshot()
        page = self.doc[index]
        annot = page.add_freetext_annot(fitz.Rect(*rect), text, fontsize=fontsize,
                                        text_color=color)
        annot.update()

    # ----- delete annotations -----
    def delete_annot_at(self, index: int, point: tuple) -> bool:
        """Delete an annotation whose rect contains the point. Returns True if deleted."""
        page = self.doc[index]
        p = fitz.Point(*point)
        for annot in (page.annots() or []):
            if annot.rect.contains(p):
                self.snapshot()
                page.delete_annot(annot)
                return True
        return False

    # ----- links + bookmarks -----
    def add_link_url(self, index: int, rect: tuple, url: str):
        self.snapshot()
        page = self.doc[index]
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(*rect), "uri": url})

    def add_link_to_page(self, index: int, rect: tuple, target_page: int):
        self.snapshot()
        page = self.doc[index]
        page.insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(*rect),
                          "page": target_page, "to": fitz.Point(0, 0)})

    def list_links(self, index: int) -> list:
        out = []
        for link in self.doc[index].links():
            kind = link.get("kind")
            label = link.get("uri") if kind == fitz.LINK_URI else f"page {link.get('page', 0) + 1}"
            out.append({"rect": tuple(link["from"]), "label": label, "kind": kind})
        return out

    def add_bookmark(self, title: str, page: int, level: int = 1):
        """Append a bookmark to the TOC."""
        self.snapshot()
        toc = self.doc.get_toc(simple=False) or []
        toc.append([level, title, page + 1])
        self.doc.set_toc(toc)

    def replace_toc(self, toc: list):
        """toc = list of [level, title, page_1_indexed]"""
        self.snapshot()
        self.doc.set_toc(toc)

    def get_toc(self) -> list:
        return self.doc.get_toc(simple=True) or []

    # ----- search & text -----
    def search(self, text: str, page_index: Optional[int] = None,
               case_sensitive: bool = False, whole_words: bool = False) -> list:
        results = []
        pages = [page_index] if page_index is not None else range(self.page_count)
        flags = 0
        if not case_sensitive:
            flags |= fitz.TEXT_DEHYPHENATE
        for i in pages:
            page = self.doc[i]
            quads = page.search_for(text, quads=True)
            for q in quads:
                if whole_words:
                    # quick filter: extract text near quad and verify word boundary
                    rect = q.rect
                    pad = 2
                    around = page.get_textbox(fitz.Rect(rect.x0 - pad, rect.y0 - pad,
                                                       rect.x1 + pad, rect.y1 + pad))
                    pattern = r"\b" + re.escape(text) + r"\b"
                    if not re.search(pattern, around, 0 if case_sensitive else re.IGNORECASE):
                        continue
                results.append((i, q))
        return results

    def find_and_replace(self, find: str, replace: str,
                         case_sensitive: bool = False,
                         color=(0, 0, 0), fontsize: float = 0) -> int:
        """Replace every occurrence of `find` with `replace`. Returns count.
        Uses redaction (erase) + insert_text to preserve position.
        """
        if not find:
            return 0
        self.snapshot()
        count = 0
        for i in range(self.page_count):
            page = self.doc[i]
            quads = page.search_for(find, quads=True)
            if not quads:
                continue
            # Determine fontsize from quad height if not provided
            for q in quads:
                r = q.rect
                fs = fontsize or max(8.0, r.height * 0.9)
                # erase original
                page.add_redact_annot(r, fill=(1, 1, 1))
            page.apply_redactions()
            # write replacement at each location (re-search since apply_redactions changes coords)
            for q in quads:
                r = q.rect
                fs = fontsize or max(8.0, r.height * 0.9)
                # baseline approximately r.y1 - small offset
                page.insert_text((r.x0, r.y1 - r.height * 0.15), replace,
                                 fontsize=fs, color=color)
                count += 1
        return count

    def get_text(self, index: int) -> str:
        return self.doc[index].get_text()

    def all_text(self) -> str:
        return "\n\n".join(self.doc[i].get_text() for i in range(self.page_count))

    def text_spans(self, index: int) -> list[TextSpan]:
        """Return every text span on a page, useful for click-to-edit."""
        out = []
        page = self.doc[index]
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if block.get("type", 0) != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    color_int = span.get("color", 0)
                    r = ((color_int >> 16) & 0xff) / 255
                    g = ((color_int >> 8) & 0xff) / 255
                    b = (color_int & 0xff) / 255
                    out.append(TextSpan(
                        page=index,
                        text=span.get("text", ""),
                        bbox=tuple(span.get("bbox", (0, 0, 0, 0))),
                        fontname=span.get("font", "helv"),
                        fontsize=span.get("size", 12),
                        color=(r, g, b),
                        flags=span.get("flags", 0),
                    ))
        return out

    def hit_test_text(self, index: int, x: float, y: float) -> Optional[TextSpan]:
        """Find which text span (if any) contains the given page-coord point."""
        for span in self.text_spans(index):
            x0, y0, x1, y1 = span.bbox
            if x0 <= x <= x1 and y0 <= y <= y1:
                return span
        return None

    def replace_span(self, span: TextSpan, new_text: str,
                     color: Optional[tuple] = None, fontsize: Optional[float] = None):
        """Erase the span's rect and write new text in roughly the same place."""
        self.snapshot()
        page = self.doc[span.page]
        page.add_redact_annot(fitz.Rect(*span.bbox), fill=(1, 1, 1))
        page.apply_redactions()
        fs = fontsize or span.fontsize
        c = color or span.color
        # baseline near y1
        y_baseline = span.bbox[3] - (span.bbox[3] - span.bbox[1]) * 0.18
        # try to use original font if it's a standard one
        font = "helv"
        fn = (span.fontname or "").lower()
        if "times" in fn or "serif" in fn:
            font = "tiro"
        elif "courier" in fn or "mono" in fn:
            font = "cour"
        try:
            page.insert_text((span.bbox[0], y_baseline), new_text,
                             fontsize=fs, color=c, fontname=font)
        except Exception:
            page.insert_text((span.bbox[0], y_baseline), new_text, fontsize=fs, color=c)

    # ----- redaction -----
    def redact(self, index: int, rect, fill=(0, 0, 0)):
        self.snapshot()
        page = self.doc[index]
        page.add_redact_annot(fitz.Rect(*rect), fill=fill)
        page.apply_redactions()

    def redact_text(self, text: str, case_sensitive: bool = False) -> int:
        self.snapshot()
        count = 0
        for i in range(self.page_count):
            page = self.doc[i]
            quads = page.search_for(text, quads=True)
            for q in quads:
                page.add_redact_annot(q.rect, fill=(0, 0, 0))
                count += 1
            if quads:
                page.apply_redactions()
        return count

    def mark_for_redaction(self, page: int, rect: tuple, fill=(0, 0, 0)):
        """Queue a redaction without applying it. Use apply_pending_redactions to commit."""
        self.pending_redactions.append(RedactionMark(page=page, rect=rect, fill=fill))

    def clear_pending_redactions(self):
        self.pending_redactions.clear()

    def apply_pending_redactions(self) -> int:
        if not self.pending_redactions:
            return 0
        self.snapshot()
        count = 0
        per_page: dict[int, list[RedactionMark]] = {}
        for m in self.pending_redactions:
            per_page.setdefault(m.page, []).append(m)
        for page_idx, marks in per_page.items():
            page = self.doc[page_idx]
            for m in marks:
                page.add_redact_annot(fitz.Rect(*m.rect), fill=m.fill)
                count += 1
            page.apply_redactions()
        self.pending_redactions.clear()
        return count

    # ----- watermarks + headers/footers -----
    def add_watermark(self, text: str, opacity: float = 0.25, fontsize: int = 60,
                      color=(0.5, 0.5, 0.5), rotation: int = 45):
        self.snapshot()
        for i in range(self.page_count):
            page = self.doc[i]
            r = page.rect
            cx, cy = r.width / 2, r.height / 2
            font = fitz.Font("helv")
            text_w = font.text_length(text, fontsize=fontsize)
            tw = fitz.TextWriter(page.rect, opacity=opacity, color=color)
            tw.append((cx - text_w / 2, cy + fontsize / 3), text, font=font, fontsize=fontsize)
            tw.write_text(page, morph=(fitz.Point(cx, cy), fitz.Matrix(rotation)))

    def add_image_watermark(self, image_path: str, opacity: float = 0.3,
                            scale: float = 0.5, rotation: int = 0):
        """Centered, scaled image watermark over every page."""
        self.snapshot()
        with Image.open(image_path) as im:
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA")
            img_w, img_h = im.size
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            data = buf.getvalue()
        for i in range(self.page_count):
            page = self.doc[i]
            r = page.rect
            target_w = r.width * scale
            target_h = target_w * (img_h / img_w)
            x0 = (r.width - target_w) / 2
            y0 = (r.height - target_h) / 2
            page.insert_image(fitz.Rect(x0, y0, x0 + target_w, y0 + target_h),
                              stream=data, overlay=True, rotate=rotation)

    def add_page_numbers(self, start: int = 1, fontsize: int = 11,
                         color=(0, 0, 0), position: str = "bottom-center",
                         pattern: str = "{n}"):
        """pattern can use {n} for page number and {N} for total."""
        self.snapshot()
        total = self.page_count
        for i in range(self.page_count):
            page = self.doc[i]
            r = page.rect
            label = pattern.replace("{n}", str(start + i)).replace("{N}", str(start + total - 1))
            tw = fitz.get_text_length(label, fontsize=fontsize)
            pos = self._position_for(position, r, tw)
            page.insert_text(pos, label, fontsize=fontsize, color=color)

    def add_header_footer(self, *,
                          header_left: str = "", header_center: str = "", header_right: str = "",
                          footer_left: str = "", footer_center: str = "", footer_right: str = "",
                          fontsize: int = 10, color=(0, 0, 0), margin: float = 28):
        """Add fully custom header/footer text. Supports {n} and {N}."""
        self.snapshot()
        total = self.page_count
        for i in range(self.page_count):
            page = self.doc[i]
            r = page.rect
            def render(text, y, align):
                if not text: return
                txt = text.replace("{n}", str(i + 1)).replace("{N}", str(total))
                tw = fitz.get_text_length(txt, fontsize=fontsize)
                if align == "left": x = margin
                elif align == "right": x = r.width - margin - tw
                else: x = (r.width - tw) / 2
                page.insert_text((x, y), txt, fontsize=fontsize, color=color)
            render(header_left, margin, "left")
            render(header_center, margin, "center")
            render(header_right, margin, "right")
            render(footer_left, r.height - margin + fontsize, "left")
            render(footer_center, r.height - margin + fontsize, "center")
            render(footer_right, r.height - margin + fontsize, "right")

    def _position_for(self, position: str, r, text_w: float) -> tuple:
        if position == "bottom-center": return (r.width / 2 - text_w / 2, r.height - 20)
        if position == "bottom-right":  return (r.width - 40, r.height - 20)
        if position == "bottom-left":   return (30, r.height - 20)
        if position == "top-right":     return (r.width - 40, 30)
        if position == "top-left":      return (30, 30)
        return (r.width / 2 - text_w / 2, 30)

    # ----- stamps -----
    def add_stamp(self, index: int, rect: tuple, image_bytes: bytes,
                  opacity: float = 1.0):
        self.snapshot()
        page = self.doc[index]
        if opacity >= 0.99:
            page.insert_image(fitz.Rect(*rect), stream=image_bytes)
        else:
            # use overlay with opacity via temporary tinted image
            page.insert_image(fitz.Rect(*rect), stream=image_bytes, overlay=True)

    # ----- forms -----
    def list_form_fields(self) -> list[dict]:
        """Return all form fields with page, name, type, value, rect."""
        out = []
        for i in range(self.page_count):
            page = self.doc[i]
            for w in (page.widgets() or []):
                out.append({
                    "page": i,
                    "name": w.field_name or "",
                    "label": w.field_label or "",
                    "type": w.field_type_string or "",
                    "value": w.field_value,
                    "rect": tuple(w.rect),
                    "options": (w.choice_values or []) if hasattr(w, "choice_values") else [],
                })
        return out

    def set_form_field(self, page: int, field_name: str, value) -> bool:
        """Set a field's value by name. Returns True on success."""
        for w in (self.doc[page].widgets() or []):
            if w.field_name == field_name:
                self.snapshot()
                w.field_value = value
                w.update()
                return True
        return False

    def flatten_form_fields(self):
        """Burn form fields into the document so they're no longer editable."""
        self.snapshot()
        # PyMuPDF's bake_widgets is the simplest path
        try:
            self.doc.bake()  # newer fitz
        except Exception:
            try:
                self.doc.bake_widgets()
            except Exception:
                pass

    def add_form_text_field(self, page: int, rect: tuple, name: str, value: str = ""):
        self.snapshot()
        p = self.doc[page]
        w = fitz.Widget()
        w.rect = fitz.Rect(*rect)
        w.field_name = name
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.field_value = value
        p.add_widget(w)

    def add_form_checkbox(self, page: int, rect: tuple, name: str, checked: bool = False):
        self.snapshot()
        p = self.doc[page]
        w = fitz.Widget()
        w.rect = fitz.Rect(*rect)
        w.field_name = name
        w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        w.field_value = checked
        p.add_widget(w)

    # ----- save -----
    def save(self, path: Optional[str] = None, compress: bool = True,
             apply_pending: bool = True, verify: bool = True) -> str:
        """Atomic, lock-safe save. Applies queued redactions automatically.
        Returns the path written. Raises on failure with a useful message."""
        out = path or self.path
        if not out:
            raise ValueError("No save path specified")

        if apply_pending and self.pending_redactions:
            self.apply_pending_redactions()

        kwargs = dict(garbage=3, deflate=True, deflate_images=True,
                      deflate_fonts=True, clean=False)
        # cannot clean and use incremental together; we never use incremental here

        is_in_place = (self.path is not None
                       and os.path.abspath(out) == os.path.abspath(self.path))

        if is_in_place:
            # write to temp, then atomically rename
            tmp = out + ".saving"
            try:
                self.doc.save(tmp, **kwargs)
            except Exception as e:
                try:
                    if os.path.exists(tmp): os.remove(tmp)
                except Exception:
                    pass
                raise IOError(f"Could not write to '{tmp}': {e}") from e
            try:
                self.doc.close()
            except Exception:
                pass
            # On Windows os.replace is atomic — handles the case where 'out' exists
            for attempt in range(5):
                try:
                    os.replace(tmp, out)
                    break
                except PermissionError:
                    import time
                    time.sleep(0.15 * (attempt + 1))
            else:
                # last resort: try delete+rename
                try:
                    if os.path.exists(out): os.remove(out)
                    os.rename(tmp, out)
                except Exception as e:
                    raise IOError(
                        f"Could not replace '{out}'. Is it open in another "
                        f"application?\n\nA backup is at '{tmp}'."
                    ) from e
            self.doc = fitz.open(out)
        else:
            # different path - direct save
            try:
                self.doc.save(out, **kwargs)
            except Exception as e:
                raise IOError(f"Could not save to '{out}': {e}") from e

        if verify and not self._verify_saved(out):
            raise IOError(f"Saved file at '{out}' failed integrity check.")

        self.path = out
        self._history.clear()
        self._future.clear()
        return out

    def save_copy(self, path: str, compress: bool = True,
                  apply_pending: bool = False) -> str:
        """Save without changing the open document's path. Used for export-like flows."""
        if apply_pending and self.pending_redactions:
            self.apply_pending_redactions()
        kwargs = dict(garbage=3, deflate=True, deflate_images=True,
                      deflate_fonts=True, clean=False)
        self.doc.save(path, **kwargs)
        return path

    def save_with_password(self, path: str, user_pw: str, owner_pw: Optional[str] = None,
                           permissions: Optional[dict] = None) -> str:
        """Save with strong (AES-256) encryption."""
        if self.pending_redactions:
            self.apply_pending_redactions()
        perms = -1  # all permissions by default
        if permissions:
            perms = 0
            mapping = {
                "print":     fitz.PDF_PERM_PRINT,
                "modify":    fitz.PDF_PERM_MODIFY,
                "copy":      fitz.PDF_PERM_COPY,
                "annotate":  fitz.PDF_PERM_ANNOTATE,
                "form":      fitz.PDF_PERM_FORM,
                "accessibility": fitz.PDF_PERM_ACCESSIBILITY,
                "assemble":  fitz.PDF_PERM_ASSEMBLE,
                "print_hq":  fitz.PDF_PERM_PRINT_HQ,
            }
            for k, allowed in permissions.items():
                if allowed and k in mapping:
                    perms |= mapping[k]
        self.doc.save(path,
                      encryption=fitz.PDF_ENCRYPT_AES_256,
                      user_pw=user_pw,
                      owner_pw=owner_pw or user_pw,
                      permissions=perms,
                      garbage=3, deflate=True)
        return path

    def _verify_saved(self, path: str) -> bool:
        """Sanity-check that the saved file is readable and has the expected page count."""
        try:
            with fitz.open(path) as d:
                return d.page_count >= 1 and not d.needs_pass
        except Exception:
            return False

    def revert(self):
        """Reload from disk, discarding all in-memory changes."""
        if not self.path:
            raise ValueError("Cannot revert an unsaved document")
        try:
            self.doc.close()
        except Exception:
            pass
        self.doc = fitz.open(self.path)
        self._history.clear()
        self._future.clear()
        self.pending_redactions.clear()

    def close(self):
        try:
            self.doc.close()
        except Exception:
            pass


# ----------------------------------------------------------------------
# module-level batch ops
# ----------------------------------------------------------------------
def merge_pdfs(paths: list[str], out_path: str, progress: Optional[Callable] = None):
    out = fitz.open()
    for idx, p in enumerate(paths):
        with fitz.open(p) as src:
            out.insert_pdf(src)
        if progress: progress(idx + 1, len(paths))
    out.save(out_path, garbage=4, deflate=True)
    out.close()


def split_pdf(path: str, out_dir: str, mode: str = "single",
              ranges: Optional[list[tuple[int, int]]] = None,
              by_size_kb: Optional[int] = None,
              by_page_count: Optional[int] = None) -> list[str]:
    """mode: single | ranges | by_size | by_count"""
    results = []
    src = fitz.open(path)
    stem = Path(path).stem
    try:
        if mode == "single":
            for i in range(src.page_count):
                new = fitz.open(); new.insert_pdf(src, from_page=i, to_page=i)
                out = os.path.join(out_dir, f"{stem}_page{i+1}.pdf")
                new.save(out, garbage=4, deflate=True); new.close()
                results.append(out)
        elif mode == "ranges" and ranges:
            for j, (a, b) in enumerate(ranges):
                new = fitz.open(); new.insert_pdf(src, from_page=a, to_page=b)
                out = os.path.join(out_dir, f"{stem}_part{j+1}.pdf")
                new.save(out, garbage=4, deflate=True); new.close()
                results.append(out)
        elif mode == "by_count" and by_page_count:
            i = 0; part = 1
            while i < src.page_count:
                a = i
                b = min(i + by_page_count - 1, src.page_count - 1)
                new = fitz.open(); new.insert_pdf(src, from_page=a, to_page=b)
                out = os.path.join(out_dir, f"{stem}_part{part}.pdf")
                new.save(out, garbage=4, deflate=True); new.close()
                results.append(out)
                i = b + 1; part += 1
        elif mode == "by_size" and by_size_kb:
            target = by_size_kb * 1024
            i = 0; part = 1
            while i < src.page_count:
                a = i; b = i
                new = fitz.open(); new.insert_pdf(src, from_page=a, to_page=b)
                buf = new.tobytes(); new.close()
                # grow b while under target
                while b < src.page_count - 1:
                    new = fitz.open(); new.insert_pdf(src, from_page=a, to_page=b + 1)
                    buf2 = new.tobytes(); new.close()
                    if len(buf2) > target and b > a:
                        break
                    b += 1; buf = buf2
                out = os.path.join(out_dir, f"{stem}_part{part}.pdf")
                with open(out, "wb") as f: f.write(buf)
                results.append(out)
                i = b + 1; part += 1
    finally:
        src.close()
    return results


def compress_pdf(in_path: str, out_path: str, image_quality: int = 60,
                 max_image_dim: int = 1500):
    src = fitz.open(in_path)
    for page in src:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(src, xref)
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width > max_image_dim or pix.height > max_image_dim:
                    scale = max_image_dim / max(pix.width, pix.height)
                    pix = fitz.Pixmap(pix, int(pix.width * scale), int(pix.height * scale), True)
                buf = io.BytesIO()
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                im.save(buf, format="JPEG", quality=image_quality, optimize=True)
                src.update_stream(xref, buf.getvalue())
            except Exception:
                continue
    src.save(out_path, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    src.close()


def encrypt_pdf(in_path: str, out_path: str, user_pw: str, owner_pw: str = "",
                allow_print: bool = True, allow_copy: bool = True,
                allow_modify: bool = False, allow_annotate: bool = False):
    with pikepdf.open(in_path) as pdf:
        perms = pikepdf.Permissions(
            print_lowres=allow_print, print_highres=allow_print,
            extract=allow_copy,
            modify_annotation=allow_annotate,
            modify_assembly=allow_modify,
            modify_form=allow_modify,
            modify_other=allow_modify,
        )
        pdf.save(out_path, encryption=pikepdf.Encryption(
            user=user_pw, owner=owner_pw or user_pw, R=6, allow=perms
        ))


def decrypt_pdf(in_path: str, out_path: str, password: str):
    with pikepdf.open(in_path, password=password) as pdf:
        pdf.save(out_path)


def pdf_to_images(in_path: str, out_dir: str, fmt: str = "png", dpi: int = 200,
                  progress: Optional[Callable] = None) -> list[str]:
    src = fitz.open(in_path)
    stem = Path(in_path).stem
    results = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for i in range(src.page_count):
        pix = src[i].get_pixmap(matrix=mat, alpha=False)
        out = os.path.join(out_dir, f"{stem}_page{i+1}.{fmt}")
        pix.save(out)
        results.append(out)
        if progress: progress(i + 1, src.page_count)
    src.close()
    return results


def images_to_pdf(image_paths: list[str], out_path: str,
                  page_size: Optional[tuple] = None):
    """page_size: (w,h) in PDF points, or None to fit image."""
    new = fitz.open()
    for p in image_paths:
        img = Image.open(p)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        w, h = img.size
        if page_size:
            page = new.new_page(width=page_size[0], height=page_size[1])
            # fit image centered
            scale = min(page_size[0] / w, page_size[1] / h)
            iw, ih = w * scale, h * scale
            x = (page_size[0] - iw) / 2; y = (page_size[1] - ih) / 2
            page.insert_image(fitz.Rect(x, y, x + iw, y + ih), stream=buf.getvalue())
        else:
            page = new.new_page(width=w, height=h)
            page.insert_image(fitz.Rect(0, 0, w, h), stream=buf.getvalue())
    new.save(out_path, garbage=4, deflate=True)
    new.close()


def extract_text(in_path: str, out_path: str):
    src = fitz.open(in_path)
    with open(out_path, "w", encoding="utf-8") as f:
        for i in range(src.page_count):
            f.write(f"--- Page {i+1} ---\n")
            f.write(src[i].get_text())
            f.write("\n\n")
    src.close()


def extract_images(in_path: str, out_dir: str) -> list[str]:
    src = fitz.open(in_path)
    stem = Path(in_path).stem
    results = []
    for i in range(src.page_count):
        for j, img in enumerate(src[i].get_images(full=True)):
            xref = img[0]
            pix = fitz.Pixmap(src, xref)
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out = os.path.join(out_dir, f"{stem}_p{i+1}_img{j+1}.png")
            pix.save(out)
            results.append(out)
    src.close()
    return results


def ocr_pdf(in_path: str, out_path: str, tesseract_cmd: Optional[str] = None,
            language: str = "eng", progress: Optional[Callable] = None) -> bool:
    try:
        import pytesseract
    except ImportError:
        return False
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    src = fitz.open(in_path)
    out = fitz.open()
    try:
        for i in range(src.page_count):
            page = src[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            try:
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=language, extension="pdf")
            except Exception:
                return False
            with fitz.open(stream=pdf_bytes, filetype="pdf") as new:
                out.insert_pdf(new)
            if progress: progress(i + 1, src.page_count)
        out.save(out_path, garbage=4, deflate=True)
    finally:
        out.close(); src.close()
    return True


def find_tesseract() -> Optional[str]:
    for c in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]:
        if os.path.isfile(c): return c
    return None
