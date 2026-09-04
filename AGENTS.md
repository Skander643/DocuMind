# Agent instructions (DocuMind)

You are implementing a student portfolio RAG system. Optimize for a **clear, testable pipeline**, not a framework demo.

## Before coding

1. Read `prd.md` and `docs/architecture.md`.
2. Check `docs/decisions.md` before changing models, chunk size, or thresholds.
3. Implement **one phase / one module** per turn. Do not “finish the app.”

## Phases (do not skip ahead)

| Phase | Deliverable | Done when |
|---|---|---|
| 0 | Scaffold, rules, health endpoint | Done |
| 1 | Ingest CLI → Chroma with page metadata | Done |
| 2 | `pipeline.py` retrieve → rerank → generate + tests | Done |
| 3 | FastAPI `/chat` + React citations | Done |
| 4 | RAGAS batch + query logs | Done |
| 5 | Docker, API key, rate limit, README metrics | Done |

## Rules of change

- Do not add libraries not listed in `backend/requirements.txt` / `prd.md` without updating both.
- Do not put secrets in git. Use `.env`.
- API routers must not call embedding models directly; they call `rag.pipeline`.
- Every chunk written to Chroma must include `filename` and `page`.
- If retrieval is weak, refuse. Never invent labor-law answers.
- Match existing module style. No drive-by refactors.
- Prefer small functions with type hints and docstrings.

## Verification the agent should run

- Backend: `cd backend && pytest -q` (when tests exist)
- Ingest smoke: list PDFs under `data/raw/`
- Do not download large embedding weights unless the user asked to run ingest
- Phase 5: `docker compose up --build` then `curl -s http://127.0.0.1:8000/health`
