import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, eval as eval_routes, health
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
origin_regex = settings.cors_origin_regex.strip() or None
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(eval_routes.router, prefix=settings.api_prefix)


def _warmup_models() -> None:
    try:
        from app.rag.embeddings import get_model
        from app.rag.reranker import get_cross_encoder

        get_model()
        get_cross_encoder()
        logger.info("embedding and reranker models ready")
    except Exception:
        logger.exception("model warmup failed")


if settings.app_env == "prod":
    threading.Thread(target=_warmup_models, daemon=True, name="model-warmup").start()

