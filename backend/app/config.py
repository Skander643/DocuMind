from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DocuMind"
    app_env: str = "dev"
    api_prefix: str = "/api"

    data_raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    chroma_persist_dir: Path = PROJECT_ROOT / "data" / "chroma"

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-base"
    retrieve_k: int = 10
    rerank_top_n: int = 5
    rerank_min_score: float = 0.25
    chunk_size: int = 512
    chunk_overlap: int = 64

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-2.5-flash"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "mistral"

    api_key: str = ""
    rate_limit_per_minute: int = 20
    cors_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "https://documind-orpin.vercel.app,"
        "https://documind-skander643s-projects.vercel.app"
    )
    cors_origin_regex: str = r"https://documind.*\.vercel\.app"


settings = Settings()
