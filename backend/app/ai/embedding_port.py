from dataclasses import dataclass
from typing import Protocol


class EmbeddingProviderError(Exception):
    """Transport/provider-level failure (timeout, network, non-2xx, exhausted
    retries) — mirrors AIProviderError in app/ai/port.py. There is no
    embedding equivalent of AIResponseValidationError: there's no schema to
    validate a vector against, only a dimension sanity-check the caller can
    do itself if it wants one."""


@dataclass(frozen=True)
class EmbeddingResponse:
    """What every EmbeddingProvider call returns, regardless of which
    concrete provider produced it — mirrors AIResponse's role in
    app/ai/port.py, but text-in/vector-out has no `data`/schema to carry."""

    vector: list[float]
    model: str
    dimension: int
    latency_ms: int
    retry_count: int


class EmbeddingProvider(Protocol):
    """Deliberately separate from AIProvider (app/ai/port.py): embeddings are
    text-in/vector-out with tuning knobs (task_type, output_dimensionality)
    that don't fit generate_structured/generate_text's prompt+schema shape.
    Same swappable-adapter intent as AIProvider — one Protocol, concrete
    providers structurally satisfy it, callers never import a provider SDK
    directly."""

    def generate_embedding(self, *, text: str, task_type: str = "SEMANTIC_SIMILARITY") -> EmbeddingResponse: ...
