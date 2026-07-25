from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIProviderError(Exception):
    """Transport/provider-level failure (timeout, network, non-2xx, exhausted
    retries) — never raised for a well-formed-but-schema-invalid response,
    see AIResponseValidationError."""


class AIResponseValidationError(AIProviderError):
    """The provider returned a response, but it didn't validate against the
    requested Pydantic schema. Not retried at the provider layer — retrying
    the identical prompt tends to reproduce the identical bad output. The job
    fails and picks up the existing ai_jobs backoff/retry instead."""


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
