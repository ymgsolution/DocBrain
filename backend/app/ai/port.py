from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIProviderError(Exception):
    """Transport/provider-level failure (timeout, network, non-2xx, exhausted
    retries) — never raised for a well-formed-but-schema-invalid response,
    see AIResponseValidationError.

    retry_after_seconds/permanent let whoever raises this hint to the job
    queue how to schedule a retry (or whether to bother at all) without the
    queue needing to know anything about Gemini specifically — ai_jobs/
    worker.py reads these via getattr() with safe defaults, not an isinstance
    check, so the queue stays domain-agnostic and any future job type could
    use the same convention. Defaults here (None/False) mean "use the
    queue's normal generic backoff" — the existing, unchanged behavior."""

    retry_after_seconds: float | None = None
    permanent: bool = False


class AIResponseValidationError(AIProviderError):
    """The provider returned a response, but it didn't validate against the
    requested Pydantic schema. Not retried at the provider layer — retrying
    the identical prompt tends to reproduce the identical bad output. The job
    fails and picks up the existing ai_jobs backoff/retry instead (Gemini's
    output isn't fully deterministic, so a later attempt can genuinely
    succeed — this is deliberately NOT marked permanent)."""


class AIQuotaExceededError(AIProviderError):
    """Raised specifically for a 429/RESOURCE_EXHAUSTED response — never
    retried within a single generate_structured() call, since waiting a few
    seconds cannot fix "you're out of quota" (see GeminiProvider). Carries
    Gemini's own suggested wait time when the response includes one, so the
    job queue can schedule the retry sensibly instead of guessing."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AINonRetryableError(AIProviderError):
    """Raised for a request that can never succeed by retrying — a bad
    request, an invalid/revoked API key, a model name that doesn't exist for
    this project, etc. permanent=True tells the job queue to give up
    immediately rather than spend its retry budget on something that will
    fail identically every time."""

    permanent = True


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class AIResponse:
    """What every AIProvider call returns, regardless of which concrete
    provider (Gemini today; OpenAI/Claude later) produced it."""

    data: BaseModel
    raw_text: str
    model: str
    usage: TokenUsage
    latency_ms: int
    retry_count: int


class AIProvider(Protocol):
    """Mirrors StoragePort's shape: one Protocol, swappable concrete adapters,
    zero change to callers when the provider changes. generate_structured is
    the only method this milestone implements — generate_text is declared now
    so the metadata-generation service (and future summary/chat services)
    never have to depend on a provider-specific interface, even though only
    Gemini + structured output exists today. Embeddings are a separate
    EmbeddingProvider (app/ai/embedding_port.py) — different call shape
    (text-in/vector-out, no schema) and different tuning knobs
    (task_type/output_dimensionality) that don't belong on this Protocol."""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[SchemaT],
        timeout_seconds: float,
    ) -> AIResponse: ...

    def generate_text(self, *, system_prompt: str, user_prompt: str, timeout_seconds: float) -> str: ...
