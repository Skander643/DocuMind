"""CrossEncoder rerank (bge-reranker-base). Skips ONNX snapshots."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from pathlib import Path
from functools import lru_cache

from app.config import settings
from app.ingest.chunking import Chunk

_IGNORE = (
    "*.onnx",
    "onnx/**",
    "*.onnx_data",
    "openvino/**",
    "*.ot",
    "pytorch_model.bin.index.json",
    "flax_model.msgpack",
    "tf_model.h5",
)
PredictFn = Callable[[list[tuple[str, str]]], Sequence[float]]


def rerank(
    query: str,
    chunks: list[Chunk],
    top_n: int | None = None,
    *,
    predict_fn: PredictFn | None = None,
) -> list[tuple[Chunk, float]]:
    """Return `top_n` chunks sorted by sigmoid(CrossEncoder logit), desc."""
    if not chunks:
        return []
    keep = top_n if top_n is not None else settings.rerank_top_n
    keep = max(keep, 0)
    if keep == 0:
        return []

    pairs = [(query, chunk.text) for chunk in chunks]
    predict = predict_fn or _default_predict
    raw_scores = _as_float_list(predict(pairs))
    scored = [
        (chunk, _sigmoid(raw_scores[i] if i < len(raw_scores) else 0.0))
        for i, chunk in enumerate(chunks)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:keep]


@lru_cache(maxsize=1)
def get_cross_encoder():
    from huggingface_hub import snapshot_download
    from sentence_transformers import CrossEncoder

    path = snapshot_download(
        repo_id=settings.reranker_model,
        ignore_patterns=list(_IGNORE),
    )
    names = {p.name for p in Path(path).glob("*")}
    if not any(
        name == "pytorch_model.bin" or name.endswith(".safetensors") for name in names
    ):
        path = snapshot_download(
            repo_id=settings.reranker_model,
            ignore_patterns=list(_IGNORE),
            force_download=True,
        )
    return CrossEncoder(path)


def _default_predict(pairs: list[tuple[str, str]]) -> Sequence[float]:
    scores = get_cross_encoder().predict(pairs, show_progress_bar=False)
    return _as_float_list(scores)


def _as_float_list(scores: object) -> list[float]:
    if hasattr(scores, "tolist"):
        converted = scores.tolist()
        if isinstance(converted, (int, float)):
            return [float(converted)]
        return [float(x) for x in converted]
    if isinstance(scores, (int, float)):
        return [float(scores)]
    return [float(x) for x in scores]  # type: ignore[arg-type]


def _sigmoid(logit: float) -> float:
    if logit >= 0:
        z = math.exp(-logit)
        return 1.0 / (1.0 + z)
    z = math.exp(logit)
    return z / (1.0 + z)
