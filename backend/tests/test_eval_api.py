from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_eval_summary_404_without_results(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.eval.load_latest_summary", lambda: None)
    response = client.get("/api/eval/summary")
    assert response.status_code == 404


def test_eval_summary_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.eval.load_latest_summary",
        lambda: {
            "created_at": "2026-09-03T10:00:00+00:00",
            "n_questions": 50,
            "faithfulness": 0.81,
            "answer_relevancy": 0.77,
            "context_precision": 0.72,
            "context_recall": 0.69,
            "refuse_accuracy": 1.0,
            "config": {"retrieve_k": 10},
        },
    )
    response = client.get("/api/eval/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["n_questions"] == 50
    assert body["faithfulness"] == 0.81
    assert body["refuse_accuracy"] == 1.0
