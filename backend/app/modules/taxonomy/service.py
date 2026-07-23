import uuid

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.models import Category, DocumentTag, Tag
from app.modules.taxonomy.repository import TaxonomyRepository
from app.utils.slugify import slugify


class TaxonomyService:
    def __init__(self, repository: TaxonomyRepository) -> None:
        self.repository = repository

    # --- categories ---

    def list_categories(self, *, include_archived: bool) -> list[tuple[Category, int]]:
        return self.repository.list_categories(include_archived=include_archived)

    def _unique_slug(self, base: str, *, exclude_category_id: uuid.UUID | None = None) -> str:
        base_slug = slugify(base)
        candidate = base_slug
        i = 2
        while True:
            existing = self.repository.get_category_by_slug(candidate)
            if existing is None or existing.id == exclude_category_id:
                return candidate
            candidate = f"{base_slug}-{i}"
            i += 1

    def create_category(
        self, *, name: str, description: str | None, default_review_period_days: int | None
    ) -> Category:
        if self.repository.get_category_by_name_ci(name) is not None:
            raise ConflictError(
                "A category with that name already exists.",
                fields=[{"field": "name", "message": "Name must be unique (case-insensitive)."}],
            )
        category = Category(
            name=name.strip(),
            slug=self._unique_slug(name),
            description=description,
            default_review_period_days=default_review_period_days,
        )
        self.repository.add_category(category)
        self.repository.db.commit()
        self.repository.db.refresh(category)
        return category

    def update_category(
        self,
        category_id: uuid.UUID,
        *,
        name: str | None,
        description: str | None,
        default_review_period_days: int | None,
        is_archived: bool | None,
    ) -> Category:
        category = self.repository.get_category(category_id)
        if category is None:
            raise NotFoundError("This category doesn't exist.")

        if name is not None and name.strip().lower() != category.name.lower():
            existing = self.repository.get_category_by_name_ci(name)
            if existing is not None and existing.id != category.id:
                raise ConflictError(
                    "A category with that name already exists.",
                    fields=[{"field": "name", "message": "Name must be unique (case-insensitive)."}],
                )
            category.name = name.strip()
            category.slug = self._unique_slug(name, exclude_category_id=category.id)

        if description is not None:
            category.description = description
        if default_review_period_days is not None:
            category.default_review_period_days = default_review_period_days
        if is_archived is not None:
            category.is_archived = is_archived

        self.repository.db.commit()
        self.repository.db.refresh(category)
        return category

    def delete_category(self, category_id: uuid.UUID) -> None:
        category = self.repository.get_category(category_id)
        if category is None:
            raise NotFoundError("This category doesn't exist.")
        usage = self.repository.get_category_document_count(category_id)
        if usage > 0:
            raise ConflictError(
                f"This category is used by {usage} document(s) and can't be deleted — archive it instead.",
                fields=[{"field": "category_id", "message": "Category is in use."}],
            )
        self.repository.delete_category(category)
        self.repository.db.commit()

    # --- tags ---

    def list_tags(self, *, q: str | None, limit: int) -> list[Tag]:
        return self.repository.list_tags(q=q, limit=limit)

    def rename_tag(self, tag_id: uuid.UUID, *, name: str) -> Tag:
        tag = self.repository.get_tag(tag_id)
        if tag is None:
            raise NotFoundError("This tag doesn't exist.")
        normalized = name.strip().lower()
        existing = self.repository.get_tag_by_normalized_name(normalized)
        if existing is not None and existing.id != tag.id:
            raise ConflictError(
                f"A tag named “{existing.name}” already exists — merge into it instead of renaming.",
                fields=[{"field": "name", "message": "Tag name already in use."}],
            )
        tag.name = name.strip()
        tag.normalized_name = normalized
        self.repository.db.commit()
        self.repository.db.refresh(tag)
        return tag

    def merge_tag(self, source_tag_id: uuid.UUID, *, target_tag_id: uuid.UUID) -> int:
        if source_tag_id == target_tag_id:
            raise ValidationError("Can't merge a tag into itself.")
        source = self.repository.get_tag(source_tag_id)
        target = self.repository.get_tag(target_tag_id)
        if source is None or target is None:
            raise NotFoundError("One of these tags doesn't exist.")

        links = self.repository.list_document_tags_for_tag(source.id)
        updated_count = 0
        for link in links:
            already_tagged = self.repository.get_document_tag(link.document_id, target.id)
            # Explicit delete (+ insert) rather than an in-place UPDATE, so the
            # tags.usage_count trigger — which only fires on INSERT/DELETE —
            # stays correct on both sides of the merge.
            self.repository.db.delete(link)
            self.repository.db.flush()
            if already_tagged is None:
                self.repository.db.add(DocumentTag(document_id=link.document_id, tag_id=target.id))
                self.repository.db.flush()
            updated_count += 1

        self.repository.delete_tag(source)
        self.repository.db.commit()
        return updated_count

    def delete_tag(self, tag_id: uuid.UUID) -> None:
        tag = self.repository.get_tag(tag_id)
        if tag is None:
            raise NotFoundError("This tag doesn't exist.")
        if tag.usage_count > 0:
            raise ConflictError(
                f"This tag is used by {tag.usage_count} document(s) and can't be deleted.",
                fields=[{"field": "tag_id", "message": "Tag is in use."}],
            )
        self.repository.delete_tag(tag)
        self.repository.db.commit()
