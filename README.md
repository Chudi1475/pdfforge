# Chudi PDF Pro

a complete, free pdf editor for windows / mac / linux. everything you'd actually use a paid pdf suite for - view, edit text, annotate, sign, redact, merge, split, compress, ocr, watermark, fill forms, convert to word / excel / html, compare, and a lot more. runs entirely on your own machine, no subscription, no cloud upload.

## what it can do

### view & navigate
- multi-document tabs - open many pdfs at once, drag tabs to reorder
- three viewing modes: continuous scroll, single page, two-page spread
- reading mode (full screen, no chrome) - F11 to toggle
- left icon rail switches the side panel between **Pages / Bookmarks / Comments / Attachments**
- page thumbnails with drag-to-reorder and right-click menu
- bookmarks tree, comments list, attachment list, all wired to jump-on-click
- continuous text search + Ctrl+F panel with prev/next, match-case, whole-words
- fit width / fit page / actual size / custom zoom / page indicator with jump
- right-click any page for copy text, export as image, rotate, duplicate, delete

### edit
- **edit existing text inline** - click on a word with Edit-text tool to retype it
- add new text anywhere in any color / size / font
- crop pages visually (drag a rectangle) or by margins for the whole doc
- headers & footers with left / center / right slots on top and bottom, `{n}` / `{N}` placeholders
- text watermarks with custom color, opacity, rotation
- image watermarks with scale, opacity, rotation
- automatic page numbers in any corner with custom formats
- create hyperlinks to URLs or other pages (drag a rectangle)
- add bookmarks to build a TOC outline
- find & replace text across the whole document
- edit document properties (title, author, subject, keywords)

### comment & markup
- highlight, underline, strikeout, squiggly
- sticky notes (popup annotations)
- text callouts with leader line
- free-hand drawing, rectangles, ovals, lines, **arrows**, polygons, polylines
- stamps gallery: Approved, Confidential, Draft, Final, Reviewed, Rejected, Void, Paid, Received, For Comment, Top Secret, Sample, Original, Copy, Urgent, Not Approved — plus round versions, custom text stamps, and stamps from your own images
- eraser tool removes any annotation under your cursor

### fill & sign
- digital signature: draw with mouse, type with cursive fonts, or upload an image
- form field detection — opens all form fields in one dialog to fill
- create form fields (text inputs, checkboxes)
- flatten forms to burn values into the document permanently

### organize pages
- rotate (90 left / right / 180), rotate all / odd / even only
- delete, duplicate, insert blank, extract page range to new pdf
- **insert pages from another pdf** at any position
- **replace a page** with one from another pdf
- drag-to-reorder via thumbnails, then "apply order"
- combine multiple pdfs into one (drag list to reorder)
- split: one-per-page, custom ranges, every N pages, or by file size

### protect
- password protect with permission flags (print / copy / modify / annotate)
- remove passwords
- redact by dragging a black bar
- **mark for redaction** — preview many redactions before applying
- redact every occurrence of given terms in bulk
- sanitize: strip metadata and JavaScript annotations
- compress: presets from "high quality" to "smallest", custom JPEG quality + max dimension

### convert
- pdf → word (.docx) preserving paragraphs + inline images
- pdf → excel (.xlsx) with table detection per page
- pdf → html with embedded images and inline styles
- pdf → rich text (.rtf)
- pdf → plain text (.txt)
- pdf → images (png/jpeg) at any dpi
- images → pdf
- extract all embedded images
- ocr scanned pdfs (needs tesseract installed)
- print to any printer

### advanced
- **compare two pdfs** — text diff per page, color-coded HTML report you can save
- **batch processor** — apply compress / page-numbers / watermark / convert / sanitize to many files at once with a progress log
- **read aloud** — text-to-speech with voice + speed controls (uses your OS voices)
- **measure tools** — distance and area in points/inches/cm
- **text select** — drag to copy text content from any region

## install (windows)

1. install python 3.10+ from https://python.org (tick "add to path")
2. double-click `install.bat` — installs deps once
3. double-click `run.bat` to launch

drag a pdf onto the running window to open it.

## install (mac / linux)

```
python3 -m pip install -r requirements.txt
python3 main.py
```

## build a standalone .exe

run `build_exe.bat`. output lands in `dist/ChudiPdfPro/`.

## ocr (optional)

tesseract handles ocr.
- windows: https://github.com/UB-Mannheim/tesseract/wiki
- mac: `brew install tesseract`
- linux: `sudo apt install tesseract-ocr`

the app auto-detects standard install locations.

## keyboard shortcuts

| action | shortcut |
| --- | --- |
| open | Ctrl+O |
| save / save as | Ctrl+S / Ctrl+Shift+S |
| close tab | Ctrl+W |
| print | Ctrl+P |
| undo / redo | Ctrl+Z / Ctrl+Y |
| find | Ctrl+F |
| find & replace | Ctrl+H |
| add bookmark | Ctrl+B |
| add hyperlink | Ctrl+K |
| read aloud | Ctrl+Shift+R |
| reading mode | F11 |
| delete current page | Ctrl+Shift+D |
| zoom in / out | Ctrl+= / Ctrl+- |
| fit page / fit width | Ctrl+0 / Ctrl+1 |
| previous / next page | PgUp / PgDn |
| select / hand / text / edit text | V / H / Shift+T / Shift+E |
| highlight / draw | Shift+H / Shift+D |

## tech

- python 3.10+
- pyside6 (qt) — gui
- pymupdf — rendering, annotations, redaction, ocr glue, forms, links, bookmarks
- pikepdf — encryption + low-level pdf fixes
- python-docx + openpyxl — word/excel export
- pillow + reportlab — image work
- pyttsx3 — offline text-to-speech
- pytesseract — ocr

all icons are rendered at runtime with qpainter — no asset files needed.

## license

mit
