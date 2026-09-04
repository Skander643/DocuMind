"""Orchestrator: retrieve → rerank → confidence gate → generate.

API routers must call `Pipeline.ask` only.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.config import settings
from app.ingest.chunking import Chunk
from app.ingest.language import detect_language
from app.models.schemas import ChatResponse, Citation
from app.rag.prompts import refusal_message
from app.rag.reranker import rerank
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)

RetrieveFn = Callable[..., list[tuple[Chunk, float]]]
RerankFn = Callable[..., list[tuple[Chunk, float]]]
GenerateFn = Callable[..., str]

_EXCERPT = 280


@dataclass
class RetrievalTrace:
    query: str
    retrieved: list[tuple[Chunk, float]] = field(default_factory=list)
    reranked: list[tuple[Chunk, float]] = field(default_factory=list)
    used: list[tuple[Chunk, float]] = field(default_factory=list)
    use_rerank: bool = True


class Pipeline:
    def __init__(
        self,
        *,
        retrieve_fn: RetrieveFn | None = None,
        rerank_fn: RerankFn | None = None,
        generate_fn: GenerateFn | None = None,
    ) -> None:
        self._retrieve = retrieve_fn or retrieve
        self._rerank = rerank_fn or rerank
        self._generate = generate_fn or _default_generate

    def trace(self, query: str, *, use_rerank: bool = True) -> RetrievalTrace:
        retrieved = self._retrieve(query, settings.retrieve_k)
        if use_rerank:
            used = self._rerank(
                query,
                [chunk for chunk, _ in retrieved],
                settings.rerank_top_n,
            )
        else:
            used = retrieved[: settings.rerank_top_n]
        return RetrievalTrace(
            query=query,
            retrieved=retrieved,
            reranked=used if use_rerank else [],
            used=used,
            use_rerank=use_rerank,
        )

    def ask(
        self,
        query: str,
        conversation_id: str | None = None,
        *,
        use_rerank: bool = True,
    ) -> ChatResponse:
        response, _trace = self.ask_with_trace(
            query,
            conversation_id,
            use_rerank=use_rerank,
        )
        return response

    def ask_with_trace(
        self,
        query: str,
        conversation_id: str | None = None,
        *,
        use_rerank: bool = True,
    ) -> tuple[ChatResponse, RetrievalTrace]:
        started = time.perf_counter()
        trace = self.trace(query, use_rerank=use_rerank)
        language = detect_language(query, min_chars=8)
        citations = [_citation(chunk, score) for chunk, score in trace.used]
        best = trace.used[0][1] if trace.used else 0.0
        logger.info(
            "ask rerank=%s retrieved=%s used=%s best=%.3f",
            use_rerank,
            len(trace.retrieved),
            len(trace.used),
            best,
        )

        if not trace.used or best < settings.rerank_min_score:
            response = ChatResponse(
                answer=refusal_message(language),
                citations=citations,
                confidence="low",
                latency_ms=_latency_ms(started),
                conversation_id=conversation_id,
            )
            _log_ask(trace, response)
            return response, trace

        answer = self._generate(query, [chunk for chunk, _ in trace.used])
        refused = answer.strip() == refusal_message(language)
        response = ChatResponse(
            answer=answer,
            citations=citations,
            confidence="low" if refused else "high",
            latency_ms=_latency_ms(started),
            conversation_id=conversation_id,
        )
        _log_ask(trace, response)
        return response, trace


def get_pipeline() -> Pipeline:
    return Pipeline()


def _default_generate(query: str, context: list[Chunk]) -> str:
    from app.rag.llm import generate

    return generate(query, context)


def _citation(chunk: Chunk, score: float) -> Citation:
    excerpt = " ".join(chunk.text.split())
    if len(excerpt) > _EXCERPT:
        excerpt = excerpt[: _EXCERPT - 1].rstrip() + "…"
    return Citation(
        filename=chunk.filename,
        page=chunk.page,
        excerpt=excerpt,
        score=round(float(score), 4),
        doc_id=chunk.doc_id,
    )


def _log_ask(trace: RetrievalTrace, response: ChatResponse) -> None:
    try:
        from app.eval.query_log import append_query_log

        append_query_log(trace, response)
    except Exception:
        logger.exception("query log write failed")


def _latency_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
