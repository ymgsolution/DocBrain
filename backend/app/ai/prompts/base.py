from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    """A versioned, testable unit of prompt text. `render_user` is a pure
    function (inputs -> rendered string) — no DB/network access — so prompt
    changes are reviewable as a diff and testable without mocking anything,
    the same philosophy already applied to text_extraction's extractors."""

    name: str
    version: str
    system: str
    render_user: Callable[..., str]
