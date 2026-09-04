"""Persistent Chroma collection for labour-law chunks."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.ingest.chunking import Chunk
from app.ingest.ids import chunk_id

COLLECTION_NAME = "documind_labor_law"


def get_persist_dir() -> str:
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return str(settings.chroma_persist_dir)


def get_client():
    import chromadb

    return chromadb.PersistentClient(path=get_persist_dir())


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": settings.embedding_model,
        },
    )


def delete_doc(doc_id: str) -> None:
    collection = get_collection()
    try:
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        existing = collection.get(where={"doc_id": doc_id})
        ids = existing.get("ids") or []
        if ids:
            collection.delete(ids=ids)


def upsert_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    if not chunks:
        return
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    collection = get_collection()
    batch = 100
    for start in range(0, len(chunks), batch):
        slc = chunks[start : start + batch]
        embs = embeddings[start : start + batch]
        collection.upsert(
            ids=[chunk_id(c.doc_id, c.chunk_index) for c in slc],
            embeddings=embs,
            documents=[c.text for c in slc],
            metadatas=[_metadata(c) for c in slc],
        )


def count_chunks() -> int:
    return get_collection().count()


def chunk_stats_by_doc_id() -> dict[str, dict[str, Any]]:
    """Group collection metadata by doc_id (n_chunks, filename, language)."""
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return {}
    got = collection.get(limit=total, include=["metadatas"])
    stats: dict[str, dict[str, Any]] = {}
    for meta in got.get("metadatas") or []:
        if not meta:
            continue
        doc_id = str(meta.get("doc_id") or "")
        if not doc_id:
            continue
        row = stats.setdefault(
            doc_id,
            {
                "n_chunks": 0,
                "filename": meta.get("filename"),
                "language": meta.get("language"),
            },
        )
        row["n_chunks"] = int(row["n_chunks"]) + 1
    return stats



def sample_records(n: int = 3) -> list[dict[str, Any]]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []
    got = collection.get(limit=min(n, total), include=["documents", "metadatas"])
    rows: list[dict[str, Any]] = []
    for i, cid in enumerate(got.get("ids") or []):
        meta = (got.get("metadatas") or [{}])[i] or {}
        rows.append(
            {
                "id": cid,
                "filename": meta.get("filename"),
                "page": meta.get("page"),
                "language": meta.get("language"),
                "chunk_index": meta.get("chunk_index"),
                "text": (got.get("documents") or [""])[i] or "",
            }
        )
    return rows


def _metadata(chunk: Chunk) -> dict[str, str | int]:
    return {
        "doc_id": chunk.doc_id,
        "filename": chunk.filename,
        "page": int(chunk.page),
        "language": chunk.language,
        "chunk_index": int(chunk.chunk_index),
    }
