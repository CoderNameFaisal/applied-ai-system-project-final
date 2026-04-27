"""Configuration helpers for PawPal AI features."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_embedding_model: str
    log_level: str
    rag_collection_name: str
    rag_db_path: str
    rag_top_k: int


def load_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        log_level=os.getenv("PAWPAL_LOG_LEVEL", "INFO").strip().upper(),
        rag_collection_name="pawpal_knowledge",
        rag_db_path="data/chroma",
        rag_top_k=4,
    )

