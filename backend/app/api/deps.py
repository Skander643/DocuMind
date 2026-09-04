"""HTTP auth and rate limit. Deploy-only — never imported by pipeline.py."""

from __future__ import annotations

import hmac
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import settings
from app.rag.pipeline import Pipeline, get_pipeline


def pipeline_dep() -> Pipeline:
    return get_pipeline()


def require_api_key(request: Request) -> None:
    """No-op when API_KEY is unset (local pytest / open laptop)."""
    expected = settings.api_key
    if not expected:
        return
    provided = _extract_api_key(request)
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def require_write_access(request: Request) -> None:
    """Block corpus mutations on the public demo when no API_KEY is configured."""
    if settings.app_env == "prod" and not settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Document writes are disabled on the public demo.",
        )
    require_api_key(request)


def rate_limit_chat(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    key = _client_key(request)
    allowed, retry_after = _limiter.hit(key, limit)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )


def reset_rate_limiter() -> None:
    _limiter.reset()


def _extract_api_key(request: Request) -> str:
    header = request.headers.get("x-api-key") or ""
    if header.strip():
        return header.strip()
    auth = request.headers.get("authorization") or ""
    prefix = "bearer "
    if auth.lower().startswith(prefix):
        return auth[len(prefix) :].strip()
    return ""


def _client_key(request: Request) -> str:
    api_key = _extract_api_key(request) or settings.api_key
    if api_key:
        return f"key:{api_key[:16]}"
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


class _SlidingWindow:
    def __init__(self, window_s: float = 60.0) -> None:
        self.window_s = window_s
        self._hits: dict[str, list[float]] = defaultdict(list)

    def hit(self, key: str, limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_s
        bucket = [ts for ts in self._hits[key] if ts > cutoff]
        if len(bucket) >= limit:
            self._hits[key] = bucket
            retry = int(self.window_s - (now - bucket[0])) + 1
            return False, max(retry, 1)
        bucket.append(now)
        self._hits[key] = bucket
        return True, 0

    def reset(self) -> None:
        self._hits.clear()


_limiter = _SlidingWindow()
