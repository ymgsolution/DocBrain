"""GeminiProvider's retry/validation logic tested against a fake stand-in for
the google-genai client's `.models.generate_content` — no real network call,
mirroring the no-mocking-library, real-fixture style used elsewhere, just
applied to a seam (the HTTP call) that has no pure in-process equivalent to
construct for real."""

import json
from dataclasses import dataclass, field

import pytest
from google.genai import errors as genai_errors

from app.ai.gemini_provider import GeminiProvider
from app.ai.port import AINonRetryableError, AIProviderError, AIQuotaExceededError, AIResponseValidationError
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


def _make_client_error(code: int, *, status: str, retry_delay: str | None = None) -> genai_errors.ClientError:
    """Builds a real google.genai ClientError with the same response shape
    Gemini actually returns (verified live against a real 429), rather than
    a hand-rolled fake — same "real fixture" philosophy as the rest of this
    file, applied to an exception type instead of a response object."""
    details = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}] if retry_delay else []
    response_json = {"error": {"code": code, "status": status, "message": f"{status} for testing", "details": details}}
    return genai_errors.ClientError(code, response_json)


def test_raises_quota_exceeded_immediately_on_429_without_retrying(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=3)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    calls = {"count": 0}

    def quota_exhausted(**kwargs: object) -> _FakeResponse:
        calls["count"] += 1
        raise _make_client_error(429, status="RESOURCE_EXHAUSTED", retry_delay="58s")

    provider._client.models.generate_content = quota_exhausted

    with pytest.raises(AIQuotaExceededError) as exc_info:
        provider.generate_structured(
            system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
        )
    # The whole point: a quota error must not consume the normal retry
    # budget — waiting a few seconds and asking again cannot fix "you're
    # out of quota," so it should cost exactly one call, not max_retries+1.
    assert calls["count"] == 1
    assert exc_info.value.retry_after_seconds == 58.0


def test_raises_quota_exceeded_with_no_retry_delay_when_gemini_omits_it(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=3)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    def quota_exhausted(**kwargs: object) -> _FakeResponse:
        raise _make_client_error(429, status="RESOURCE_EXHAUSTED")

    provider._client.models.generate_content = quota_exhausted

    with pytest.raises(AIQuotaExceededError) as exc_info:
        provider.generate_structured(
            system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
        )
    assert exc_info.value.retry_after_seconds is None


def test_raises_non_retryable_error_immediately_on_other_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=3)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    calls = {"count": 0}

    def bad_request(**kwargs: object) -> _FakeResponse:
        calls["count"] += 1
        raise _make_client_error(400, status="INVALID_ARGUMENT")

    provider._client.models.generate_content = bad_request

    with pytest.raises(AINonRetryableError) as exc_info:
        provider.generate_structured(
            system_prompt="system", user_prompt="user", response_schema=MetadataSuggestion, timeout_seconds=5
        )
    assert calls["count"] == 1
    assert exc_info.value.permanent is True


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
