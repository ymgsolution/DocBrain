"""GeminiEmbeddingProvider's retry logic tested against a fake stand-in for
the google-genai client's `.models.embed_content` — same no-mocking-library,
real-fixture style as test_gemini_provider.py, applied to the embedding
call's own SDK method/response shape (embeddings[0].values, not .text)."""

from dataclasses import dataclass

import pytest

from app.ai.embedding_port import EmbeddingProviderError
from app.ai.gemini_embedding_provider import GeminiEmbeddingProvider

VALID_VECTOR = [0.1, -0.2, 0.3, 0.05, -0.15, 0.25, 0.0, -0.1, 0.2, -0.05]


@dataclass
class _FakeEmbedding:
    values: list[float]


@dataclass
class _FakeEmbedResponse:
    embeddings: list[_FakeEmbedding]


def _make_provider(max_retries: int = 3) -> GeminiEmbeddingProvider:
    return GeminiEmbeddingProvider(
        api_key="fake-key-for-tests",
        model="gemini-embedding-001",
        max_retries=max_retries,
        output_dimensionality=len(VALID_VECTOR),
    )


def test_succeeds_on_first_attempt() -> None:
    provider = _make_provider()
    provider._client.models.embed_content = lambda **kwargs: _FakeEmbedResponse(
        embeddings=[_FakeEmbedding(values=VALID_VECTOR)]
    )

    response = provider.generate_embedding(text="Employee leave policy for full-time staff.")

    assert response.vector == VALID_VECTOR
    assert response.dimension == len(VALID_VECTOR)
    assert response.model == "gemini-embedding-001"
    assert response.retry_count == 0
    assert response.latency_ms >= 0


def test_passes_task_type_and_output_dimensionality_through(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider()
    captured: dict[str, object] = {}

    def capture(**kwargs: object) -> _FakeEmbedResponse:
        captured.update(kwargs)
        return _FakeEmbedResponse(embeddings=[_FakeEmbedding(values=VALID_VECTOR)])

    provider._client.models.embed_content = capture

    provider.generate_embedding(text="some text", task_type="RETRIEVAL_QUERY")

    config = captured["config"]
    assert config.task_type == "RETRIEVAL_QUERY"
    assert config.output_dimensionality == len(VALID_VECTOR)


def test_retries_transient_failures_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=2)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    calls = {"count": 0}

    def flaky(**kwargs: object) -> _FakeEmbedResponse:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient network error")
        return _FakeEmbedResponse(embeddings=[_FakeEmbedding(values=VALID_VECTOR)])

    provider._client.models.embed_content = flaky

    response = provider.generate_embedding(text="some text")
    assert response.retry_count == 2
    assert calls["count"] == 3


def test_raises_provider_error_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider(max_retries=1)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    def always_fails(**kwargs: object) -> _FakeEmbedResponse:
        raise RuntimeError("still down")

    provider._client.models.embed_content = always_fails

    with pytest.raises(EmbeddingProviderError):
        provider.generate_embedding(text="some text")
