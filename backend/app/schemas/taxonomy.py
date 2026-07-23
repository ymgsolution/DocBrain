import uuid

from pydantic import Field

from app.schemas.base import CamelModel


class CategoryOut(CamelModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    default_review_period_days: int | None
    is_archived: bool
    document_count: int


class CategoryCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    default_review_period_days: int | None = Field(default=None, gt=0)


class CategoryUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    default_review_period_days: int | None = None
    is_archived: bool | None = None


class TagOut(CamelModel):
    id: uuid.UUID
    name: str
    usage_count: int


class TagRename(CamelModel):
    name: str = Field(min_length=1, max_length=50)


class TagMergeRequest(CamelModel):
    target_tag_id: uuid.UUID


class TagMergeResponse(CamelModel):
    documents_updated: int
