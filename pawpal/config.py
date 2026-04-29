"""Configuration helpers for PawPal AI features."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    ai_api_key: str
    ai_model: str
    ai_embedding_model: str
    ai_base_url: str
    log_level: str
    rag_collection_name: str
    rag_db_path: str
    rag_top_k: int


def load_settings() -> Settings:
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    if provider not in {"gemini", "openai"}:
        provider = "gemini"

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    ai_key = gemini_key if provider == "gemini" else openai_key
    ai_model = os.getenv("AI_MODEL", "gemini-2.0-flash" if provider == "gemini" else "gpt-4.1-mini").strip()
    ai_embedding_model = os.getenv(
        "AI_EMBEDDING_MODEL",
        "text-embedding-004" if provider == "gemini" else "text-embedding-3-small",
    ).strip()
    ai_base_url = (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
        if provider == "gemini"
        else "https://api.openai.com/v1"
    )

    return Settings(
        ai_provider=provider,
        ai_api_key=ai_key,
        ai_model=ai_model,
        ai_embedding_model=ai_embedding_model,
        ai_base_url=ai_base_url,
        log_level=os.getenv("PAWPAL_LOG_LEVEL", "INFO").strip().upper(),
        rag_collection_name="pawpal_knowledge",
        rag_db_path="data/chroma",
        rag_top_k=4,
    )

