# Architecture

DocuMind is a **custom retrieve → rerank → generate** pipeline. FastAPI owns orchestration. Vector search is ChromaDB. The LLM never sees the full corpus.

```
PDF Upload → Chunking + Embedding (BGE-M3)
                    ↓
            ChromaDB (persistent)
                    ↓
    User Query → Retrieve top-10 → Rerank → Gemini / Ollama
                    ↓
          FastAPI + React Chat UI (clickable page citations)
```

## Components

| Module | Path | Responsibility |
|---|---|---|
| Ingest | `backend/app/ingest/` | PyMuPDF per-page extract, chunk, embed, upsert |
| Catalog | `backend/app/ingest/catalog.py` | List / upload / delete / reindex; serve PDF bytes |
| Store | `backend/app/db/` | Chroma client, collection name, persistence path |
| Retrieve | `backend/app/rag/retriever.py` | Query embed + top-10 |
| Rerank | `backend/app/rag/reranker.py` | CrossEncoder, keep top 3–5 |
| Generate | `backend/app/rag/llm.py` | Gemini primary, Ollama fallback |
| Pipeline | `backend/app/rag/pipeline.py` | Glue + confidence gate |
| API | `backend/app/api/` | HTTP only — no embedding logic |
| Eval | `backend/app/eval/` | RAGAS-style batch, CSV query logs, `/eval/summary` |
| UI | `frontend/src/` | Chat, clickable citation cards, PDF page preview, doc list, eval scores |

## Chunk metadata (required on every vector)

- `doc_id` — stable id (hash of filename + size or uuid stored in a manifest)
- `filename`
- `page` — 1-based page index from PyMuPDF
- `text`
- `language` — `fr` / `ar` / `en` / `unknown` (detect at ingest)
- `chunk_index`

## Confidence gate

1. Retrieve `k=10`.
2. Rerank; keep `top_n=5`.
3. If best rerank score `< RERANK_MIN_SCORE` (see `docs/decisions.md`), return refusal. Do not generate a legal answer.
4. Else send query + reranked passages to the LLM with a strict grounded prompt.

## Prompt contract (generate phase)

- Answer **only** from provided context.
- Cite sources in the structured API field, not as invented footnotes.
- If context is insufficient: same refusal as the confidence gate.
- Prefer the document’s language when the user query is FR or AR.

## What is out of this diagram

Auth (`X-API-Key`) and chat rate limits live in `app/api/deps.py`. Docker networking is Compose. They must not leak into `pipeline.py`.
