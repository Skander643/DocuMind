"""Grounded generation prompt and refusal copy."""

from __future__ import annotations

from app.ingest.chunking import Chunk

INSUFFICIENT_SENTINEL = "INSUFFICIENT_CONTEXT"

_REFUSAL = {
    "fr": (
        "Je n'ai pas assez de contexte dans les documents indexés pour répondre "
        "de façon fiable."
    ),
    "en": "I don't have enough confidence to answer from the indexed documents.",
    "ar": "لا أملك سياقاً كافياً في الوثائق المفهرسة للإجابة بثقة.",
    "unknown": (
        "Je n'ai pas assez de contexte dans les documents indexés pour répondre "
        "de façon fiable. / I don't have enough confidence to answer from the "
        "indexed documents."
    ),
}


def refusal_message(language: str) -> str:
    return _REFUSAL.get(language, _REFUSAL["unknown"])


def build_prompt(query: str, context: list[Chunk], language: str) -> str:
    passages: list[str] = []
    for i, chunk in enumerate(context, start=1):
        passages.append(
            f"[{i}] {chunk.filename} p.{chunk.page}\n{chunk.text.strip()}"
        )
    block = "\n\n".join(passages) if passages else "(none)"
    lang_line = {
        "fr": "Answer in French.",
        "ar": "Answer in Arabic.",
        "en": "Answer in English.",
    }.get(language, "Answer in the same language as the question.")
    return (
        "You are DocuMind, a retrieval-augmented assistant for Tunisian labour law.\n"
        "Answer ONLY from the numbered passages. Do not invent articles, dates, "
        "amounts, or procedure.\n"
        f"If the passages are insufficient, reply with exactly {INSUFFICIENT_SENTINEL} "
        "and nothing else.\n"
        "Do not add a bibliography; citations are attached separately.\n"
        f"{lang_line}\n\n"
        f"Passages:\n{block}\n\n"
        f"Question: {query.strip()}\n"
    )
