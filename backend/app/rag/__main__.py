"""CLI: run one query, optionally compare retrieve-only vs retrieve+rerank."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.rag.pipeline import Pipeline, RetrievalTrace


def _print_hits(title: str, hits: list, limit: int | None = None) -> None:
    print(title)
    if not hits:
        print("  (none)")
        return
    rows = hits if limit is None else hits[:limit]
    for i, (chunk, score) in enumerate(rows, start=1):
        excerpt = " ".join(chunk.text.split())[:120]
        print(
            f"  {i}. {chunk.filename} p.{chunk.page}  score={score:.3f}  {excerpt}"
        )


def _trace_table(trace: RetrievalTrace) -> None:
    _print_hits(f"Retrieved (k={len(trace.retrieved)})", trace.retrieved)
    if trace.use_rerank:
        _print_hits(f"Reranked (n={len(trace.reranked)})", trace.reranked)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DocuMind RAG query (Phase 2)")
    parser.add_argument("--query", required=True, help="User question")
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Skip CrossEncoder; use Chroma order truncated to rerank_top_n",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Print retrieve vs rerank lists for the same query",
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Do not call OpenRouter/Gemini/Ollama (retrieval trace only)",
    )
    parser.add_argument("--json", action="store_true", help="Dump ChatResponse JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pipeline = Pipeline()

    if args.compare or args.no_generate:
        with_rerank = pipeline.trace(args.query, use_rerank=True)
        without = pipeline.trace(args.query, use_rerank=False)
        print("=== with rerank ===")
        _trace_table(with_rerank)
        print("=== without rerank ===")
        _print_hits("Used (Chroma top-n)", without.used)
        if args.no_generate:
            return 0

    use_rerank = not args.no_rerank
    try:
        result = pipeline.ask(args.query, use_rerank=use_rerank)
    except RuntimeError as exc:
        print(f"Generation failed: {exc}")
        return 2
    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    print(f"confidence={result.confidence}  latency_ms={result.latency_ms}")
    print(result.answer)
    if result.citations:
        print("citations:")
        for citation in result.citations:
            print(f"  - {citation.filename} p.{citation.page} ({citation.score})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
