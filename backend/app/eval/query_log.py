"""Append pipeline traces to eval/results/query_log.csv."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.config import PROJECT_ROOT
from app.models.schemas import ChatResponse

if TYPE_CHECKING:
    from app.rag.pipeline import RetrievalTrace

LOG_PATH = PROJECT_ROOT / "eval" / "results" / "query_log.csv"
_FIELDS = (
    "ts",
    "query",
    "conversation_id",
    "confidence",
    "latency_ms",
    "best_score",
    "refused",
    "answer",
    "retrieved",
    "reranked",
)


def query_log_enabled() -> bool:
    return "PYTEST_CURRENT_TEST" not in os.environ


def append_query_log(
    trace: RetrievalTrace,
    response: ChatResponse,
    *,
    path: Path | None = None,
) -> Path | None:
    if not query_log_enabled() and path is None:
        return None
    dest = path or LOG_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    best = trace.used[0][1] if trace.used else 0.0
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query": trace.query,
        "conversation_id": response.conversation_id or "",
        "confidence": response.confidence,
        "latency_ms": str(response.latency_ms),
        "best_score": f"{best:.4f}",
        "refused": "1" if response.confidence == "low" else "0",
        "answer": response.answer.replace("\n", " ").strip(),
        "retrieved": _hits(trace.retrieved),
        "reranked": _hits(trace.reranked or trace.used),
    }
    new_file = not dest.is_file()
    with dest.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return dest


def _hits(rows: list[Any]) -> str:
    parts: list[str] = []
    for chunk, score in rows:
        parts.append(f"{chunk.filename}:{chunk.page}:{float(score):.4f}")
    return "|".join(parts)
