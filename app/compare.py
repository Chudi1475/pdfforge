"""Compare two PDFs - text diff per page."""
from __future__ import annotations
import difflib
from dataclasses import dataclass

import fitz


@dataclass
class PageDiff:
    page: int
    a_text: str
    b_text: str
    html_diff: str
    added_count: int
    removed_count: int


def compare_text(a_path: str, b_path: str) -> tuple[list[PageDiff], int, int]:
    a = fitz.open(a_path)
    b = fitz.open(b_path)
    n = max(a.page_count, b.page_count)
    diffs: list[PageDiff] = []
    total_add = total_rem = 0
    differ = difflib.HtmlDiff(wrapcolumn=80)
    try:
        for i in range(n):
            a_txt = a[i].get_text() if i < a.page_count else ""
            b_txt = b[i].get_text() if i < b.page_count else ""
            a_lines = a_txt.splitlines()
            b_lines = b_txt.splitlines()
            html = differ.make_table(a_lines, b_lines,
                                     fromdesc=f"Original p{i+1}",
                                     todesc=f"Revised p{i+1}",
                                     context=True, numlines=2)
            # simple add/remove count via unified_diff
            udiff = list(difflib.unified_diff(a_lines, b_lines, lineterm=""))
            add = sum(1 for x in udiff if x.startswith("+ ") or
                      (x.startswith("+") and not x.startswith("+++")))
            rem = sum(1 for x in udiff if x.startswith("- ") or
                      (x.startswith("-") and not x.startswith("---")))
            total_add += add; total_rem += rem
            diffs.append(PageDiff(i, a_txt, b_txt, html, add, rem))
    finally:
        a.close(); b.close()
    return diffs, total_add, total_rem


def compare_html(diffs: list[PageDiff]) -> str:
    """Wrap all per-page diffs into one HTML document."""
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<style>",
        "body{font-family:Calibri,Arial,sans-serif;background:#1e1e1e;color:#eee;margin:20px;}",
        "h2{color:#e63946;border-bottom:1px solid #444;padding-bottom:6px;}",
        "table.diff{font-family:Consolas,monospace;font-size:12px;background:#252525;width:100%;}",
        "table.diff th{background:#2d2d2d;color:#e63946;padding:4px;text-align:left;}",
        "table.diff td{padding:2px 6px;}",
        ".diff_header{background:#2d2d2d;color:#888;}",
        ".diff_next{background:#1a1a1a;}",
        ".diff_add{background:#1b3b1b;color:#9bd99b;}",
        ".diff_chg{background:#3b3b1b;color:#e0e09b;}",
        ".diff_sub{background:#3b1b1b;color:#e09b9b;}",
        ".empty{padding:24px;color:#888;}",
        "</style></head><body>",
    ]
    for d in diffs:
        parts.append(f"<h2>Page {d.page+1} &mdash; +{d.added_count} / -{d.removed_count}</h2>")
        parts.append(d.html_diff)
    parts.append("</body></html>")
    return "\n".join(parts)
