"""Chroma top-k retrieval using the same embedder as ingest."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.config import settings
from app.ingest.chunking import Chunk

EmbedFn = Callable[[list[str]], list[list[float]]]


def retrieve(
    query: str,
    k: int | None = None,
    *,
    embed_fn: EmbedFn | None = None,
    collection=None,
) -> list[tuple[Chunk, float]]:
    """Return up to `k` chunks ranked by cosine similarity (higher is better)."""
    text = query.strip()
    if not text:
        return []
    top_k = k if k is not None else settings.retrieve_k
    if top_k < 1:
        return []

    encode = embed_fn or _default_embed
    store = collection if collection is not None else _default_collection()
    vectors = encode([text])
    if not vectors:
        return []

    n_store = store.count()
    if n_store == 0:
        return []

    result = store.query(
        query_embeddings=[vectors[0]],
        n_results=min(top_k, n_store),
        include=["documents", "metadatas", "distances"],
    )
    documents: Sequence[str] = (result.get("documents") or [[]])[0] or []
    metadatas: Sequence[dict] = (result.get("metadatas") or [[]])[0] or []
    distances: Sequence[float] = (result.get("distances") or [[]])[0] or []

    hits: list[tuple[Chunk, float]] = []
    for i, doc in enumerate(documents):
        meta = metadatas[i] if i < len(metadatas) else {}
        dist = float(distances[i]) if i < len(distances) else 1.0
        hits.append((_chunk_from_hit(doc or "", meta or {}), _similarity(dist)))
    return hits


def _similarity(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))


def _chunk_from_hit(text: str, meta: dict) -> Chunk:
    return Chunk(
        doc_id=str(meta.get("doc_id") or ""),
        filename=str(meta.get("filename") or ""),
        page=int(meta.get("page") or 0),
        text=text,
        language=str(meta.get("language") or "unknown"),
        chunk_index=int(meta.get("chunk_index") or 0),
    )


def _default_embed(texts: list[str]) -> list[list[float]]:
    from app.rag.embeddings import embed_texts

    return embed_texts(texts)


def _default_collection():
    from app.db.chroma_client import get_collection

    return get_collection()
