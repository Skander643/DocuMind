from fastapi.testclient import TestClient

from app.api.deps import pipeline_dep
from app.main import app
from app.models.schemas import ChatResponse

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["phase"] == "5"
    assert body["app"] == "DocuMind"


def test_chat_uses_pipeline() -> None:
    class Stub:
        def ask(self, query: str, conversation_id: str | None = None) -> ChatResponse:
            return ChatResponse(
                answer=f"echo:{query}",
                citations=[],
                confidence="high",
                latency_ms=4,
                conversation_id=conversation_id,
            )

    app.dependency_overrides[pipeline_dep] = lambda: Stub()
    try:
        response = client.post(
            "/api/chat",
            json={"query": "Quelle est la durée du congé annuel ?"},
        )
        assert response.status_code == 200
        assert response.json()["answer"].startswith("echo:")
        assert response.json()["confidence"] == "high"
    finally:
        app.dependency_overrides.clear()


def test_chat_llm_unavailable() -> None:
    class Stub:
        def ask(self, query: str, conversation_id: str | None = None) -> ChatResponse:
            raise RuntimeError("No LLM available")

    app.dependency_overrides[pipeline_dep] = lambda: Stub()
    try:
        response = client.post("/api/chat", json={"query": "test question longue assez"})
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_list_documents_ok() -> None:
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
