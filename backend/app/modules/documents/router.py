import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.ai.analysis_repository import AiDocumentAnalysisRepository
from app.ai.embedding_repository import DocumentVectorEmbeddingRepository
from app.ai.similarity_service import SimilarityService
from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.models.enums import DocumentStatus
from app.db.session import get_db_session
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.service import DocumentService
from app.schemas.document import DocumentCreateMetadata, DocumentDetail, DocumentUpdate, PagedDocuments, SimilarDocument
from app.schemas.mappers import to_document_detail, to_document_summary, to_similar_document, to_trashed_document_item
from app.schemas.trash import PagedTrash
from app.storage.factory import get_storage

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_document_service(db: Session = Depends(get_db_session)) -> DocumentService:
    return DocumentService(DocumentRepository(db), get_storage())


def get_similarity_service(db: Session = Depends(get_db_session)) -> SimilarityService:
    return SimilarityService(DocumentVectorEmbeddingRepository(db), DocumentRepository(db))


def get_analysis_repository(db: Session = Depends(get_db_session)) -> AiDocumentAnalysisRepository:
    return AiDocumentAnalysisRepository(db)


@router.get("", response_model=PagedDocuments)
def list_documents(
    q: str | None = None,
    category_id: uuid.UUID | None = Query(default=None, alias="categoryId"),
    tag_id: list[uuid.UUID] | None = Query(default=None, alias="tagId"),
    owner_id: uuid.UUID | None = Query(default=None, alias="ownerId"),
    review_status: str | None = Query(default=None, alias="reviewStatus", pattern="^(overdue|due_soon|ok)$"),
    sort: str = "updated_at",
    page: int = Query(default=0, ge=0),
    size: int = Query(default=25, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> PagedDocuments:
    items, total = service.list_documents(
        organization_id=current_user.organization_id,
        q=q,
        category_id=category_id,
        tag_ids=tag_id,
        owner_id=owner_id,
        status=DocumentStatus.ACTIVE,
        review_status=review_status,
        sort=sort,
        page=page,
        size=size,
    )
    return PagedDocuments(
        items=[to_document_summary(d) for d in items],
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size if size else 0,
    )


@router.post("", response_model=DocumentDetail, status_code=201)
def create_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category_id: uuid.UUID = Form(..., alias="categoryId"),
    description: str | None = Form(default=None),
    tags: str = Form(default=""),
    review_due_date: date | None = Form(default=None, alias="reviewDueDate"),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> DocumentDetail:
    metadata = DocumentCreateMetadata(
        title=title,
        category_id=category_id,
        description=description,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        review_due_date=review_due_date,
    )
    document = service.create_document(
        file=file,
        title=metadata.title,
        category_id=metadata.category_id,
        description=metadata.description,
        tag_names=metadata.tags,
        review_due_date=metadata.review_due_date,
        current_user=current_user,
    )
    return to_document_detail(document, ai_suggestions_enabled=current_user.organization.ai_suggestions_enabled)


@router.get("/trash", response_model=PagedTrash)
def list_trash(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=25, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> PagedTrash:
    items, total = service.list_trash(current_user=current_user, page=page, size=size)
    return PagedTrash(
        items=[to_trashed_document_item(d) for d in items],
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size if size else 0,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> DocumentDetail:
    document = service.get_detail(document_id, current_user.organization_id)
    service.touch_last_accessed(document)
    return to_document_detail(document, ai_suggestions_enabled=current_user.organization.ai_suggestions_enabled)


@router.get("/{document_id}/similar", response_model=list[SimilarDocument])
def get_similar_documents(
    document_id: uuid.UUID,
    limit: int = Query(default=5, ge=1, le=20),
    service: DocumentService = Depends(get_document_service),
    similarity: SimilarityService = Depends(get_similarity_service),
    current_user: User = Depends(get_current_user),
) -> list[SimilarDocument]:
    # 404s via NotFoundError if missing/inactive/another org's, same as GET /documents/{id}
    service.get_detail(document_id, current_user.organization_id)
    if not current_user.organization.duplicate_detection_enabled:
        # Checked before the query rather than filtering its results: with the
        # setting off there is nothing to compute, so the pgvector search is
        # skipped entirely. An empty list rather than an error — the card
        # already hides itself on an empty result, so the feature disappears
        # with no frontend change. Existing embeddings are left in place;
        # hiding is reversible, deleting them isn't.
        return []
    results = similarity.find_similar_documents(
        document_id, organization_id=current_user.organization_id, limit=limit
    )
    return [to_similar_document(document, score) for document, score in results]


@router.post("/{document_id}/ai-suggestion/review", response_model=DocumentDetail)
def review_ai_suggestion(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    analysis_repo: AiDocumentAnalysisRepository = Depends(get_analysis_repository),
    current_user: User = Depends(get_current_user),
) -> DocumentDetail:
    document = service.get_detail(document_id, current_user.organization_id)
    if document.current_version is not None:
        analysis_repo.mark_reviewed(document.current_version.id, accepted_by=current_user.id)
    return to_document_detail(document, ai_suggestions_enabled=current_user.organization.ai_suggestions_enabled)


@router.patch("/{document_id}", response_model=DocumentDetail)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> DocumentDetail:
    document = service.update_metadata(
        document_id,
        current_user=current_user,
        title=payload.title,
        description=payload.description,
        category_id=payload.category_id,
        tag_names=payload.tags,
        review_due_date=payload.review_due_date,
        owner_id=payload.owner_id,
    )
    return to_document_detail(document, ai_suggestions_enabled=current_user.organization.ai_suggestions_enabled)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> None:
    service.soft_delete(document_id, current_user=current_user)


@router.post("/{document_id}/restore", response_model=DocumentDetail)
def restore_document(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> DocumentDetail:
    document = service.restore(document_id, current_user=current_user)
    return to_document_detail(document, ai_suggestions_enabled=current_user.organization.ai_suggestions_enabled)


@router.delete("/{document_id}/permanent", status_code=204)
def hard_delete_document(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> None:
    service.hard_delete(document_id, current_user=current_user)
