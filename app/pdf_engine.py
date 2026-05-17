"""Core PDF operations backed by PyMuPDF (fitz) and pikepdf."""
from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

import fitz
import pikepdf
from PIL import Image


@dataclass
class PageInfo:
    index: int
    width: float
    height: float
    rotation: int


class PdfDocument:
    """Wraps a fitz.Document with undo history and convenience ops."""

    def __init__(self, path: Optional[str] = None, password: Optional[str] = None):
        self.path: Optional[str] = path
        self._history: list[bytes] = []
        self._future: list[bytes] = []
        if path is None:
            self.doc = fitz.open()
        else:
            self.doc = fitz.open(path)
            if self.doc.needs_pass:
                if password is None:
                    raise PermissionError("Password required")
                if not self.doc.authenticate(password):
                    raise PermissionError("Wrong password")

    # ------------- history -------------
    def snapshot(self):
        data = self.doc.tobytes()
        self._history.append(data)
        self._future.clear()
        if len(self._history) > 50:
            self._history.pop(0)

    def can_undo(self) -> bool:
        return len(self._history) > 0

    def can_redo(self) -> bool:
        return len(self._future) > 0

    def undo(self):
        if not self._history:
            return
        cur = self.doc.tobytes()
        self._future.append(cur)
        data = self._history.pop()
        self.doc.close()
        self.doc = fitz.open(stream=data, filetype="pdf")

    def redo(self):
        if not self._future:
            return
        cur = self.doc.tobytes()
        self._history.append(cur)
        data = self._future.pop()
        self.doc.close()
        self.doc = fitz.open(stream=data, filetype="pdf")

    # ------------- metadata -------------
    @property
    def page_count(self) -> int:
        return self.doc.page_count

    def page_info(self, i: int) -> PageInfo:
        p = self.doc[i]
        return PageInfo(i, p.rect.width, p.rect.height, p.rotation)

    def metadata(self) -> dict:
        return dict(self.doc.metadata or {})

    def set_metadata(self, meta: dict):
        self.snapshot()
        self.doc.set_metadata(meta)

    # ------------- rendering -------------
    def render(self, index: int, zoom: float = 1.0) -> bytes:
        page = self.doc[index]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")

    def render_pil(self, index: int, zoom: float = 1.0) -> Image.Image:
        page = self.doc[index]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def thumbnail(self, index: int, max_dim: int = 180) -> bytes:
        page = self.doc[index]
        r = page.rect
        scale = max_dim / max(r.width, r.height)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")

    # ------------- page ops -------------
    def delete_pages(self, indices: Iterable[int]):
        self.snapshot()
        for i in sorted(set(indices), reverse=True):
            self.doc.delete_page(i)

    def rotate_page(self, index: int, degrees: int):
        self.snapshot()
        p = self.doc[index]
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

    # ------------- annotations -------------
    def add_text(self, index: int, x: float, y: float, text: str,
                 fontsize: int = 12, color=(0, 0, 0), fontname: str = "helv"):
        self.snapshot()
        page = self.doc[index]
        page.insert_text((x, y), text, fontsize=fontsize, color=color, fontname=fontname)

    def add_text_box(self, index: int, rect: tuple, text: str,
                     fontsize: int = 12, color=(0, 0, 0)):
        self.snapshot()
        page = self.doc[index]
        page.insert_textbox(fitz.Rect(*rect), text, fontsize=fontsize, color=color)

    def add_highlight(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_highlight_annot(quads)
        annot.update()

    def add_underline(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_underline_annot(quads)
        annot.update()

    def add_strikeout(self, index: int, quads):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_strikeout_annot(quads)
        annot.update()

    def add_rect(self, index: int, rect, color=(1, 0, 0), width: float = 1.5):
        self.snapshot()
        page = self.doc[index]
        annot = page.add_rect_annot(fitz.Rect(*rect))
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
        page = self.doc[index]
        page.insert_image(fitz.Rect(*rect), filename=image_path)

    def add_image_bytes(self, index: int, rect, data: bytes):
        self.snapshot()
        page = self.doc[index]
        page.insert_image(fitz.Rect(*rect), stream=data)

    # ------------- search & text -------------
    def search(self, text: str, page_index: Optional[int] = None) -> list:
        results = []
        pages = [page_index] if page_index is not None else range(self.page_count)
        for i in pages:
            page = self.doc[i]
            quads = page.search_for(text, quads=True)
            for q in quads:
                results.append((i, q))
        return results

    def get_text(self, index: int) -> str:
        return self.doc[index].get_text()

    def all_text(self) -> str:
        return "\n\n".join(self.doc[i].get_text() for i in range(self.page_count))

    # ------------- redaction -------------
    def redact(self, index: int, rect, fill=(0, 0, 0)):
        self.snapshot()
        page = self.doc[index]
        page.add_redact_annot(fitz.Rect(*rect), fill=fill)
        page.apply_redactions()

    def redact_text(self, text: str):
        self.snapshot()
        for i in range(self.page_count):
            page = self.doc[i]
            for q in page.search_for(text, quads=True):
                page.add_redact_annot(q.rect, fill=(0, 0, 0))
            page.apply_redactions()

    # ------------- watermark -------------
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
            tw.append((cx - text_w / 2, cy + fontsize / 3), text,
                      font=font, fontsize=fontsize)
            mat = fitz.Matrix(rotation)
            pivot = fitz.Point(cx, cy)
            tw.write_text(page, morph=(pivot, mat))

    def add_page_numbers(self, start: int = 1, fontsize: int = 11,
                         color=(0, 0, 0), position: str = "bottom-center"):
        self.snapshot()
        for i in range(self.page_count):
            page = self.doc[i]
            r = page.rect
            num = str(start + i)
            tw = fitz.get_text_length(num, fontsize=fontsize)
            if position == "bottom-center":
                pos = (r.width / 2 - tw / 2, r.height - 20)
            elif position == "bottom-right":
                pos = (r.width - 40, r.height - 20)
            elif position == "bottom-left":
                pos = (30, r.height - 20)
            elif position == "top-right":
                pos = (r.width - 40, 30)
            elif position == "top-left":
                pos = (30, 30)
            else:
                pos = (r.width / 2 - tw / 2, 30)
            page.insert_text(pos, num, fontsize=fontsize, color=color)

    # ------------- save -------------
    def save(self, path: Optional[str] = None, compress: bool = True):
        out = path or self.path
        if not out:
            raise ValueError("No path provided")
        kwargs = dict(garbage=4, clean=True)
        if compress:
            kwargs["deflate"] = True
            kwargs["deflate_images"] = True
            kwargs["deflate_fonts"] = True
        if out == self.path:
            kwargs["incremental"] = False
            # need to save to temp then replace
            tmp = out + ".tmp"
            self.doc.save(tmp, **kwargs)
            self.doc.close()
            os.replace(tmp, out)
            self.doc = fitz.open(out)
        else:
            self.doc.save(out, **kwargs)
        self.path = out

    def save_copy(self, path: str, compress: bool = True):
        kwargs = dict(garbage=4, clean=True)
        if compress:
            kwargs["deflate"] = True
            kwargs["deflate_images"] = True
            kwargs["deflate_fonts"] = True
        self.doc.save(path, **kwargs)

    def close(self):
        self.doc.close()


# ----------------------------- module-level ops -----------------------------

def merge_pdfs(paths: list[str], out_path: str, progress: Optional[Callable] = None):
    out = fitz.open()
    for idx, p in enumerate(paths):
        with fitz.open(p) as src:
            out.insert_pdf(src)
        if progress:
            progress(idx + 1, len(paths))
    out.save(out_path, garbage=4, deflate=True)
    out.close()


def split_pdf(path: str, out_dir: str, mode: str = "single",
              ranges: Optional[list[tuple[int, int]]] = None) -> list[str]:
    """mode: 'single' (one file per page) or 'ranges' (use ranges list 0-indexed inclusive)."""
    results = []
    src = fitz.open(path)
    stem = Path(path).stem
    if mode == "single":
        for i in range(src.page_count):
            new = fitz.open()
            new.insert_pdf(src, from_page=i, to_page=i)
            out = os.path.join(out_dir, f"{stem}_page{i+1}.pdf")
            new.save(out, garbage=4, deflate=True)
            new.close()
            results.append(out)
    elif mode == "ranges" and ranges:
        for j, (a, b) in enumerate(ranges):
            new = fitz.open()
            new.insert_pdf(src, from_page=a, to_page=b)
            out = os.path.join(out_dir, f"{stem}_part{j+1}.pdf")
            new.save(out, garbage=4, deflate=True)
            new.close()
            results.append(out)
    src.close()
    return results


def compress_pdf(in_path: str, out_path: str, image_quality: int = 60):
    """Re-saves with deflate + downsamples large images."""
    src = fitz.open(in_path)
    for page in src:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(src, xref)
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width > 1500 or pix.height > 1500:
                    scale = 1500 / max(pix.width, pix.height)
                    pix = fitz.Pixmap(pix, int(pix.width * scale), int(pix.height * scale), True)
                buf = io.BytesIO()
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                im.save(buf, format="JPEG", quality=image_quality, optimize=True)
                src.update_stream(xref, buf.getvalue())
            except Exception:
                continue
    src.save(out_path, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)
    src.close()


def encrypt_pdf(in_path: str, out_path: str, user_pw: str, owner_pw: str = "",
                allow_print: bool = True, allow_copy: bool = True, allow_modify: bool = False):
    with pikepdf.open(in_path) as pdf:
        perms = pikepdf.Permissions(
            print_lowres=allow_print,
            print_highres=allow_print,
            extract=allow_copy,
            modify_annotation=allow_modify,
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


def pdf_to_images(in_path: str, out_dir: str, fmt: str = "png", dpi: int = 200) -> list[str]:
    src = fitz.open(in_path)
    stem = Path(in_path).stem
    results = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for i in range(src.page_count):
        pix = src[i].get_pixmap(matrix=mat, alpha=False)
        out = os.path.join(out_dir, f"{stem}_page{i+1}.{fmt}")
        pix.save(out)
        results.append(out)
    src.close()
    return results


def images_to_pdf(image_paths: list[str], out_path: str):
    new = fitz.open()
    for p in image_paths:
        img = Image.open(p)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        w, h = img.size
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
    """Make a scanned PDF searchable using tesseract."""
    try:
        import pytesseract
    except ImportError:
        return False
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    src = fitz.open(in_path)
    out = fitz.open()
    for i in range(src.page_count):
        page = src[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        try:
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=language, extension="pdf")
        except Exception:
            src.close(); out.close()
            return False
        with fitz.open(stream=pdf_bytes, filetype="pdf") as new:
            out.insert_pdf(new)
        if progress:
            progress(i + 1, src.page_count)
    out.save(out_path, garbage=4, deflate=True)
    out.close()
    src.close()
    return True


def find_tesseract() -> Optional[str]:
    """Look for tesseract.exe on Windows in common locations."""
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None
