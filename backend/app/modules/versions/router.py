import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.service import DocumentService
from app.modules.versions.repository import VersionRepository
from app.modules.versions.service import VersionService
from app.schemas.mappers import to_version_detail
from app.schemas.version import VersionDetail, VersionRestoreRequest
from app.storage.local_adapter import LocalFileSystemStorage

router = APIRouter(prefix="/api/v1/documents/{document_id}/versions", tags=["versions"])

INLINE_PREVIEWABLE_MIME_TYPES = {"application/pdf", "text/plain"}


def get_version_service(db: Session = Depends(get_db_session)) -> VersionService:
    return VersionService(VersionRepository(db), LocalFileSystemStorage())


def get_document_service(db: Session = Depends(get_db_session)) -> DocumentService:
    return DocumentService(DocumentRepository(db), LocalFileSystemStorage())


def _resolve_disposition(requested: str, mime_type: str) -> str:
    if requested == "inline" and (mime_type in INLINE_PREVIEWABLE_MIME_TYPES or mime_type.startswith("image/")):
        return "inline"
    return "attachment"


@router.get("", response_model=list[VersionDetail])
def list_versions(
    document_id: uuid.UUID,
    version_service: VersionService = Depends(get_version_service),
    document_service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> list[VersionDetail]:
    document = document_service.get_detail(document_id)
    versions = version_service.list_versions(document)
    return [to_version_detail(v, document.current_version_id) for v in versions]


@router.post("", response_model=VersionDetail, status_code=201)
def upload_version(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    change_note: str = Form(..., alias="changeNote", min_length=5, max_length=500),
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_user),
) -> VersionDetail:
    version = version_service.upload_version(
        document_id, file=file, change_note=change_note, current_user=current_user
    )
    return to_version_detail(version, current_version_id=version.id)


@router.get("/{version_number}/content")
def download_version(
    document_id: uuid.UUID,
    version_number: int,
    disposition: str = "attachment",
    version_service: VersionService = Depends(get_version_service),
    document_service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    document = document_service.get_detail(document_id)
    version, stream = version_service.get_content(document, version_number)
    disp = _resolve_disposition(disposition, version.mime_type)
    headers = {
        "Content-Disposition": f'{disp}; filename="{version.original_filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(stream, media_type=version.mime_type, headers=headers)


@router.post("/{version_number}/restore", response_model=VersionDetail, status_code=201)
def restore_version(
    document_id: uuid.UUID,
    version_number: int,
    payload: VersionRestoreRequest,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_user),
) -> VersionDetail:
    version = version_service.restore_version(
        document_id, version_number, change_note=payload.change_note, current_user=current_user
    )
    return to_version_detail(version, current_version_id=version.id)
