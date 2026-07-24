"""Prompt templates are pure functions (inputs -> rendered string), so these
are tested the same way as the text extractors: no DB, no network, no
mocking. See app/ai/prompts/base.py."""

import pytest

from app.ai.prompts import metadata_generation
from app.ai.prompts.registry import get_prompt


def test_registry_returns_the_registered_prompt() -> None:
    prompt = get_prompt("metadata_generation")
    assert prompt is metadata_generation.PROMPT
    assert prompt.version == "v1"


def test_registry_raises_on_unknown_name() -> None:
    with pytest.raises(KeyError):
        get_prompt("does_not_exist")


def test_render_user_includes_title_and_extracted_text() -> None:
    rendered = metadata_generation.render_user(title="Q1 Budget.xlsx", extracted_text="Travel | 4200")
    assert "Q1 Budget.xlsx" in rendered
    assert "Travel | 4200" in rendered
