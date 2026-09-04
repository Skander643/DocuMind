from typing import Any, Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    filename: str
    page: int
    excerpt: str
    score: float
    doc_id: str = ""


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Literal["high", "low"]
    latency_ms: int
    conversation_id: str | None = None


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    n_chunks: int = 0
    language: str | None = None
    status: str = "pending"


class EvalSummary(BaseModel):
    created_at: str | None = None
    n_questions: int
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    refuse_accuracy: float | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    phase: str
    app: str
