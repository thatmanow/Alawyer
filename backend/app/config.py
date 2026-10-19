from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "alawyer"
    APP_DESCRIPTION: str = "alawyer 智能法律顾问平台 API"
    SECRET_KEY: str = "alawyer-jwt-secret-2026-please-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3307
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "alawyer123"
    MYSQL_DB: str = "alawyer_db"

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CHAT_CACHE_TTL: int = 86400

    NEO4J_URI: str = "bolt://127.0.0.1:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "alawyer12345"

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "qwen2.5:1.5b"
    EMBED_MODEL: str = "quentinz/bge-large-zh-v1.5:latest"
    EMBED_DIM: int = 1024
    LLM_TIMEOUT: int = 180

    RERANK_BASE_URL: str = "http://127.0.0.1:9999"

    CHROMA_DIR: str = str(BASE_DIR / "data" / "chroma")
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    SEED_DIR: str = str(BASE_DIR / "seed_docs")

    CHUNK_SIZE: int = 480
    CHUNK_OVERLAP: int = 80
    RAG_TOP_K: int = 8
    RERANK_TOP_N: int = 4
    RERANK_SCORE_THRESHOLD: float = 0.35

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()