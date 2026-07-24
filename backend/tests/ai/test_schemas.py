import pytest
from pydantic import ValidationError

from app.ai.schemas import MetadataSuggestion


def test_valid_suggestion_parses() -> None:
    suggestion = MetadataSuggestion(
        title="Q1 Travel Budget",
        summary="A breakdown of projected travel spend for Q1.",
        tags=["finance", "travel", "budget"],
    )
    assert suggestion.summary == "A breakdown of projected travel spend for Q1."
    assert suggestion.tags == ["finance", "travel", "budget"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"summary": ""},
        {"tags": []},
    ],
)
def test_invalid_suggestion_raises(overrides: dict) -> None:
    base = {
        "title": "Q1 Travel Budget",
        "summary": "A breakdown of projected travel spend for Q1.",
        "tags": ["finance"],
    }
    with pytest.raises(ValidationError):
        MetadataSuggestion(**{**base, **overrides})


def test_rejects_unparseable_json() -> None:
    with pytest.raises(ValidationError):
        MetadataSuggestion.model_validate({"title": "Only a title"})
