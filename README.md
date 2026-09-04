# DocuMind

Multilingual RAG assistant for **Tunisian labor law** PDFs. Answers are grounded in retrieved pages, reranked, and cited. Weak retrieval refuses instead of hallucinating.

> Portfolio project — DS/AI engineering. Phase 5: Docker Compose + API key + rate limit.  
> Source: [github.com/Skander643/DocuMind](https://github.com/Skander643/DocuMind) · UI: [documind-orpin.vercel.app](https://documind-orpin.vercel.app)

## Pipeline

```
PDF → PyMuPDF → chunk (+ page metadata) → BGE-M3 → ChromaDB
query → retrieve top-10 → bge-reranker-base → Gemini / Ollama → citations
```

## RAGAS metrics (baseline, n=50)

| Metric | Score |
|---|---|
| Faithfulness | 97.9% |
| Answer relevancy | 70.3% |
| Context precision | 97.3% |
| Context recall | 99.2% |
| Out-of-corpus refuse | 3/3 |

47 grounded gold questions + 3 `expect_refuse`. Full log: `docs/decisions.md`. Re-run `python -m app.eval` after retrieval config changes.

## Repo layout

| Path | Role |
|---|---|
| `prd.md` | Product spec (source of truth) |
| `docs/architecture.md` | Retrieve → rerank → generate |
| `docs/decisions.md` | Model/chunk/threshold log + eval deltas |
| `backend/` | FastAPI, ingest, RAG, eval |
| `frontend/` | Vite + React + TypeScript chat UI |
| `data/raw/` | Source PDFs (gitignored, not committed) |
| `eval/gold_qa.json` | Gold questions (Phase 4) |
| `docker-compose.yml` | API + nginx frontend |

## Prerequisites

- Python 3.12, Node 22+, Docker Compose
- OpenRouter or Gemini API key; optional Ollama

## Docker demo (Phase 5)

Stop the local uvicorn (`8001`) and Vite (`5173`) first if you want the default ports. Compose maps the **API to host `API_HOST_PORT` (default 8000)** and the **UI to host `FRONTEND_HOST_PORT` (default 5173)**. If another stack already owns 8000 (for example `visiinspect-api`) or Vite owns 5173, set those variables in `.env` (this laptop often needs `8002` and `5174`).

```bash
cp .env.example .env   # then set OPENROUTER_API_KEY (and optionally API_KEY)

# Optional: a random key. Nginx injects X-API-Key for the browser.
# Leave empty for an open local demo. Health stays public either way.
# API_KEY=$(openssl rand -hex 16)

docker compose up --build
```

- UI: [http://127.0.0.1:5173](http://127.0.0.1:5173) (or `FRONTEND_HOST_PORT`)
- API health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) (or `API_HOST_PORT`)

First API image build installs CPU PyTorch (slow). First chat may still load BGE-M3 / the reranker; Hugging Face cache is bind-mounted from `~/.cache/huggingface`. Chat is limited to **20 requests / minute** per client (`RATE_LIMIT_PER_MINUTE`). Document uploads and deletes require `API_KEY` when it is set.

Direct API calls when `API_KEY` is set:

```bash
curl -s http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $API_KEY" \
  -d '{"query":"Quelle est la durée du congé annuel payé ?"}'
```

## Local quick start (no Docker)

```bash
cp .env.example .env

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-phase0.txt
pytest -q
uvicorn app.main:app --reload --app-dir . --port 8001

# frontend (another terminal)
cd frontend
npm install
npm run dev
```

Local API uses **8001** so it does not clash with other Docker apps on 8000. Vite on 5173 proxies `/api` and `/health` to 8001. Leave `API_KEY` empty so pytest and the open laptop UI work without a header. If you set `API_KEY` locally, also set `VITE_API_KEY` in `frontend/.env`.

Phase 1 ingest stack:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-phase1.txt
python -m app.ingest --dry-run          # parse + chunk only
python -m app.ingest --limit 1          # smoke: one PDF into Chroma
python -m app.ingest --reset            # full corpus (downloads BGE-M3 once)
```

Chroma data: `data/chroma/`. Manifest: `data/processed/manifest.json`.

Phase 2 query (same question with and without the reranker):

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-phase2.txt   # google-generativeai
python -m app.rag --query "Quelle est la durée du congé annuel payé ?" --compare --no-generate
# needs OPENROUTER_API_KEY or GEMINI_API_KEY in .env
python -m app.rag --query "Quelle est la durée du congé annuel payé ?"
```

API health: [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)  
UI: [http://127.0.0.1:5173](http://127.0.0.1:5173)

Phase 3 (chat + citations + documents): leave the API running, start the Vite app, then ask a question. Click a citation card to open that PDF page. Upload / reindex / delete from the sidebar.

`GET /api/documents/{doc_id}/file` streams the PDF (`#page=N` for the cited page).

Phase 4 (gold set + RAGAS + query logs):

```bash
cd backend
source .venv/bin/activate
python -m app.eval                 # 50 questions; writes eval/results/latest.json
python -m app.eval --limit 3       # smoke
```

`GET /api/eval/summary` feeds the sidebar scores. Chat traces append to `eval/results/query_log.csv`. Re-run after retrieval config changes and add a row in `docs/decisions.md`.

## Roadmap

1. **Phase 0** — scaffold, Cursor rules, health endpoint
2. **Phase 1** — ingest PDFs into Chroma with page metadata
3. **Phase 2** — retrieve → rerank → generate + confidence gate
4. **Phase 3** — `/chat` + citation UI + document management
5. **Phase 4** — RAGAS on ~50 gold questions, query logging
6. **Phase 5** — Docker Compose, API key, rate limit, deploy

## Hosting

- **GitHub:** [https://github.com/Skander643/DocuMind](https://github.com/Skander643/DocuMind)
- **Vercel UI:** [https://documind-orpin.vercel.app](https://documind-orpin.vercel.app)
- **API:** [https://api-production-4d57.up.railway.app](https://api-production-4d57.up.railway.app) (Railway). `VITE_API_URL` on Vercel points here.

Vercel hosts the React UI (`frontend/`). The RAG API (PyTorch, BGE-M3, Chroma) runs on Railway. Public chat is rate-limited; document upload/delete is disabled unless `API_KEY` is set. Local Docker Compose remains the full laptop demo. `fly.toml` is there if you switch hosts after adding a Fly.io payment method.

## Working with Cursor

Tag `@prd.md` and the one module you are changing. Implement one phase at a time. See `AGENTS.md`.
