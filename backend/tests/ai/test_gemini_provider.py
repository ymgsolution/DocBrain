"""GeminiProvider's retry/validation logic tested against a fake stand-in for
the google-genai client's `.models.generate_content` — no real network call,
mirroring the no-mocking-library, real-fixture style used elsewhere, just
applied to a seam (the HTTP call) that has no pure in-process equivalent to
construct for real."""

import json
from dataclasses import dataclass, field

import pytest

from app.ai.gemini_provider import GeminiProvider
from app.ai.port import AIProviderError, AIResponseValidationError
from app.ai.schemas import MetadataSuggestion

VALID_PAYLOAD = {
    "title": "Q1 Travel Budget",
    "summary": "A breakdown of projected travel spend for Q1.",
    "tags": ["finance", "travel"],
}


@dataclass
class _FakeUsage:
    prompt_token_count: int
    candidates_token_count: int
    total_token_count: int


@dataclass
class _FakeResponse:
    text: str
    usage_metadata: _FakeUsage = field(default_factory=lambda: _FakeUsage(10, 20, 30))


def _make_provider(max_retries: int = 3) -> GeminiProvider:
    return GeminiProvider(api_key="fake-key-for-tests", model="gemini-2.0-flash", max_retries=max_retries)


def test_succeeds_on_first_attempt() -> None:
    provider = _make_provider()
    provider._client.models.generate_content = lambda **kwargs: _FakeResponse(text=json.dumps(VALID_PAYLOAD))

    response = provider.generate_structured(
        system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
    )

    assert isinstance(response.data, MetadataSuggestion)
    assert response.data.title == "Q1 Travel Budget"
    assert response.retry_count == 0
    assert response.usage.total_tokens == 30


def test_retries_transient_failures_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=2)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    calls = {"count": 0}

    def flaky(**kwargs: object) -> _FakeResponse:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient network error")
        return _FakeResponse(text=json.dumps(VALID_PAYLOAD))

    provider._client.models.generate_content = flaky

    response = provider.generate_structured(
        system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
    )
    assert response.retry_count == 2
    assert calls["count"] == 3


def test_raises_provider_error_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=1)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    def always_fails(**kwargs: object) -> _FakeResponse:
        raise RuntimeError("still down")

    provider._client.models.generate_content = always_fails

    with pytest.raises(AIProviderError):
        provider.generate_structured(
            system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
        )


def test_raises_validation_error_on_malformed_json_without_retrying() -> None:
    provider = _make_provider(max_retries=3)
    calls = {"count": 0}

    def bad_json(**kwargs: object) -> _FakeResponse:
        calls["count"] += 1
        return _FakeResponse(text="not json")

    provider._client.models.generate_content = bad_json

    with pytest.raises(AIResponseValidationError):
        provider.generate_structured(
            system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
        )
    assert calls["count"] == 1


def test_raises_validation_error_on_schema_mismatch_without_retrying() -> None:
    provider = _make_provider(max_retries=3)
    calls = {"count": 0}

    def wrong_shape(**kwargs: object) -> _FakeResponse:
        calls["count"] += 1
        return _FakeResponse(text=json.dumps({"title": "Only a title"}))

    provider._client.models.generate_content = wrong_shape

    with pytest.raises(AIResponseValidationError):
        provider.generate_structured(
            system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
        )
    assert calls["count"] == 1
