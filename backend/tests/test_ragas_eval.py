from app.eval.ragas_eval import run_batch
from app.ingest.chunking import Chunk
from app.models.schemas import ChatResponse
from app.rag.pipeline import Pipeline, RetrievalTrace


def test_run_batch_mocked(tmp_path, monkeypatch) -> None:
    gold = tmp_path / "gold.json"
    gold.write_text(
        """
{
  "items": [
    {
      "id": "q001",
      "question": "Quelle est la durée du congé annuel payé ?",
      "ground_truth": "quinze jours",
      "language": "fr",
      "source_hint": "code.pdf:76",
      "expect_refuse": false
    },
    {
      "id": "q002",
      "question": "What is the capital of Australia?",
      "ground_truth": "refuse",
      "language": "en",
      "source_hint": "",
      "expect_refuse": true
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    chunk = Chunk("d", "code.pdf", 76, "quinze jours ouvrables article 113", "fr", 0)

    class Stub(Pipeline):
        def ask_with_trace(self, query, conversation_id=None, *, use_rerank=True):
            if "Australia" in query:
                response = ChatResponse(
                    answer="I don't have enough confidence to answer from the indexed documents.",
                    citations=[],
                    confidence="low",
                    latency_ms=3,
                )
                trace = RetrievalTrace(query=query)
                return response, trace
            response = ChatResponse(
                answer="quinze jours comprenant douze jours ouvrables",
                citations=[],
                confidence="high",
                latency_ms=9,
            )
            trace = RetrievalTrace(
                query=query,
                retrieved=[(chunk, 0.7)],
                reranked=[(chunk, 0.9)],
                used=[(chunk, 0.9)],
            )
            return response, trace

    monkeypatch.setattr("app.eval.ragas_eval.RESULTS_DIR", tmp_path)
    payload = run_batch(
        gold,
        pipeline=Stub(),
        judge_fn=lambda prompt: '{"score": 1.0, "relevant": [true]}',
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    assert payload["n_questions"] == 2
    assert payload["metrics"]["faithfulness"] == 1.0
    assert payload["metrics"]["refuse_accuracy"] == 1.0
    assert (tmp_path / "latest.json").is_file()
