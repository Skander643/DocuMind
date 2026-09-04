"""Indexed PDF catalog: disk + Chroma + manifest. No embedding calls."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.ingest.ids import make_doc_id
from app.models.schemas import DocumentInfo

MAX_UPLOAD_BYTES = 30 * 1024 * 1024


def list_pdfs(raw_dir: Path | None = None) -> list[Path]:
    directory = raw_dir or settings.data_raw_dir
    directory.mkdir(parents=True, exist_ok=True)
    return sorted(directory.glob("*.pdf"))


def manifest_path(raw_dir: Path | None = None) -> Path:
    directory = raw_dir or settings.data_raw_dir
    return directory.parent / "processed" / "manifest.json"


def load_manifest(raw_dir: Path | None = None) -> list[dict]:
    path = manifest_path(raw_dir)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def merge_manifest_rows(
    rows: list[dict],
    *,
    raw_dir: Path | None = None,
    replace: bool = False,
) -> Path:
    """Write ingest rows. Merge by filename unless `replace` (full --reset)."""
    merged: dict[str, dict]
    if replace:
        merged = {str(row["filename"]): row for row in rows}
    else:
        merged = {str(row["filename"]): row for row in load_manifest(raw_dir) if row.get("filename")}
        for row in rows:
            merged[str(row["filename"])] = row
    path = manifest_path(raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(list(merged.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def drop_manifest_doc(doc_id: str, raw_dir: Path | None = None) -> None:
    rows = [row for row in load_manifest(raw_dir) if row.get("doc_id") != doc_id]
    path = manifest_path(raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_pdf_filename(name: str) -> str:
    if not name or "/" in name or "\\" in name:
        raise ValueError("Invalid filename.")
    base = Path(name).name
    if base != name or base in {".", ".."}:
        raise ValueError("Invalid filename.")
    if not base.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are accepted.")
    return base


def save_upload(filename: str, data: bytes, raw_dir: Path | None = None) -> Path:
    name = safe_pdf_filename(filename)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"PDF exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
    if not data.startswith(b"%PDF"):
        raise ValueError("File is not a PDF.")
    directory = raw_dir or settings.data_raw_dir
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / name
    previous_id = make_doc_id(dest) if dest.is_file() else None
    dest.write_bytes(data)
    new_id = make_doc_id(dest)
    if previous_id and previous_id != new_id:
        from app.db.chroma_client import delete_doc

        delete_doc(previous_id)
        drop_manifest_doc(previous_id, raw_dir)
    return dest


def find_pdf_by_doc_id(doc_id: str, raw_dir: Path | None = None) -> Path | None:
    for path in list_pdfs(raw_dir):
        if make_doc_id(path) == doc_id:
            return path
    for row in load_manifest(raw_dir):
        if row.get("doc_id") == doc_id and row.get("filename"):
            candidate = (raw_dir or settings.data_raw_dir) / Path(str(row["filename"])).name
            if candidate.is_file() and make_doc_id(candidate) == doc_id:
                return candidate
    return None


def list_document_infos(raw_dir: Path | None = None) -> list[DocumentInfo]:
    stats = _chunk_stats()
    infos: list[DocumentInfo] = []
    seen: set[str] = set()
    for path in list_pdfs(raw_dir):
        doc_id = make_doc_id(path)
        seen.add(doc_id)
        meta = stats.get(doc_id, {})
        n_chunks = int(meta.get("n_chunks") or 0)
        infos.append(
            DocumentInfo(
                doc_id=doc_id,
                filename=path.name,
                n_chunks=n_chunks,
                language=meta.get("language"),
                status="indexed" if n_chunks else "on_disk",
            )
        )
    for doc_id, meta in stats.items():
        if doc_id in seen:
            continue
        infos.append(
            DocumentInfo(
                doc_id=doc_id,
                filename=str(meta.get("filename") or doc_id),
                n_chunks=int(meta.get("n_chunks") or 0),
                language=meta.get("language"),
                status="missing_file",
            )
        )
    return infos


def delete_indexed_document(doc_id: str, raw_dir: Path | None = None) -> None:
    path = find_pdf_by_doc_id(doc_id, raw_dir)
    stats = _chunk_stats()
    in_manifest = any(row.get("doc_id") == doc_id for row in load_manifest(raw_dir))
    if path is None and doc_id not in stats and not in_manifest:
        raise FileNotFoundError(doc_id)
    from app.db.chroma_client import delete_doc

    delete_doc(doc_id)
    if path is not None:
        path.unlink(missing_ok=True)
    drop_manifest_doc(doc_id, raw_dir)


def _chunk_stats() -> dict[str, dict]:
    try:
        from app.db.chroma_client import chunk_stats_by_doc_id

        return chunk_stats_by_doc_id()
    except Exception:
        return {}
