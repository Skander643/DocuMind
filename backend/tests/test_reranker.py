from app.ingest.chunking import Chunk
from app.rag.reranker import rerank


def _chunk(name: str, page: int) -> Chunk:
    return Chunk(
        doc_id="d",
        filename=name,
        page=page,
        text=f"passage {name} {page}",
        language="fr",
        chunk_index=page,
    )


def test_rerank_empty() -> None:
    assert rerank("q", []) == []


def test_rerank_orders_by_sigmoid_score() -> None:
    a = _chunk("a.pdf", 1)
    b = _chunk("b.pdf", 2)
    c = _chunk("c.pdf", 3)
    # logits: low, high, mid → order b, c, a after sigmoid
    ranked = rerank(
        "congé",
        [a, b, c],
        top_n=2,
        predict_fn=lambda _pairs: [-2.0, 3.0, 0.1],
    )
    assert [chunk.filename for chunk, _ in ranked] == ["b.pdf", "c.pdf"]
    assert ranked[0][1] > ranked[1][1]
    assert 0.0 < ranked[1][1] < 1.0
