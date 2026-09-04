import json
from pathlib import Path

import pytest

from app.ingest.ids import make_doc_id
from app.ingest.catalog import (
    MAX_UPLOAD_BYTES,
    delete_indexed_document,
    find_pdf_by_doc_id,
    list_document_infos,
    merge_manifest_rows,
    safe_pdf_filename,
    save_upload,
)


def test_safe_pdf_filename_rejects_paths() -> None:
    with pytest.raises(ValueError):
        safe_pdf_filename("../secret.pdf")
    with pytest.raises(ValueError):
        safe_pdf_filename("notes.txt")
    assert safe_pdf_filename("code.pdf") == "code.pdf"


def test_save_upload_writes_pdf(tmp_path: Path) -> None:
    dest = save_upload("loi.pdf", b"%PDF-1.4 hello", raw_dir=tmp_path)
    assert dest == tmp_path / "loi.pdf"
    assert dest.read_bytes().startswith(b"%PDF")


def test_save_upload_rejects_non_pdf(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a PDF"):
        save_upload("loi.pdf", b"not-a-pdf", raw_dir=tmp_path)


def test_manifest_merge_keeps_other_files(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    merge_manifest_rows(
        [{"doc_id": "a", "filename": "a.pdf", "n_chunks": 1, "language": "fr"}],
        raw_dir=raw,
    )
    merge_manifest_rows(
        [{"doc_id": "b", "filename": "b.pdf", "n_chunks": 2, "language": "fr"}],
        raw_dir=raw,
    )
    rows = json.loads((tmp_path / "processed" / "manifest.json").read_text())
    names = {row["filename"] for row in rows}
    assert names == {"a.pdf", "b.pdf"}


def test_manifest_replace_overwrites(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    merge_manifest_rows(
        [{"doc_id": "a", "filename": "a.pdf", "n_chunks": 1, "language": "fr"}],
        raw_dir=raw,
    )
    merge_manifest_rows(
        [{"doc_id": "b", "filename": "b.pdf", "n_chunks": 2, "language": "fr"}],
        raw_dir=raw,
        replace=True,
    )
    rows = json.loads((tmp_path / "processed" / "manifest.json").read_text())
    assert [row["filename"] for row in rows] == ["b.pdf"]


def test_list_document_infos_combines_disk_and_chroma(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "code.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc_id = make_doc_id(pdf)
    monkeypatch.setattr(
        "app.ingest.catalog._chunk_stats",
        lambda: {
            doc_id: {"n_chunks": 3, "filename": "code.pdf", "language": "fr"},
            "orphan": {"n_chunks": 1, "filename": "gone.pdf", "language": "fr"},
        },
    )
    infos = list_document_infos(tmp_path)
    by_id = {item.doc_id: item for item in infos}
    assert by_id[doc_id].status == "indexed"
    assert by_id[doc_id].n_chunks == 3
    assert by_id["orphan"].status == "missing_file"


def test_find_and_delete_document(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    pdf = raw / "code.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc_id = make_doc_id(pdf)
    deleted: list[str] = []
    monkeypatch.setattr("app.ingest.catalog._chunk_stats", lambda: {doc_id: {"n_chunks": 1}})
    monkeypatch.setattr(
        "app.db.chroma_client.delete_doc",
        lambda value: deleted.append(value),
    )
    assert find_pdf_by_doc_id(doc_id, raw) == pdf
    delete_indexed_document(doc_id, raw)
    assert deleted == [doc_id]
    assert not pdf.exists()


def test_upload_size_limit_constant() -> None:
    assert MAX_UPLOAD_BYTES >= 1_000_000
