from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAG_NANO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    index_dir: Path = Path("./.rag-nano")
    embedding_model: str = "intfloat/multilingual-e5-base"
    embedding_backend: str = "local"
    vector_store: str = "numpy_flat"
    structured_store: str = "sqlite"
    reranker: str = "identity"
    log_level: str = "INFO"
    http_host: str = "127.0.0.1"
    http_port: int = 8089

    @classmethod
    def from_env(cls) -> Settings:
        return cls()
