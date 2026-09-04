from pathlib import Path

from app.eval.query_log import append_query_log
from app.ingest.chunking import Chunk
from app.models.schemas import ChatResponse
from app.rag.pipeline import RetrievalTrace


def test_append_query_log_writes_csv(tmp_path: Path) -> None:
    chunk = Chunk("d", "code.pdf", 76, "congé annuel", "fr", 0)
    trace = RetrievalTrace(
        query="Quelle est la durée du congé annuel payé ?",
        retrieved=[(chunk, 0.7)],
        reranked=[(chunk, 0.9)],
        used=[(chunk, 0.9)],
    )
    response = ChatResponse(
        answer="Un jour par mois.",
        citations=[],
        confidence="high",
        latency_ms=12,
        conversation_id="c1",
    )
    dest = tmp_path / "query_log.csv"
    written = append_query_log(trace, response, path=dest)
    assert written == dest
    text = dest.read_text(encoding="utf-8")
    assert "congé annuel" in text
    assert "code.pdf:76:0.9000" in text
    assert "high" in text
