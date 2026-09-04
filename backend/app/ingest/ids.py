"""Stable document ids from filename + size (not mtime — re-index must stay stable)."""

from __future__ import annotations

import hashlib
from pathlib import Path


def make_doc_id(path: Path) -> str:
    size = path.stat().st_size if path.exists() else 0
    payload = f"{path.name}:{size}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def chunk_id(doc_id: str, chunk_index: int) -> str:
    return f"{doc_id}:{chunk_index}"
