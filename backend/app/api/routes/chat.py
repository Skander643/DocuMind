from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import pipeline_dep, rate_limit_chat, require_api_key
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.pipeline import Pipeline

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    pipeline: Pipeline = Depends(pipeline_dep),
    _: None = Depends(require_api_key),
    __: None = Depends(rate_limit_chat),
) -> ChatResponse:
    try:
        return pipeline.ask(body.query, body.conversation_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
