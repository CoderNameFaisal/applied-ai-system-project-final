"""Thin OpenAI client wrapper with retries and guardrails."""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from pawpal.config import load_settings
from pawpal.logging_utils import get_logger

logger = get_logger("pawpal.ai.client")


def get_openai_client() -> OpenAI:
    settings = load_settings()
    if not settings.ai_api_key:
        key_name = "GEMINI_API_KEY" if settings.ai_provider == "gemini" else "OPENAI_API_KEY"
        raise RuntimeError(f"{key_name} is not configured.")
    return OpenAI(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        timeout=30.0,
        max_retries=0,
    )


def call_with_retries(callable_fn: Any, retries: int = 2, backoff_seconds: float = 1.0) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return callable_fn()
        except Exception as error:  # pragma: no cover - intentionally broad wrapper
            last_error = error
            logger.warning("OpenAI call failed on attempt %s: %s", attempt + 1, error)
            if attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
    if last_error is None:
        raise RuntimeError("OpenAI call failed without exception details.")
    raise last_error

