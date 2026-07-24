from app.ai.prompts import metadata_generation
from app.ai.prompts.base import Prompt

_PROMPTS: dict[str, Prompt] = {
    metadata_generation.PROMPT.name: metadata_generation.PROMPT,
}


def get_prompt(name: str) -> Prompt:
    """Explicit registration, not filesystem/module auto-discovery — at one
    or two prompts, magic dynamic loading buys nothing but indirection.
    Revisit if the prompt count actually grows large enough to make explicit
    registration tedious."""
    try:
        return _PROMPTS[name]
    except KeyError:
        raise KeyError(f"No prompt registered under name={name!r}") from None
