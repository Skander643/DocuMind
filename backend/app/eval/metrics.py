"""RAGAS-style metrics: faithfulness, answer relevancy, context precision/recall.

Judge LLM = same OpenRouter/Gemini/Ollama stack as generation (httpx, not LangChain).
Answer relevancy uses BGE-M3 cosine(query, answer) so we do not download extra embedders.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

JudgeFn = Callable[[str], str]
EmbedFn = Callable[[list[str]], list[list[float]]]


def score_item(
    *,
    question: str,
    answer: str,
    ground_truth: str,
    contexts: list[str],
    refused: bool,
    expect_refuse: bool,
    judge_fn: JudgeFn,
    embed_fn: EmbedFn,
) -> dict[str, Any]:
    if expect_refuse:
        return {
            "faithfulness": None,
            "answer_relevancy": None,
            "context_precision": None,
            "context_recall": None,
            "refuse_correct": bool(refused),
        }
    ctx = [c for c in contexts if c.strip()]
    faithfulness = _faithfulness(answer, ctx, judge_fn)
    relevancy = 0.0 if refused else _answer_relevancy(question, answer, embed_fn)
    precision = _context_precision(question, ground_truth, ctx, judge_fn)
    recall = _context_recall(ground_truth, ctx, judge_fn)
    return {
        "faithfulness": faithfulness,
        "answer_relevancy": relevancy,
        "context_precision": precision,
        "context_recall": recall,
        "refuse_correct": None,
    }


def _faithfulness(answer: str, contexts: list[str], judge_fn: JudgeFn) -> float:
    if not answer.strip():
        return 0.0
    prompt = (
        "You grade RAG faithfulness (0-1): fraction of the answer supported by CONTEXT.\n"
        "Ignore style. Penalize invented articles, amounts, or dates.\n"
        "Return JSON only: {\"score\": 0.0}\n\n"
        f"CONTEXT:\n{_join_ctx(contexts)}\n\nANSWER:\n{answer.strip()}\n"
    )
    return _score_from_judge(judge_fn(prompt))


def _context_precision(
    question: str,
    ground_truth: str,
    contexts: list[str],
    judge_fn: JudgeFn,
) -> float:
    if not contexts:
        return 0.0
    numbered = "\n".join(f"[{i}] {text}" for i, text in enumerate(contexts, start=1))
    prompt = (
        "For each CONTEXT passage, is it useful to answer QUESTION given GOLD?\n"
        "Return JSON only: {\"relevant\": [true, false, ...] } one bool per passage.\n\n"
        f"QUESTION: {question}\nGOLD: {ground_truth}\n\nCONTEXT:\n{numbered}\n"
    )
    flags = _bools_from_judge(judge_fn(prompt), len(contexts))
    hits = 0
    total = 0.0
    running = 0
    for i, ok in enumerate(flags, start=1):
        if ok:
            running += 1
            hits += 1
            total += running / i
    if hits == 0:
        return 0.0
    return round(total / hits, 4)


def _context_recall(ground_truth: str, contexts: list[str], judge_fn: JudgeFn) -> float:
    if not ground_truth.strip() or not contexts:
        return 0.0
    prompt = (
        "What fraction of GOLD can be attributed to CONTEXT (0-1)?\n"
        "Return JSON only: {\"score\": 0.0}\n\n"
        f"GOLD:\n{ground_truth.strip()}\n\nCONTEXT:\n{_join_ctx(contexts)}\n"
    )
    return _score_from_judge(judge_fn(prompt))


def _answer_relevancy(question: str, answer: str, embed_fn: EmbedFn) -> float:
    if not question.strip() or not answer.strip():
        return 0.0
    vectors = embed_fn([question.strip(), answer.strip()])
    if len(vectors) < 2:
        return 0.0
    return round(_cosine(vectors[0], vectors[1]), 4)


def _join_ctx(contexts: list[str]) -> str:
    if not contexts:
        return "(none)"
    return "\n\n".join(f"[{i}] {c}" for i, c in enumerate(contexts, start=1))


def _score_from_judge(text: str) -> float:
    data = _parse_json(text)
    if data is None:
        return 0.0
    try:
        value = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0
    return round(min(max(value, 0.0), 1.0), 4)


def _bools_from_judge(text: str, n: int) -> list[bool]:
    data = _parse_json(text)
    raw = data.get("relevant") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return [False] * n
    flags = [bool(x) for x in raw[:n]]
    while len(flags) < n:
        flags.append(False)
    return flags


def _parse_json(text: str) -> dict | None:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _cosine(left: list[float], right: list[float]) -> float:
    n = min(len(left), len(right))
    if n == 0:
        return 0.0
    dot = sum(left[i] * right[i] for i in range(n))
    na = sum(left[i] * left[i] for i in range(n)) ** 0.5
    nb = sum(right[i] * right[i] for i in range(n)) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
