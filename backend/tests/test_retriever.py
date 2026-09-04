from app.ingest.chunking import Chunk
from app.rag.retriever import retrieve


class _FakeCollection:
    def __init__(self, n: int, result: dict) -> None:
        self._n = n
        self._result = result

    def count(self) -> int:
        return self._n

    def query(self, **_kwargs) -> dict:
        return self._result


def test_retrieve_empty_query() -> None:
    assert retrieve("  ", embed_fn=lambda _: [[0.1]], collection=_FakeCollection(1, {})) == []


def test_retrieve_empty_store() -> None:
    assert retrieve("congé annuel", embed_fn=lambda _: [[0.1]], collection=_FakeCollection(0, {})) == []


def test_retrieve_maps_metadata_and_similarity() -> None:
    result = {
        "documents": [["Article 112. Congé annuel payé."]],
        "metadatas": [
            [
                {
                    "doc_id": "abc",
                    "filename": "code.pdf",
                    "page": 12,
                    "language": "fr",
                    "chunk_index": 3,
                }
            ]
        ],
        "distances": [[0.2]],
    }
    hits = retrieve(
        "durée du congé annuel",
        k=10,
        embed_fn=lambda texts: [[0.1] * 4],
        collection=_FakeCollection(1, result),
    )
    assert len(hits) == 1
    chunk, score = hits[0]
    assert isinstance(chunk, Chunk)
    assert chunk.filename == "code.pdf"
    assert chunk.page == 12
    assert chunk.chunk_index == 3
    assert score == 0.8
