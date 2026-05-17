# Chudi PDF Pro

a free, full-featured pdf editor for windows, mac, and linux. professional editing without a subscription.

view, edit, annotate, sign, merge, split, compress, password protect, ocr, watermark, redact, and convert pdf files. everything runs locally - your documents never leave your machine.

## what it looks like

- top brand bar with built-in document search
- multi-document tabs so you can have several pdfs open at once
- left icon rail for switching between pages / bookmarks / comments / attachments
- center canvas with smooth zoom and pan
- right-side tools panel with grouped tool cards
- contextual property strip with color, text size, and stroke controls
- home screen with quick actions and recent files

## features

**view + navigate**
- multi-document tabs with drag-to-reorder, close, and unsaved-change prompts
- multi-page continuous viewer with smooth zoom + pan
- page thumbnails with drag-to-reorder
- bookmarks tree (jumps to outline destinations)
- comments panel (lists every annotation in the doc)
- attachments panel (embedded files)
- full text search with prev/next jumps + status counter
- fit width / fit page / actual / custom zoom / page indicator with jump

**edit + annotate**
- add text anywhere with font size + color
- highlight, underline, strikeout
- freehand drawing (digital ink)
- rectangles + shapes
- sticky notes (popup annotations)
- insert images (drag a rectangle to place)
- digital signatures: draw with mouse, type in cursive, or upload a png
- redaction: drag-to-redact, or bulk-redact every instance of given terms
- undo / redo (50 step history per document)

**pages**
- rotate (90 left/right/180)
- delete, duplicate, insert blank
- drag-reorder via thumbnails (then "apply order")
- extract a range to a new pdf

**document tools**
- merge multiple pdfs into one (drag list to reorder)
- split (one-per-page or custom ranges)
- compress (downsamples large images, deflate everything)
- password protect with print/copy/modify permission flags
- remove passwords
- ocr scanned pdfs to make them searchable (uses tesseract)
- diagonal watermarks: custom text, color, opacity, rotation
- automatic page numbers in any corner
- edit document metadata (title, author, subject, keywords)

**convert**
- pdf -> png/jpeg at any dpi
- images -> pdf
- pdf -> plain text
- extract embedded images
- print to any printer

## install (windows)

1. install python 3.10+ from https://python.org (tick "add python to path" during setup)
2. double-click `install.bat` - installs deps once
3. double-click `run.bat` to launch

drag a pdf onto `run.bat` to open it directly, or drag any pdf onto the running app window.

## install (mac / linux)

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## build a standalone .exe

want to give it to a friend without making them install python? run `build_exe.bat`. output lands in `dist/ChudiPdfPro/`.

## ocr setup (optional)

ocr requires tesseract:
- windows: https://github.com/UB-Mannheim/tesseract/wiki
- mac: `brew install tesseract`
- linux: `sudo apt install tesseract-ocr`

the app auto-detects tesseract in standard locations.

## keyboard shortcuts

| action | shortcut |
| --- | --- |
| open | ctrl+o |
| save / save as | ctrl+s / ctrl+shift+s |
| close tab | ctrl+w |
| print | ctrl+p |
| undo / redo | ctrl+z / ctrl+y |
| find | ctrl+f |
| zoom in / out | ctrl+= / ctrl+- |
| fit page / fit width | ctrl+0 / ctrl+1 |
| previous / next page | pgup / pgdn |
| select tool | v |
| hand (pan) | h |
| add text | shift+t |
| highlight | shift+h |
| draw | shift+d |

## tech

- python 3.10+
- pyside6 (qt) for the gui
- pymupdf (fitz) for rendering and most pdf ops
- pikepdf for encryption and low-level pdf fixes
- pillow + reportlab for image work
- pytesseract for ocr

all icons are rendered at runtime with qpainter - no external image assets needed.

## license

mit
