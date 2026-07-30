"""enforce organization_id not null and per-org taxonomy uniqueness

Revision ID: 8ebd25762f70
Revises: 7bbf96ca24d8
Create Date: 2026-07-29 19:31:23.404114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ebd25762f70'
down_revision: Union[str, Sequence[str], None] = '7bbf96ca24d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same table list as the Phase 2 migration (7bbf96ca24d8). This migration is
# deliberately the *last* step of the multi-tenant repository sweep, not an
# earlier one: every repository/service write path was updated to always
# supply organization_id before this ran, so there is no window where the
# schema requires a value the application doesn't yet send. See
# docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md, Part 9.
TENANT_SCOPED_TABLES = [
    "users",
    "documents",
    "categories",
    "tags",
    "invitations",
    "share_links",
    "document_versions",
    "activity_events",
    "ai_jobs",
    "ai_document_analysis",
    "document_vector_embeddings",
]


def upgrade() -> None:
    """Upgrade schema."""
    for table in TENANT_SCOPED_TABLES:
        op.alter_column(table, "organization_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)

    # categories/tags were global vocabularies pre-migration (single unique
    # constraint on the whole table). Each organization needs its own
    # namespace — Accenture and Infosys must each be able to have a
    # category named "Finance" without colliding.
    op.drop_constraint("categories_slug_key", "categories", type_="unique")
    op.create_unique_constraint(
        "uq_categories_organization_id_slug", "categories", ["organization_id", "slug"]
    )

    op.execute("DROP INDEX IF EXISTS ux_categories_name_lower")
    op.execute(
        "CREATE UNIQUE INDEX ux_categories_organization_id_name_lower "
        "ON categories (organization_id, lower(name))"
    )

    op.drop_constraint("tags_normalized_name_key", "tags", type_="unique")
    op.create_unique_constraint(
        "uq_tags_organization_id_normalized_name", "tags", ["organization_id", "normalized_name"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_tags_organization_id_normalized_name", "tags", type_="unique")
    op.create_unique_constraint("tags_normalized_name_key", "tags", ["normalized_name"])

    op.execute("DROP INDEX IF EXISTS ux_categories_organization_id_name_lower")
    op.execute("CREATE UNIQUE INDEX ux_categories_name_lower ON categories (lower(name))")

    op.drop_constraint("uq_categories_organization_id_slug", "categories", type_="unique")
    op.create_unique_constraint("categories_slug_key", "categories", ["slug"])

    for table in reversed(TENANT_SCOPED_TABLES):
        op.alter_column(table, "organization_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
