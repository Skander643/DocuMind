"""Shared BGE-M3 embedder (query + documents). Lazy-loaded.

Skips ONNX/OpenVINO snapshots so a laptop does not download extra multi-GB files.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings

_BATCH = 8
_IGNORE = (
    "*.onnx",
    "onnx/**",
    "*.onnx_data",
    "openvino/**",
    "*.ot",
    "pytorch_model.bin",
    "pytorch_model.bin.index.json",
    "flax_model.msgpack",
    "tf_model.h5",
)


def _model_path() -> str:
    from huggingface_hub import snapshot_download

    return snapshot_download(
        repo_id=settings.embedding_model,
        ignore_patterns=list(_IGNORE),
    )


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_model_path())


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = get_model().encode(
        texts,
        batch_size=_BATCH,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > _BATCH,
    )
    return [vec.tolist() for vec in vectors]
