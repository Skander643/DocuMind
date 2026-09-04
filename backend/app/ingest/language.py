"""Map langdetect codes to the three languages we care about."""

from __future__ import annotations

_ALLOWED = {"fr": "fr", "ar": "ar", "en": "en"}


def detect_language(text: str, min_chars: int = 20) -> str:
    sample = " ".join(text.split())[:2000]
    if len(sample) < min_chars:
        return "unknown"
    try:
        from langdetect import detect

        code = detect(sample)
    except Exception:
        return "unknown"
    return _ALLOWED.get(code, "unknown")
