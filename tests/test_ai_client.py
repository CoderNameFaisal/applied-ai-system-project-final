from types import SimpleNamespace

import pytest

from pawpal.ai.client import call_with_retries


class FakeStatusError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def test_call_with_retries_fails_fast_for_auth_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "pawpal.ai.client.load_settings",
        lambda: SimpleNamespace(ai_provider="gemini"),
    )
    attempts = {"count": 0}

    def _request() -> None:
        attempts["count"] += 1
        raise FakeStatusError("API_KEY_INVALID: API key expired.", status_code=400)

    with pytest.raises(FakeStatusError):
        call_with_retries(_request, retries=3, backoff_seconds=0)

    assert attempts["count"] == 1


def test_call_with_retries_retries_transient_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "pawpal.ai.client.load_settings",
        lambda: SimpleNamespace(ai_provider="openai"),
    )
    attempts = {"count": 0}

    def _request() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary network issue")
        return "ok"

    result = call_with_retries(_request, retries=3, backoff_seconds=0)

    assert result == "ok"
    assert attempts["count"] == 3
