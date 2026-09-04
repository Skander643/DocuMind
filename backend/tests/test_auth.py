from fastapi.testclient import TestClient

from app.api.deps import pipeline_dep, reset_rate_limiter
from app.main import app
from app.models.schemas import ChatResponse

client = TestClient(app)


def _stub_pipeline() -> None:
    class Stub:
        def ask(self, query: str, conversation_id: str | None = None) -> ChatResponse:
            return ChatResponse(
                answer=f"echo:{query}",
                citations=[],
                confidence="high",
                latency_ms=1,
                conversation_id=conversation_id,
            )

    app.dependency_overrides[pipeline_dep] = lambda: Stub()


def test_chat_requires_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.api_key", "secret-test-key")
    _stub_pipeline()
    try:
        denied = client.post("/api/chat", json={"query": "Quelle est la durée du congé annuel ?"})
        assert denied.status_code == 401
        ok = client.post(
            "/api/chat",
            json={"query": "Quelle est la durée du congé annuel ?"},
            headers={"X-API-Key": "secret-test-key"},
        )
        assert ok.status_code == 200
        bearer = client.post(
            "/api/chat",
            json={"query": "Quelle est la durée du congé annuel ?"},
            headers={"Authorization": "Bearer secret-test-key"},
        )
        assert bearer.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_health_stays_public_with_api_key(monkeypatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.api_key", "secret-test-key")
    response = client.get("/health")
    assert response.status_code == 200


def test_document_write_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.api_key", "secret-test-key")
    denied = client.post(
        "/api/documents",
        files=[("files", ("loi.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert denied.status_code == 401
    listed = client.get("/api/documents")
    assert listed.status_code == 200


def test_chat_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.api_key", "")
    monkeypatch.setattr("app.api.deps.settings.rate_limit_per_minute", 2)
    reset_rate_limiter()
    _stub_pipeline()
    try:
        body = {"query": "Quelle est la durée du congé annuel ?"}
        assert client.post("/api/chat", json=body).status_code == 200
        assert client.post("/api/chat", json=body).status_code == 200
        limited = client.post("/api/chat", json=body)
        assert limited.status_code == 429
        assert "Retry-After" in limited.headers
    finally:
        reset_rate_limiter()
        app.dependency_overrides.clear()
