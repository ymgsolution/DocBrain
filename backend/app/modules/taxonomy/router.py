import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.models import Category, User
from app.db.models.enums import UserRole
from app.db.session import get_db_session
from app.modules.taxonomy.repository import TaxonomyRepository
from app.modules.taxonomy.service import TaxonomyService
from app.schemas.taxonomy import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    TagMergeRequest,
    TagMergeResponse,
    TagOut,
    TagRename,
)

router = APIRouter(prefix="/api/v1", tags=["taxonomy"])


def get_taxonomy_service(db: Session = Depends(get_db_session)) -> TaxonomyService:
    return TaxonomyService(TaxonomyRepository(db))


def _to_category_out(category: Category, document_count: int) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        default_review_period_days=category.default_review_period_days,
        is_archived=category.is_archived,
        document_count=document_count,
    )


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    include_archived: bool = Query(default=False, alias="includeArchived"),
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(get_current_user),
) -> list[CategoryOut]:
    return [_to_category_out(c, count) for c, count in service.list_categories(include_archived=include_archived)]


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate,
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> CategoryOut:
    category = service.create_category(
        name=payload.name,
        description=payload.description,
        default_review_period_days=payload.default_review_period_days,
    )
    return _to_category_out(category, 0)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> CategoryOut:
    category = service.update_category(
        category_id,
        name=payload.name,
        description=payload.description,
        default_review_period_days=payload.default_review_period_days,
        is_archived=payload.is_archived,
    )
    count = service.repository.get_category_document_count(category.id)
    return _to_category_out(category, count)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    service.delete_category(category_id)


@router.get("/tags", response_model=list[TagOut])
def list_tags(
    q: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(get_current_user),
) -> list[TagOut]:
    return [TagOut.model_validate(t, from_attributes=True) for t in service.list_tags(q=q, limit=limit)]


@router.patch("/tags/{tag_id}", response_model=TagOut)
def rename_tag(
    tag_id: uuid.UUID,
    payload: TagRename,
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> TagOut:
    tag = service.rename_tag(tag_id, name=payload.name)
    return TagOut.model_validate(tag, from_attributes=True)


@router.post("/tags/{tag_id}/merge", response_model=TagMergeResponse)
def merge_tag(
    tag_id: uuid.UUID,
    payload: TagMergeRequest,
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> TagMergeResponse:
    count = service.merge_tag(tag_id, target_tag_id=payload.target_tag_id)
    return TagMergeResponse(documents_updated=count)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(
    tag_id: uuid.UUID,
    service: TaxonomyService = Depends(get_taxonomy_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    service.delete_tag(tag_id)
