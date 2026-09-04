# Decisions log

Record every retrieval/generation config change and the eval delta. Do not silently retune.

| Date | Decision | Value | Why | Eval delta |
|---|---|---|---|---|
| 2026-08-13 | Domain | Tunisian labor law PDFs | Unique, multilingual, public | — |
| 2026-08-13 | Orchestration | Custom Python, not LangChain chains | Interview-explainable pipeline | — |
| 2026-08-13 | Vector DB | ChromaDB persistent | Local, simple, Docker volume | — |
| 2026-08-13 | Embeddings | `BAAI/bge-m3` | FR + AR + EN | — |
| 2026-08-13 | Reranker | `BAAI/bge-reranker-base` | Cheap CrossEncoder lift | — |
| 2026-08-13 | Chunking (v0) | 512 tokens, 64 overlap, page-aware | Baseline before A/B | TBD |
| 2026-08-13 | Token proxy | 1 token ≈ 4 chars (no tokenizer in splitter) | Fast, no extra dep; A/B later vs HF tokenizer | TBD |
| 2026-08-13 | Torch | CPU wheel (`torch==2.6.0+cpu`) | Avoid multi-GB CUDA install on a laptop | — |
| 2026-08-13 | Retrieve k | 10 then rerank to 5 | Standard two-stage | TBD |
| 2026-08-13 | Confidence | `RERANK_MIN_SCORE` = 0.25 (placeholder) | Tune after first traces | TBD |
| 2026-09-02 | Rerank score | sigmoid(CrossEncoder logit) | Makes 0.25 a probability-like gate | TBD |
| 2026-09-02 | HF snapshots | Skip ONNX + `pytorch_model.bin` | Avoid duplicate GB downloads | — |
| 2026-08-13 | LLM | Gemini Flash API; Ollama Mistral fallback | Internship + offline demo | — |
| 2026-09-03 | LLM gateway | OpenRouter `google/gemini-2.5-flash` first if `OPENROUTER_API_KEY` is set | Gemini 2.0 Flash shut down June 2026; same Flash-class model via student OpenRouter key | — |
| 2026-09-03 | Eval metrics | RAGAS faithfulness / answer relevancy / context precision / recall via OpenRouter judge + BGE-M3 cosine; no LangChain orchestrator | ragas PyPI package pulls LangChain; keep the four metric names without wrapping `pipeline.py` | **Baseline** n=50 (47 RAGAS + 3 refuse): faithfulness 97.9%, answer relevancy 70.3%, context precision 97.3%, context recall 99.2%, refuse accuracy 100% |
| 2026-09-03 | Deploy | Compose + optional `API_KEY` + in-memory 20 chat req/min | Auth/rate limit stay in `app/api/deps.py`; CPU torch in the API image | — |

## How to update

After a config change: run `eval/gold_qa.json` through RAGAS, paste a new row, never overwrite the baseline row.
