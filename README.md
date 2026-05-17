# PDFForge

a free, open-source pdf editor for windows, macos and linux. an alternative to adobe acrobat pro.

view, edit, annotate, sign, merge, split, compress, password protect, ocr, watermark, redact and convert pdf files. no subscriptions, no nags, runs entirely on your machine.

## features

**view + navigate**
- multi-page continuous viewer with smooth zoom and pan
- page thumbnails sidebar with drag-to-reorder
- full text search with next/prev jumps
- fit width / fit page / actual size / custom zoom

**edit**
- add text anywhere with font size + color
- highlight, underline, strikeout text
- freehand drawing (digital ink)
- rectangles + shapes
- sticky notes (popup annotations)
- insert images
- digital signatures: draw, type or upload
- redaction: drag a black bar over anything sensitive
- bulk redaction: enter a list of terms to black out everywhere
- undo / redo

**pages**
- rotate (90 left/right/180)
- delete, duplicate, insert blank
- drag-reorder via thumbnails
- extract a range to a new pdf

**document operations**
- merge multiple pdfs into one
- split a pdf (one-per-page or custom ranges)
- compress (downsamples large images)
- password protect with permission flags
- remove passwords
- ocr scanned pdfs to make them searchable (needs tesseract installed)
- diagonal watermarks with custom text, color, opacity, rotation
- automatic page numbers in any corner

**convert**
- pdf -> png/jpeg images at any dpi
- images -> pdf
- pdf -> plain text
- extract embedded images
- print to any printer

## install (windows)

1. install python 3.10 or newer from https://python.org (tick "add to path")
2. double-click `install.bat` - installs deps automatically
3. double-click `run.bat` to launch

## install (mac/linux)

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## build a standalone .exe

want one file you can distribute? run `build_exe.bat`. output lands in `dist/PDFForge/`.

## ocr setup (optional)

ocr requires tesseract:
- windows: https://github.com/UB-Mannheim/tesseract/wiki
- mac: `brew install tesseract`
- linux: `sudo apt install tesseract-ocr`

pdfforge auto-detects tesseract in standard locations.

## keyboard shortcuts

| action | shortcut |
| --- | --- |
| open | ctrl+o |
| save / save as | ctrl+s / ctrl+shift+s |
| print | ctrl+p |
| undo / redo | ctrl+z / ctrl+y |
| find | ctrl+f |
| zoom in/out | ctrl+= / ctrl+- |
| fit width | ctrl+1 |
| fit page | ctrl+0 |
| select tool | v |
| hand tool | h |
| add text | shift+t |
| highlight | shift+h |
| draw | shift+d |
| next/prev page | pgdn / pgup |

## tech

- python 3.10+
- pyside6 (qt) for the gui
- pymupdf (fitz) for rendering and most pdf ops
- pikepdf for encryption and low-level pdf fixes
- pillow + reportlab for image work
- pytesseract for ocr

## license

mit
