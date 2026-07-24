from pydantic import BaseModel, Field


class MetadataSuggestion(BaseModel):
    """The structured output requested from the model — scoped to exactly the
    3 demo-visible features (title, summary, tags). Field constraints exist
    so a technically-valid-JSON-but-useless response (empty title, 40 tags)
    fails Pydantic validation rather than getting written to the DB; see
    AIResponseValidationError."""

    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    tags: list[str] = Field(min_length=1, max_length=10)
