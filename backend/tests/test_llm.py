from app.ingest.chunking import Chunk
from app.rag.llm import generate
from app.rag.prompts import INSUFFICIENT_SENTINEL, refusal_message


def test_generate_uses_openrouter(monkeypatch) -> None:
    monkeypatch.setattr("app.rag.llm.settings.openrouter_api_key", "sk-or-test")
    monkeypatch.setattr("app.rag.llm.settings.gemini_api_key", "")
    chunks = [
        Chunk("d", "code.pdf", 1, "Le congé annuel est de 12 jours.", "fr", 0),
    ]
    answer = generate(
        "Quelle est la durée du congé annuel payé ?",
        chunks,
        openrouter_fn=lambda _p: "12 jours ouvrables selon le passage.",
        ollama_fn=lambda _p: "SHOULD_NOT_RUN",
    )
    assert "12 jours" in answer


def test_generate_uses_gemini(monkeypatch) -> None:
    monkeypatch.setattr("app.rag.llm.settings.gemini_api_key", "test-key")
    chunks = [
        Chunk("d", "code.pdf", 1, "Le congé annuel est de 12 jours.", "fr", 0),
    ]
    answer = generate(
        "Quelle est la durée du congé annuel payé ?",
        chunks,
        gemini_fn=lambda prompt: "12 jours ouvrables selon le passage.",
        ollama_fn=lambda _p: "SHOULD_NOT_RUN",
    )
    assert "12 jours" in answer


def test_generate_falls_back_to_ollama(monkeypatch) -> None:
    monkeypatch.setattr("app.rag.llm.settings.gemini_api_key", "test-key")
    answer = generate(
        "Quelle est la durée du congé annuel payé ?",
        [],
        gemini_fn=lambda _p: (_ for _ in ()).throw(RuntimeError("quota")),
        ollama_fn=lambda _p: "réponse locale",
    )
    assert answer == "réponse locale"


def test_generate_sentinel_becomes_refusal() -> None:
    answer = generate(
        "Quelle est la durée du congé annuel payé ?",
        [],
        gemini_fn=lambda _p: INSUFFICIENT_SENTINEL,
        ollama_fn=lambda _p: "SHOULD_NOT_RUN",
    )
    assert answer == refusal_message("fr")
