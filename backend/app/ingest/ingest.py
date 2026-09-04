"""CLI: walk data/raw → parse → chunk → embed → Chroma."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import settings
from app.ingest.catalog import list_pdfs, merge_manifest_rows
from app.ingest.chunking import Chunk, split_page_text
from app.ingest.ids import make_doc_id
from app.ingest.language import detect_language
from app.ingest.parse import extract_pages


def chunk_pdf(path: Path) -> list[Chunk]:
    doc_id = make_doc_id(path)
    pages = extract_pages(path)
    chunks: list[Chunk] = []
    for page in pages:
        language = detect_language(page.text)
        page_chunks = split_page_text(
            page.text,
            doc_id=doc_id,
            filename=path.name,
            page=page.page,
            language=language,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            start_index=len(chunks),
        )
        chunks.extend(page_chunks)
    return chunks


def run_ingest(
    raw_dir: Path | None = None,
    *,
    limit: int | None = None,
    filenames: list[str] | None = None,
    reset: bool = False,
    dry_run: bool = False,
) -> dict:
    pdfs = list_pdfs(raw_dir)
    if filenames:
        wanted = set(filenames)
        pdfs = [p for p in pdfs if p.name in wanted]
    if limit is not None:
        pdfs = pdfs[:limit]

    print(f"Found {len(pdfs)} PDF(s) in {raw_dir or settings.data_raw_dir}")
    for path in pdfs:
        print(f"  - {path.name}")
    if not pdfs:
        print("Add public labor-law PDFs to data/raw/ then re-run.")
        return {"documents": 0, "chunks": 0}

    if reset and not dry_run:
        from app.db.chroma_client import get_client

        client = get_client()
        try:
            client.delete_collection("documind_labor_law")
            print("Reset: dropped collection documind_labor_law")
        except Exception:
            pass

    manifest: list[dict] = []
    total_chunks = 0
    for path in pdfs:
        chunks = chunk_pdf(path)
        print(f"{path.name}: {len(chunks)} chunk(s)")
        if not dry_run:
            from app.db.chroma_client import delete_doc, upsert_chunks
            from app.rag.embeddings import embed_texts

            delete_doc(make_doc_id(path))
            if chunks:
                embeddings = embed_texts([c.text for c in chunks])
                upsert_chunks(chunks, embeddings)
        total_chunks += len(chunks)
        manifest.append(
            {
                "doc_id": make_doc_id(path),
                "filename": path.name,
                "n_chunks": len(chunks),
                "language": chunks[0].language if chunks else "unknown",
            }
        )

    written = merge_manifest_rows(
        manifest,
        raw_dir=raw_dir or settings.data_raw_dir,
        replace=reset,
    )
    print(f"Wrote {written}")
    stored = 0
    if not dry_run:
        from app.db.chroma_client import count_chunks, sample_records

        stored = count_chunks()
        _print_samples(sample_records(3))
    print(f"Indexed {total_chunks} chunk(s). Chroma count={stored}")
    return {"documents": len(pdfs), "chunks": total_chunks, "chroma": stored}


def _print_samples(rows: list[dict]) -> None:
    if not rows:
        print("No sample chunks in Chroma.")
        return
    print("Sample chunks:")
    for i, row in enumerate(rows, start=1):
        excerpt = " ".join(str(row.get("text") or "").split())[:180]
        print(
            f"  {i}. {row.get('filename')} p.{row.get('page')} "
            f"[{row.get('language')}] idx={row.get('chunk_index')}"
        )
        print(f"     {excerpt}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DocuMind PDF ingest")
    parser.add_argument("--list-only", action="store_true", help="List PDFs without indexing")
    parser.add_argument("--limit", type=int, default=None, help="Index only the first N PDFs")
    parser.add_argument("--reset", action="store_true", help="Drop the Chroma collection first")
    parser.add_argument(
        "--file",
        action="append",
        dest="filenames",
        default=None,
        help="Only index these filenames (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk only (no embeddings / Chroma)",
    )
    args = parser.parse_args(argv)
    if args.list_only:
        pdfs = list_pdfs()
        print(f"{len(pdfs)} PDF(s)")
        for path in pdfs:
            print(path)
        return 0
    run_ingest(
        limit=args.limit,
        filenames=args.filenames,
        reset=args.reset,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
