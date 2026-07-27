import uuid
from datetime import datetime, timedelta, timezone
from typing import BinaryIO

from app.core.exceptions import GoneError, NotFoundError, PermissionDeniedError, ValidationError
from app.db.models import ActivityEvent, Document, DocumentVersion, ShareLink, User
from app.db.models.enums import ActivityEventType, DocumentStatus, UserRole
from app.modules.documents.repository import DocumentRepository
from app.modules.shares.repository import ShareLinkRepository
from app.modules.shares.tokens import generate_token, hash_token
from app.storage.factory import get_storage
from app.storage.port import StoragePort

# An unauthenticated link should not live forever, so "never expires" is not
# an option the API offers at all. 90 days is a generous ceiling for sending
# a document to an external party without becoming a permanent back door.
MAX_EXPIRY_DAYS = 90
DEFAULT_EXPIRY_DAYS = 7


def _assert_can_share(document: Document, user: User) -> None:
    # Same rule as editing a document (documents/service.py::_assert_can_edit):
    # if you may change it, you may share it. Deliberately not a new,
    # separate permission concept — one more rule to reason about, with no
    # case that actually calls for it.
    if document.owner_id == user.id or user.role in (UserRole.REVIEWER, UserRole.ADMIN):
        return
    raise PermissionDeniedError("Only the owner, a reviewer, or an admin can share this document.")


class SharedDocument:
    """What a public viewer is allowed to know: enough to render the page,
    and nothing about who owns the document, its category, tags, review
    state or history."""

    def __init__(self, link: ShareLink, document: Document, version: DocumentVersion) -> None:
        self.title = document.title
        self.original_filename = version.original_filename
        self.mime_type = version.mime_type
        self.size_bytes = version.size_bytes
        self.version_number = version.version_number
        self.expires_at = link.expires_at


class ShareService:
    def __init__(
        self, repository: ShareLinkRepository, documents: DocumentRepository, storage: StoragePort
    ) -> None:
        self.repository = repository
        self.documents = documents
        self.storage = storage

    def _storage_for(self, provider: str) -> StoragePort:
        """Mirrors VersionService._storage_for — prefer the injected adapter
        when it already speaks this version's provider, fall back to the
        factory only for a genuinely different one."""
        if provider == self.storage.provider_name:
            return self.storage
        return get_storage(provider)

    def create_link(
        self, document_id: uuid.UUID, *, expires_in_days: int, current_user: User
    ) -> tuple[ShareLink, str]:
        """Returns the row **and** the raw token — the only moment the token
        exists in readable form. It is never recoverable afterwards, so the
        caller must return it to the user now or not at all."""
        if expires_in_days < 1 or expires_in_days > MAX_EXPIRY_DAYS:
            raise ValidationError(
                f"A share link must expire between 1 and {MAX_EXPIRY_DAYS} days from now.",
                fields=[{"field": "expiresInDays", "message": f"Choose 1-{MAX_EXPIRY_DAYS} days."}],
            )

        document = self.documents.get_active_by_id(document_id)
        if document is None:
            raise NotFoundError("This document doesn't exist or was deleted.")
        _assert_can_share(document, current_user)
        if document.current_version_id is None:
            raise ValidationError("This document has no file to share yet.")

        token = generate_token()
        link = ShareLink(
            token_hash=hash_token(token),
            document_id=document.id,
            # Pinned to whatever is current *now*, so a later upload can't
            # change what an external recipient sees.
            document_version_id=document.current_version_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            created_by=current_user.id,
        )
        self.repository.db.add(
            ActivityEvent(
                document_id=document.id,
                actor_id=current_user.id,
                event_type=ActivityEventType.SHARED,
                summary=(
                    f"{current_user.display_name} created a share link for “{document.title}” "
                    f"(expires in {expires_in_days} day{'s' if expires_in_days != 1 else ''})"
                ),
            )
        )
        return self.repository.add(link), token

    def list_links(self, document_id: uuid.UUID, *, current_user: User) -> list[ShareLink]:
        document = self.documents.get_active_by_id(document_id)
        if document is None:
            raise NotFoundError("This document doesn't exist or was deleted.")
        _assert_can_share(document, current_user)
        return self.repository.list_for_document(document_id)

    def revoke_link(self, document_id: uuid.UUID, link_id: uuid.UUID, *, current_user: User) -> ShareLink:
        document = self.documents.get_active_by_id(document_id)
        if document is None:
            raise NotFoundError("This document doesn't exist or was deleted.")
        _assert_can_share(document, current_user)

        link = self.repository.get_by_id(link_id)
        # The document_id check matters: without it, knowing any link id
        # plus any document you can edit would let you revoke someone
        # else's link on a document you have no rights to.
        if link is None or link.document_id != document_id:
            raise NotFoundError("That share link doesn't exist.")
        if link.revoked_at is not None:
            return link
        return self.repository.revoke(link)

    def resolve_public(self, token: str) -> tuple[ShareLink, SharedDocument]:
        """The unauthenticated path. Every failure mode — unknown token,
        expired, revoked, or a document since deleted — raises the *same*
        NotFoundError with the same wording, so an outsider probing links
        learns nothing about which of those is true (or whether a given
        document exists at all)."""
        link = self.repository.get_usable_by_token_hash(hash_token(token))
        if link is None or link.document.status != DocumentStatus.ACTIVE:
            raise NotFoundError("This link is invalid, has expired, or has been revoked.")
        return link, SharedDocument(link, link.document, link.document_version)

    def open_shared_content(self, token: str) -> tuple[ShareLink, DocumentVersion, BinaryIO]:
        """Resolves the token and opens the pinned version's bytes.

        Deliberately goes through resolve_public rather than re-implementing
        the checks, so the content route and the metadata route can never
        drift apart on what counts as a usable link."""
        link, _ = self.resolve_public(token)
        version = link.document_version
        storage = self._storage_for(version.storage_provider)
        try:
            stream = storage.open_for_read(version.storage_path)
        except FileNotFoundError as exc:
            raise GoneError("The file for this link is missing from storage.") from exc
        return link, version, stream
