from fastapi import APIRouter, HTTPException

from app.eval.ragas_eval import load_latest_summary
from app.models.schemas import EvalSummary

router = APIRouter(tags=["eval"])


@router.get("/eval/summary", response_model=EvalSummary)
def eval_summary() -> EvalSummary:
    data = load_latest_summary()
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="No eval results yet. Run: python -m app.eval",
        )
    return EvalSummary.model_validate(data)
