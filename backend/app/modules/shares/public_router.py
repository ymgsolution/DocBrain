from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.modules.shares.service import ShareService
from app.modules.shares.router import get_share_service
from app.modules.versions.router import _content_disposition_header
from app.schemas.share import PublicSharedDocument

# THE ONLY UNAUTHENTICATED ROUTER IN THE APPLICATION.
#
# Everything under /api/v1/documents requires get_current_user; these two
# routes deliberately do not, because the whole point is that a recipient has
# no account. Three rules keep that safe, and they should survive any future
# edit to this file:
#
#   1. No route here takes a document id. The token is the only input, and it
#      resolves to exactly one pinned version — so there is no parameter an
#      attacker can change to reach a different document.
#   2. Every rejection is the same 404 with the same wording (see
#      ShareService.resolve_public), so probing reveals nothing about whether
#      a token is wrong, expired, revoked, or points at a deleted document.
#   3. Downloads are not offered. Content is served inline only, matching the
#      view-only decision for external recipients.
#
# Kept on a /public/ prefix so its lack of auth is obvious from the path
# alone, rather than something a reader has to infer from missing arguments.
router = APIRouter(prefix="/api/v1/public/shares", tags=["public-shares"])


@router.get("/{token}", response_model=PublicSharedDocument)
def get_shared_document(token: str, service: ShareService = Depends(get_share_service)) -> PublicSharedDocument:
    link, shared = service.resolve_public(token)
    service.repository.record_view(link)
    return PublicSharedDocument(
        title=shared.title,
        original_filename=shared.original_filename,
        mime_type=shared.mime_type,
        size_bytes=shared.size_bytes,
        version_number=shared.version_number,
        expires_at=shared.expires_at,
    )


@router.get("/{token}/content")
def get_shared_content(token: str, service: ShareService = Depends(get_share_service)) -> StreamingResponse:
    _link, version, stream = service.open_shared_content(token)

    return StreamingResponse(
        stream,
        media_type=version.mime_type,
        headers={
            # Always "inline", never "attachment": the view-only decision is
            # enforced here rather than trusted to the frontend, so a
            # recipient calling this URL directly still can't turn it into a
            # download prompt. (Inline content is of course still saveable by
            # a determined viewer — this is a friction boundary, not DRM.)
            "Content-Disposition": _content_disposition_header("inline", version.original_filename),
            "X-Content-Type-Options": "nosniff",
            # Shared documents must never end up in a search index.
            "X-Robots-Tag": "noindex, nofollow",
            "Cache-Control": "private, no-store",
        },
    )
