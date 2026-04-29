"""Thin OpenAI client wrapper with retries and guardrails."""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from pawpal.config import load_settings
from pawpal.logging_utils import get_logger

logger = get_logger("pawpal.ai.client")


def _provider_name(provider: str) -> str:
    return "Gemini" if provider == "gemini" else "OpenAI"


def _api_key_name(provider: str) -> str:
    return "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"


def _is_non_retryable_auth_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code in {401, 403}:
        return True

    message = str(error).lower()
    auth_indicators = {
        "api_key_invalid",
        "api key expired",
        "invalid api key",
        "incorrect api key",
        "authentication",
    }
    return any(indicator in message for indicator in auth_indicators)


def get_openai_client() -> OpenAI:
    settings = load_settings()
    if not settings.ai_api_key:
        raise RuntimeError(f"{_api_key_name(settings.ai_provider)} is not configured.")
    return OpenAI(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        timeout=30.0,
        max_retries=0,
    )


def call_with_retries(callable_fn: Any, retries: int = 2, backoff_seconds: float = 1.0) -> Any:
    settings = load_settings()
    provider_name = _provider_name(settings.ai_provider)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return callable_fn()
        except Exception as error:  # pragma: no cover - intentionally broad wrapper
            last_error = error
            logger.warning("%s call failed on attempt %s: %s", provider_name, attempt + 1, error)
            if _is_non_retryable_auth_error(error):
                logger.error(
                    "%s authentication failed. Check %s.",
                    provider_name,
                    _api_key_name(settings.ai_provider),
                )
                raise error
            if attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
    if last_error is None:
        raise RuntimeError(f"{provider_name} call failed without exception details.")
    raise last_error

