from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_cors_allows_vercel_origin() -> None:
    origin = "https://documind-orpin.vercel.app"
    response = client.options(
        "/api/chat",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_regex_covers_preview_deploy() -> None:
    origin = "https://documind-abc123-skander643s-projects.vercel.app"
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == origin
    assert settings.cors_origin_regex
