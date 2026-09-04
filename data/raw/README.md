# Source PDFs

14 public Tunisian labour-law PDFs are in this folder (ILO NATLEX + one CNSS form). See `SOURCES.md` for URLs.

- Prefer official gazettes / ministry / ILO mirrors.
- Grow toward 50–200 later (Arabic versions, Loi 2025-9, sectoral CCTs).
- `*.pdf` is gitignored. Do not commit copyrighted dumps if the license is unclear.

Phase 0 check:

```bash
cd backend
python -m app.ingest.ingest --list-only
```
