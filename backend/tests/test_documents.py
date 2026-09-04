from pathlib import Path

from fastapi.testclient import TestClient

from app.ingest.ids import make_doc_id
from app.main import app
from app.models.schemas import DocumentInfo

client = TestClient(app)


def test_list_documents_uses_catalog(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.documents.list_document_infos",
        lambda: [
            DocumentInfo(
                doc_id="abc123",
                filename="code.pdf",
                n_chunks=12,
                language="fr",
                status="indexed",
            )
        ],
    )
    response = client.get("/api/documents")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["doc_id"] == "abc123"
    assert body[0]["n_chunks"] == 12
    assert body[0]["status"] == "indexed"


def test_upload_rejects_non_pdf(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.documents.run_ingest", lambda **_k: None)
    response = client.post(
        "/api/documents",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert response.status_code == 400


def test_upload_indexes_pdf(monkeypatch, tmp_path: Path) -> None:
    called: list[list[str]] = []

    def fake_save(name: str, data: bytes) -> Path:
        path = tmp_path / name
        path.write_bytes(data)
        return path

    monkeypatch.setattr("app.api.routes.documents.save_upload", fake_save)
    monkeypatch.setattr(
        "app.api.routes.documents.run_ingest",
        lambda filenames=None, **_k: called.append(list(filenames or [])),
    )
    monkeypatch.setattr(
        "app.api.routes.documents.list_document_infos",
        lambda: [
            DocumentInfo(doc_id="id1", filename="loi.pdf", n_chunks=4, status="indexed")
        ],
    )
    response = client.post(
        "/api/documents",
        files=[("files", ("loi.pdf", b"%PDF-1.4 body", "application/pdf"))],
    )
    assert response.status_code == 201
    assert called == [["loi.pdf"]]
    assert response.json()[0]["filename"] == "loi.pdf"


def test_delete_missing_is_404(monkeypatch) -> None:
    def boom(_doc_id: str) -> None:
        raise FileNotFoundError(_doc_id)

    monkeypatch.setattr("app.api.routes.documents.delete_indexed_document", boom)
    response = client.delete("/api/documents/missing")
    assert response.status_code == 404


def test_delete_ok(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        "app.api.routes.documents.delete_indexed_document",
        lambda doc_id: seen.append(doc_id),
    )
    response = client.delete("/api/documents/abc")
    assert response.status_code == 204
    assert seen == ["abc"]


def test_reindex_404(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.documents.find_pdf_by_doc_id", lambda _id: None)
    response = client.post("/api/documents/abc/reindex")
    assert response.status_code == 404


def test_reindex_ok(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "code.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    ingest_files: list[str] = []
    monkeypatch.setattr("app.api.routes.documents.find_pdf_by_doc_id", lambda _id: pdf)
    monkeypatch.setattr(
        "app.api.routes.documents.run_ingest",
        lambda filenames=None, **_k: ingest_files.extend(filenames or []),
    )
    monkeypatch.setattr(
        "app.api.routes.documents.list_document_infos",
        lambda: [DocumentInfo(doc_id="x", filename="code.pdf", n_chunks=2, status="indexed")],
    )
    response = client.post("/api/documents/x/reindex")
    assert response.status_code == 200
    assert ingest_files == ["code.pdf"]
    assert response.json()["n_chunks"] == 2


def test_get_pdf_file(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "code.pdf"
    pdf.write_bytes(b"%PDF-1.4 cited-page")
    monkeypatch.setattr("app.api.routes.documents.find_pdf_by_doc_id", lambda _id: pdf)
    response = client.get("/api/documents/doc1/file")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert b"cited-page" in response.content


def test_get_pdf_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.documents.find_pdf_by_doc_id", lambda _id: None)
    response = client.get("/api/documents/nope/file")
    assert response.status_code == 404


def test_doc_id_stable_for_same_bytes(tmp_path: Path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    assert make_doc_id(pdf) == make_doc_id(pdf)
