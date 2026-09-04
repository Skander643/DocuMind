from app.ingest.chunking import Chunk
from app.models.schemas import ChatResponse
from app.rag.pipeline import Pipeline
from app.rag.prompts import refusal_message


def _chunk(filename: str, page: int, text: str) -> Chunk:
    return Chunk("d", filename, page, text, "fr", page)


def test_same_query_order_changes_with_rerank() -> None:
    retrieved = [
        (_chunk("noisy.pdf", 1, "horaire de nuit"), 0.71),
        (_chunk("code.pdf", 40, "congé annuel payé de douze jours"), 0.70),
        (_chunk("other.pdf", 2, "formation professionnelle"), 0.69),
    ]

    def fake_retrieve(query: str, k: int) -> list:
        assert "congé" in query
        assert k == 10
        return retrieved

    def fake_rerank(query: str, chunks: list[Chunk], top_n: int) -> list:
        assert top_n == 5
        by_name = {chunk.filename: chunk for chunk in chunks}
        return [
            (by_name["code.pdf"], 0.91),
            (by_name["noisy.pdf"], 0.40),
            (by_name["other.pdf"], 0.21),
        ]

    pipeline = Pipeline(
        retrieve_fn=fake_retrieve,
        rerank_fn=fake_rerank,
        generate_fn=lambda _q, ctx: f"grounded:{ctx[0].filename}",
    )
    query = "Quelle est la durée du congé annuel payé ?"
    with_rerank = pipeline.ask(query, use_rerank=True)
    without = pipeline.ask(query, use_rerank=False)

    assert with_rerank.citations[0].filename == "code.pdf"
    assert with_rerank.citations[0].doc_id == "d"
    assert without.citations[0].filename == "noisy.pdf"
    assert with_rerank.answer == "grounded:code.pdf"
    assert without.answer == "grounded:noisy.pdf"


def test_low_rerank_score_skips_llm() -> None:
    def fake_retrieve(_query: str, _k: int) -> list:
        return [(_chunk("weak.pdf", 1, "sans rapport"), 0.11)]

    def fake_rerank(_query: str, chunks: list[Chunk], _top_n: int) -> list:
        return [(chunks[0], 0.05)]

    def boom(_q: str, _ctx: list[Chunk]) -> str:
        raise AssertionError("LLM must not run on a weak retrieval")

    pipeline = Pipeline(retrieve_fn=fake_retrieve, rerank_fn=fake_rerank, generate_fn=boom)
    result = pipeline.ask("Quelle est la durée du congé annuel payé ?")
    assert result.confidence == "low"
    assert result.answer == refusal_message("fr")
    assert result.citations[0].filename == "weak.pdf"


def test_empty_retrieval_refuses() -> None:
    pipeline = Pipeline(
        retrieve_fn=lambda _q, _k: [],
        rerank_fn=lambda *_a, **_k: [],
        generate_fn=lambda *_a, **_k: "nope",
    )
    result = pipeline.ask("Quelle est la durée du congé annuel payé ?")
    assert result.confidence == "low"
    assert result.citations == []


def test_llm_refusal_lowers_confidence() -> None:
    chunk = _chunk("code.pdf", 3, "texte")
    pipeline = Pipeline(
        retrieve_fn=lambda _q, _k: [(chunk, 0.9)],
        rerank_fn=lambda _q, chunks, _n: [(chunks[0], 0.9)],
        generate_fn=lambda _q, _c: refusal_message("fr"),
    )
    result: ChatResponse = pipeline.ask("Quelle est la durée du congé annuel payé ?")
    assert result.confidence == "low"
    assert result.answer == refusal_message("fr")
