"""LLM generate: OpenRouter, else Gemini, else Ollama. Never invents labour-law answers."""

from __future__ import annotations

import logging
from collections.abc import Callable

import httpx

from app.config import settings
from app.ingest.chunking import Chunk
from app.ingest.language import detect_language
from app.rag.prompts import INSUFFICIENT_SENTINEL, build_prompt, refusal_message

logger = logging.getLogger(__name__)

GenerateFn = Callable[[str], str]
_TIMEOUT = 60.0


def generate(
    query: str,
    context: list[Chunk],
    *,
    openrouter_fn: GenerateFn | None = None,
    gemini_fn: GenerateFn | None = None,
    ollama_fn: GenerateFn | None = None,
) -> str:
    language = detect_language(query, min_chars=8)
    prompt = build_prompt(query, context, language)
    text = _complete(
        prompt,
        openrouter_fn=openrouter_fn,
        gemini_fn=gemini_fn,
        ollama_fn=ollama_fn,
    )
    cleaned = text.strip()
    if not cleaned or cleaned.startswith(INSUFFICIENT_SENTINEL):
        return refusal_message(language)
    return cleaned


def _complete(
    prompt: str,
    *,
    openrouter_fn: GenerateFn | None,
    gemini_fn: GenerateFn | None,
    ollama_fn: GenerateFn | None,
) -> str:
    errors: list[str] = []
    steps: list[tuple[str, GenerateFn]] = []

    if openrouter_fn is not None:
        steps.append(("openrouter", openrouter_fn))
    elif settings.openrouter_api_key and gemini_fn is None:
        steps.append(("openrouter", _openrouter))

    if gemini_fn is not None:
        steps.append(("gemini", gemini_fn))
    elif settings.gemini_api_key:
        steps.append(("gemini", _gemini))

    steps.append(("ollama", ollama_fn or _ollama))

    for name, call in steps:
        try:
            return call(prompt)
        except Exception as exc:
            logger.warning("%s failed, trying next: %s", name, exc)
            errors.append(f"{name}: {exc}")

    detail = "; ".join(errors) or "no LLM configured"
    raise RuntimeError(
        "No LLM available. Set OPENROUTER_API_KEY or GEMINI_API_KEY, "
        "or start Ollama. " + detail
    )


def _openrouter(prompt: str) -> str:
    url = settings.openrouter_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:5173",
        "X-Title": "DocuMind",
    }
    payload = {
        "model": settings.openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    response = httpx.post(url, headers=headers, json=payload, timeout=_TIMEOUT)
    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"
        )
    body = response.json()
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"OpenRouter response missing text: {body}") from exc
    if not str(text).strip():
        raise RuntimeError("OpenRouter returned an empty response")
    return str(text)


def _gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.2, "max_output_tokens": 1024},
    )
    text = getattr(response, "text", None) or ""
    if not text.strip():
        raise RuntimeError("Gemini returned an empty response")
    return text


def _ollama(prompt: str) -> str:
    url = settings.ollama_base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = httpx.post(url, json=payload, timeout=_TIMEOUT)
    response.raise_for_status()
    body = response.json()
    text = str(body.get("response") or "")
    if not text.strip():
        raise RuntimeError("Ollama returned an empty response")
    return text
