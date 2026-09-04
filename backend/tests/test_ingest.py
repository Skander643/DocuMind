from pathlib import Path
from unittest.mock import MagicMock

from app.ingest.chunking import Chunk
from app.ingest.ingest import chunk_pdf, run_ingest
from app.ingest.parse import PageText


def test_chunk_pdf_uses_page_numbers(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "loi.pdf"
    pdf.write_bytes(b"%PDF-fake")

    monkeypatch.setattr(
        "app.ingest.ingest.extract_pages",
        lambda _path: [
            PageText(page=1, text="Article premier. " * 5),
            PageText(page=2, text=""),
            PageText(page=3, text="Congé annuel payé. " * 5),
        ],
    )
    monkeypatch.setattr("app.ingest.ingest.detect_language", lambda _text: "fr")

    chunks = chunk_pdf(pdf)
    pages = {c.page for c in chunks}
    assert 1 in pages
    assert 3 in pages
    assert 2 not in pages
    assert all(c.filename == "loi.pdf" for c in chunks)


def test_run_ingest_dry_run_skips_embed(monkeypatch, tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "a.pdf").write_bytes(b"%PDF-fake")

    fake_chunks = [
        Chunk(
            doc_id="x",
            filename="a.pdf",
            page=1,
            text="hello",
            language="fr",
            chunk_index=0,
        )
    ]
    monkeypatch.setattr("app.ingest.ingest.list_pdfs", lambda _d=None: [raw / "a.pdf"])
    monkeypatch.setattr("app.ingest.ingest.chunk_pdf", lambda _p: fake_chunks)
    monkeypatch.setattr(
        "app.ingest.ingest.settings",
        MagicMock(data_raw_dir=raw, chunk_size=512, chunk_overlap=64),
    )

    result = run_ingest(raw, dry_run=True)
    assert result["documents"] == 1
    assert result["chunks"] == 1
