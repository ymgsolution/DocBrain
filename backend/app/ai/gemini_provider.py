import json
import logging
import time
from typing import Any, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.ai.port import (
    AINonRetryableError,
    AIProviderError,
    AIQuotaExceededError,
    AIResponse,
    AIResponseValidationError,
    TokenUsage,
)

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class GeminiProvider:
    """The only AIProvider implementation today (structurally satisfies the
    Protocol in app/ai/port.py — no inheritance needed). Constructed once in
    app/ai_jobs/main.py and injected into MetadataGenerationService; nothing
    downstream imports google.genai directly, so a future OpenAI/Claude
    provider means writing one new class, not touching business logic.

    Validation is done ourselves (json.loads + Pydantic), not left to the
    SDK's own response.parsed — that keeps validation behavior identical
    regardless of provider, and gives us raw_text for AIResponse even when
    validation fails.
    """

    def __init__(self, *, api_key: str, model: str, max_retries: int) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_retries = max_retries

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[SchemaT],
        timeout_seconds: float,
    ) -> AIResponse:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

        start = time.monotonic()
        response, retry_count = self._generate_with_retry(contents=user_prompt, config=config)
        latency_ms = int((time.monotonic() - start) * 1000)

        raw_text = response.text or ""
        try:
            data = response_schema.model_validate(json.loads(raw_text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise AIResponseValidationError(f"Response failed schema validation: {exc}") from exc

        usage_metadata = getattr(response, "usage_metadata", None)
        usage = TokenUsage(
            prompt_tokens=getattr(usage_metadata, "prompt_token_count", None),
            completion_tokens=getattr(usage_metadata, "candidates_token_count", None),
            total_tokens=getattr(usage_metadata, "total_token_count", None),
        )

        return AIResponse(
            data=data,
            raw_text=raw_text,
            model=self._model,
            usage=usage,
            latency_ms=latency_ms,
            retry_count=retry_count,
        )

    def generate_text(self, *, system_prompt: str, user_prompt: str, timeout_seconds: float) -> str:
        raise NotImplementedError("generate_text is not implemented in this milestone — structured output only.")

    def _generate_with_retry(self, *, contents: str, config: types.GenerateContentConfig) -> tuple[Any, int]:
        """Retries transient transport failures (network/5xx/timeouts) only —
        schema-validation failures happen after this returns and are never
        retried here; see AIResponseValidationError.

        A 429 (quota exhausted) or any other 4xx is handled separately,
        before the generic retry loop even runs: waiting a few seconds and
        trying the identical request again cannot fix "you're out of quota"
        or "this request is malformed" — it can only waste more of a
        free-tier budget that's already limited. See AIQuotaExceededError/
        AINonRetryableError.
        """
        attempt = 0
        while True:
            try:
                response = self._client.models.generate_content(model=self._model, contents=contents, config=config)
                return response, attempt
            except genai_errors.ClientError as exc:
                if exc.code == 429:
                    retry_after = _parse_retry_delay(exc)
                    logger.warning("gemini quota exceeded (model=%s): %s", self._model, exc)
                    raise AIQuotaExceededError(str(exc), retry_after_seconds=retry_after) from exc
                logger.warning("gemini request permanently failed (model=%s, code=%s): %s", self._model, exc.code, exc)
                raise AINonRetryableError(str(exc)) from exc
            except Exception as exc:
                if attempt >= self._max_retries:
                    raise AIProviderError(f"Gemini request failed after {attempt + 1} attempt(s): {exc}") from exc
                sleep_seconds = min(2**attempt, 10)
                logger.warning(
                    "gemini request failed (attempt=%s), retrying in %ss: %s", attempt + 1, sleep_seconds, exc
                )
                time.sleep(sleep_seconds)
                attempt += 1


def _parse_retry_delay(exc: genai_errors.ClientError) -> float | None:
    """Gemini's 429 responses often include a structured RetryInfo detail
    (e.g. {'@type': '...RetryInfo', 'retryDelay': '58s'}) with its own
    suggested wait time. Best-effort: returns None if the shape isn't what
    we expect, rather than raising — a missing hint just means the caller
    falls back to its own default backoff."""
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
