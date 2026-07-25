import logging
import time
from typing import Any

from google import genai
from google.genai import types

from app.ai.embedding_port import EmbeddingProviderError, EmbeddingResponse

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
        """Retries transient transport failures (network/5xx) only — same
        policy as GeminiProvider._generate_with_retry."""
        attempt = 0
        while True:
            try:
                response = self._client.models.embed_content(model=self._model, contents=contents, config=config)
                return response, attempt
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
