import logging
import time
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.ai.embedding_port import (
    EmbeddingNonRetryableError,
    EmbeddingProviderError,
    EmbeddingQuotaExceededError,
    EmbeddingResponse,
)

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider:
    """The only EmbeddingProvider implementation today (structurally
    satisfies the Protocol in app/ai/embedding_port.py — no inheritance
    needed). Constructed once in app/ai_jobs/main.py and injected into
    EmbeddingGenerationService, independently of GeminiProvider/AIProvider —
    a different Gemini model (gemini-embedding-001) and SDK method
    (embed_content, not generate_content).

    The retry loop below is intentionally a near-duplicate of
    GeminiProvider._generate_with_retry rather than a shared helper: the two
    providers are constructed and fail independently, and factoring out a
    ~15-line loop isn't worth touching GeminiProvider's already-working code
    for.
    """

    def __init__(self, *, api_key: str, model: str, max_retries: int, output_dimensionality: int) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_retries = max_retries
        self._output_dimensionality = output_dimensionality

    def generate_embedding(self, *, text: str, task_type: str = "SEMANTIC_SIMILARITY") -> EmbeddingResponse:
        config = types.EmbedContentConfig(output_dimensionality=self._output_dimensionality, task_type=task_type)

        start = time.monotonic()
        response, retry_count = self._embed_with_retry(contents=text, config=config)
        latency_ms = int((time.monotonic() - start) * 1000)

        vector = response.embeddings[0].values
        return EmbeddingResponse(
            vector=vector,
            model=self._model,
            dimension=len(vector),
            latency_ms=latency_ms,
            retry_count=retry_count,
        )

    def _embed_with_retry(self, *, contents: str, config: types.EmbedContentConfig) -> tuple[Any, int]:
        """Retries transient transport failures (network/5xx/timeouts) only —
        same policy as GeminiProvider._generate_with_retry, including the
        same reasoning for handling 429/other-4xx separately, before the
        generic retry loop: see EmbeddingQuotaExceededError/
        EmbeddingNonRetryableError."""
        attempt = 0
        while True:
            try:
                response = self._client.models.embed_content(model=self._model, contents=contents, config=config)
                return response, attempt
            except genai_errors.ClientError as exc:
                if exc.code == 429:
                    retry_after = _parse_retry_delay(exc)
                    logger.warning("gemini embedding quota exceeded (model=%s): %s", self._model, exc)
                    raise EmbeddingQuotaExceededError(str(exc), retry_after_seconds=retry_after) from exc
                logger.warning(
                    "gemini embedding request permanently failed (model=%s, code=%s): %s", self._model, exc.code, exc
                )
                raise EmbeddingNonRetryableError(str(exc)) from exc
            except Exception as exc:
                if attempt >= self._max_retries:
                    raise EmbeddingProviderError(
                        f"Gemini embedding request failed after {attempt + 1} attempt(s): {exc}"
                    ) from exc
                sleep_seconds = min(2**attempt, 10)
                logger.warning(
                    "gemini embedding request failed (attempt=%s), retrying in %ss: %s",
                    attempt + 1,
                    sleep_seconds,
                    exc,
                )
                time.sleep(sleep_seconds)
                attempt += 1


def _parse_retry_delay(exc: genai_errors.ClientError) -> float | None:
    """Mirrors gemini_provider._parse_retry_delay — same best-effort parse
    of Gemini's structured RetryInfo detail, intentionally duplicated for
    the same reason the retry loop itself is."""
    try:
        detail_items = exc.details.get("error", {}).get("details", [])
        for item in detail_items:
            if str(item.get("@type", "")).endswith("RetryInfo"):
                delay_str = str(item.get("retryDelay", ""))
                if delay_str.endswith("s"):
                    return float(delay_str[:-1])
    except (AttributeError, TypeError, ValueError):
        pass
    return None
