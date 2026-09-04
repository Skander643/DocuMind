# DocuMind — Product Requirements

Enterprise document Q&A with retrieval-augmented generation.

**Domain (locked):** Tunisian / Tunisia labor law and employment regulations (public PDFs).  
**Languages:** French, Arabic, English.  
**Status:** Phase 5 Docker Compose + API key + rate limit.

## Problem

Companies and citizens cannot search dense legal PDFs effectively. Generic chatbots hallucinate on proprietary or jurisdictional text. DocuMind grounds every answer in retrieved passages and cites page-level sources.

## Goals

1. Upload and index multiple PDFs (labor codes, decrees, circulars).
2. Chat with source citations (filename, page, excerpt).
3. Add / remove / re-index documents.
4. Low-confidence fallback when retrieval is weak.
5. RAGAS evaluation dashboard on a fixed gold set (~50 questions).
6. Multilingual retrieval (FR / AR / EN) via BGE-M3 or multilingual-e5-large.

## Non-goals (Phase 0–2)

- Fine-tuning an LLM
- Multi-tenant SaaS / SSO
- Qdrant (ChromaDB first; Qdrant only if local Chroma fails at deploy)
- Wrapping the whole pipeline in LangChain/LlamaIndex chains

## Stack (frozen)

| Layer | Choice |
|---|---|
| API | FastAPI (Python 3.12) |
| Parsing | PyMuPDF |
| Chunking | Recursive character/token split, page metadata required |
| Embeddings | `BAAI/bge-m3` (fallback: `intfloat/multilingual-e5-large`) |
| Vector store | ChromaDB (persistent, local volume) |
| Reranker | `BAAI/bge-reranker-base` (CrossEncoder) |
| LLM | Gemini Flash via OpenRouter or Google AI Studio; Ollama/Mistral local fallback |
| Frontend | React + Vite + TypeScript |
| Deploy | Docker Compose |
| Eval | RAGAS (faithfulness, answer relevance, context precision/recall) |

LangChain / LlamaIndex: **splitters and PDF helpers only**, never as the orchestration layer.

## Pipeline (must not be redesigned without updating `docs/architecture.md`)

`PDF → parse pages → chunk + metadata → embed → Chroma`  
`query → embed → top-10 retrieve → rerank top 3–5 → confidence check → generate or refuse`

## API (target)

- `GET /health`
- `POST /chat` — `{ query, conversation_id? }` → `{ answer, citations, confidence, latency_ms }`
- `POST /documents` — upload PDF(s)
- `GET /documents` — list indexed docs
- `DELETE /documents/{doc_id}` — remove + re-index
- `POST /documents/{doc_id}/reindex`
- `GET /eval/summary` — latest RAGAS batch

Chat endpoint: API key auth (`X-API-Key` or `Authorization: Bearer`) + per-key/IP rate limit when `API_KEY` / `RATE_LIMIT_PER_MINUTE` are set. Health stays public.

## Citations

Every answer that is not a refusal must include:

```json
{ "filename": "code_travail.pdf", "page": 12, "excerpt": "...", "score": 0.81, "doc_id": "051c6b3d30defedc" }
```

If top rerank score is below threshold, do **not** call the LLM for a grounded answer. Return a low-confidence message.

## Eval (Phase 4)

- Gold set: `eval/gold_qa.json` (~50 questions written from the PDFs, not invented by the chat LLM)
- Metrics: faithfulness, answer relevance, context precision, context recall
- Log every query: question, retrieved chunks, reranked chunks, answer, latency (`eval/results/query_log.csv`)
- After each retrieval config change, re-run the 50 and record the delta in `docs/decisions.md`

## CV claim (fill after first eval run)

> Engineered a multilingual RAG Q&A system (BGE-M3 + reranker + Gemini Flash) over Tunisian labor-law PDFs; source-grounded citations and a RAGAS eval pipeline (faithfulness 98%, context precision 97%, context recall 99% on 47 gold questions; 3/3 out-of-corpus refusals).
