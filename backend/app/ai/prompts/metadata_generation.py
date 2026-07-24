from app.ai.prompts.base import Prompt

NAME = "metadata_generation"
VERSION = "v1"

SYSTEM = """You are a document assistant for an internal document management \
system. Given the extracted text of a document, suggest:

- title: a concise, human-readable title (not a filename).
- summary: 1-3 sentences describing what the document is and its purpose.
- tags: 3-6 short, lowercase, reusable topical labels (not full sentences).

Base every suggestion strictly on the given text. Never invent facts, \
figures, or claims that aren't in it.

Respond with structured JSON matching the given schema only."""


def render_user(*, title: str, extracted_text: str) -> str:
    return (
        f"Document filename/current title: {title}\n\n"
        f"Extracted text:\n{extracted_text}"
    )


PROMPT = Prompt(name=NAME, version=VERSION, system=SYSTEM, render_user=render_user)
