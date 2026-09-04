from pathlib import Path

import pymupdf

from app.ingest.ids import make_doc_id
from app.ingest.parse import extract_pages


def test_extract_pages_is_one_based(tmp_path: Path) -> None:
    path = tmp_path / "tiny.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Article 2. La relation de travail est prouvee par tous moyens.")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Deuxieme page du decret.")
    doc.save(path)
    doc.close()

    pages = extract_pages(path)
    assert [p.page for p in pages] == [1, 2]
    assert "Article 2" in pages[0].text
    assert "Deuxieme" in pages[1].text
    assert len(make_doc_id(path)) == 16
