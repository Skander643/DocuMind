"""PyMuPDF per-page text extraction. OCR is out of scope for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PageText:
    page: int
    text: str


def extract_pages(path: Path) -> list[PageText]:
    import pymupdf

    pages: list[PageText] = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append(PageText(page=index, text=text))
    return pages
