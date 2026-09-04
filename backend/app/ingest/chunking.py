"""Page-aware recursive splitter. chunk_size/overlap are token budgets (~4 chars/token)."""

from __future__ import annotations

from dataclasses import dataclass

CHARS_PER_TOKEN = 4
SEPARATORS = ("\n\n", "\n", ". ", " ", "")


@dataclass
class Chunk:
    doc_id: str
    filename: str
    page: int
    text: str
    language: str
    chunk_index: int


def split_page_text(
    text: str,
    *,
    doc_id: str,
    filename: str,
    page: int,
    language: str,
    chunk_size: int,
    chunk_overlap: int,
    start_index: int = 0,
) -> list[Chunk]:
    cleaned = text.strip()
    if not cleaned:
        return []

    size_chars = max(chunk_size * CHARS_PER_TOKEN, 1)
    overlap_chars = max(chunk_overlap * CHARS_PER_TOKEN, 0)
    windows = _window_with_overlap(_recursive_split(cleaned, size_chars), size_chars, overlap_chars)
    return [
        Chunk(
            doc_id=doc_id,
            filename=filename,
            page=page,
            text=window,
            language=language,
            chunk_index=start_index + i,
        )
        for i, window in enumerate(windows)
        if window.strip()
    ]


def _recursive_split(text: str, size: int, separators: tuple[str, ...] = SEPARATORS) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []

    sep, *rest = separators
    if sep == "":
        return [text[i : i + size] for i in range(0, len(text), size) if text[i : i + size].strip()]

    pieces = text.split(sep)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}{sep}{piece}" if current else piece
        if len(candidate) <= size:
            current = candidate
            continue
        if current.strip():
            chunks.append(current.strip())
        if len(piece) > size:
            chunks.extend(_recursive_split(piece, size, tuple(rest)))
            current = ""
        else:
            current = piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _window_with_overlap(parts: list[str], size: int, overlap: int) -> list[str]:
    if not parts:
        return []
    if overlap <= 0 or len(parts) == 1:
        return parts

    out: list[str] = []
    tail = ""
    for part in parts:
        merged = f"{tail} {part}".strip() if tail else part
        if len(merged) <= size:
            out.append(merged)
        else:
            out.append(part)
        tail = part[-overlap:] if len(part) > overlap else part
    return out
