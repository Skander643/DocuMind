"""Run gold_qa.json through the pipeline and score RAGAS metrics."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, settings
from app.eval.metrics import score_item
from app.rag.pipeline import Pipeline

logger = logging.getLogger(__name__)

GOLD_PATH = PROJECT_ROOT / "eval" / "gold_qa.json"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
LATEST_NAME = "latest.json"


def load_gold(path: Path | None = None) -> list[dict[str, Any]]:
    data = json.loads((path or GOLD_PATH).read_text(encoding="utf-8"))
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("gold_qa.json must contain an items list")
    return items


def run_batch(
    gold_path: str | Path | None = None,
    *,
    pipeline: Pipeline | None = None,
    limit: int | None = None,
    judge_fn=None,
    embed_fn=None,
) -> dict[str, Any]:
    items = load_gold(Path(gold_path) if gold_path else None)
    if limit is not None:
        items = items[:limit]
    pipe = pipeline or Pipeline()
    judge = judge_fn or _default_judge
    embed = embed_fn or _default_embed

    scored: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        question = str(item["question"])
        logger.info("eval %s/%s %s", i, len(items), item.get("id"))
        ground = str(item.get("ground_truth") or "")
        expect_refuse = bool(item.get("expect_refuse"))
        response, trace = pipe.ask_with_trace(question)
        contexts = [chunk.text for chunk, _ in trace.used]
        metrics = score_item(
            question=question,
            answer=response.answer,
            ground_truth=ground,
            contexts=contexts,
            refused=response.confidence == "low",
            expect_refuse=expect_refuse,
            judge_fn=judge,
            embed_fn=embed,
        )
        scored.append(
            {
                "id": item.get("id"),
                "question": question,
                "language": item.get("language"),
                "source_hint": item.get("source_hint"),
                "expect_refuse": expect_refuse,
                "answer": response.answer,
                "confidence": response.confidence,
                "latency_ms": response.latency_ms,
                "n_context": len(contexts),
                "citations": [
                    {"filename": c.filename, "page": c.page, "score": c.score}
                    for c in response.citations
                ],
                **metrics,
            }
        )
        _write_results(_payload(scored), snapshot=False)

    payload = _payload(scored)
    _write_results(payload, snapshot=True)
    return payload


def load_latest_summary() -> dict[str, Any] | None:
    path = RESULTS_DIR / LATEST_NAME
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return _public_summary(data)


def _public_summary(data: dict[str, Any]) -> dict[str, Any]:
    metrics = data.get("metrics") or {}
    return {
        "created_at": data.get("created_at"),
        "n_questions": data.get("n_questions"),
        "faithfulness": metrics.get("faithfulness"),
        "answer_relevancy": metrics.get("answer_relevancy"),
        "context_precision": metrics.get("context_precision"),
        "context_recall": metrics.get("context_recall"),
        "refuse_accuracy": metrics.get("refuse_accuracy"),
        "config": data.get("config") or {},
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ragas_rows = [r for r in rows if not r.get("expect_refuse")]
    refuse_rows = [r for r in rows if r.get("expect_refuse")]

    def mean(key: str) -> float | None:
        values = [float(r[key]) for r in ragas_rows if r.get(key) is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    refuse_accuracy = None
    if refuse_rows:
        hits = sum(1 for r in refuse_rows if r.get("refuse_correct"))
        refuse_accuracy = round(hits / len(refuse_rows), 4)

    return {
        "faithfulness": mean("faithfulness"),
        "answer_relevancy": mean("answer_relevancy"),
        "context_precision": mean("context_precision"),
        "context_recall": mean("context_recall"),
        "refuse_accuracy": refuse_accuracy,
        "n_ragas": len(ragas_rows),
        "n_refuse": len(refuse_rows),
    }


def _payload(scored: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_questions": len(scored),
        "config": {
            "retrieve_k": settings.retrieve_k,
            "rerank_top_n": settings.rerank_top_n,
            "rerank_min_score": settings.rerank_min_score,
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
            "llm": settings.openrouter_model
            if settings.openrouter_api_key
            else settings.gemini_model,
        },
        "metrics": _summarize(scored),
        "items": scored,
    }


def _write_results(payload: dict[str, Any], *, snapshot: bool = True) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (RESULTS_DIR / LATEST_NAME).write_text(text + "\n", encoding="utf-8")
    if snapshot:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = RESULTS_DIR / f"ragas_{stamp}.json"
        dest.write_text(text + "\n", encoding="utf-8")
        return dest
    return RESULTS_DIR / LATEST_NAME


def _default_judge(prompt: str) -> str:
    from app.rag.llm import _complete

    return _complete(prompt, openrouter_fn=None, gemini_fn=None, ollama_fn=None)


def _default_embed(texts: list[str]) -> list[list[float]]:
    from app.rag.embeddings import embed_texts

    return embed_texts(texts)
