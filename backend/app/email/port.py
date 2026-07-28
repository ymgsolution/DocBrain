from typing import Protocol


class EmailError(Exception):
    """Delivery failed. Callers are expected to catch this and carry on —
    a failed invitation email must not fail the invitation itself, since
    the admin still has a copyable link."""


class EmailSender(Protocol):
    """Mirrors StoragePort/AIProvider: one Protocol, swappable adapters,
    callers never import a provider SDK directly."""

    def send(self, *, to: str, subject: str, html: str, text: str) -> None: ...
