"""add nullable organization_id columns and backfill

Revision ID: 7bbf96ca24d8
Revises: 8d789bcfb44f
Create Date: 2026-07-29 19:01:08.047048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '7bbf96ca24d8'
down_revision: Union[str, Sequence[str], None] = '8d789bcfb44f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"

# Every table identified in docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md (Part 3)
# as needing a direct organization_id column, rather than relying on a join
# chain up to a parent — documents, document_versions, and the AI tables in
# particular, since a missed join is exactly how the pre-migration similarity
# search leak happened.
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
    """Upgrade schema.

    Deliberately stops short of NOT NULL, composite uniqueness on
    categories/tags, and query-driving composite indexes — those land in the
    same change as the repository code that starts supplying
    organization_id on every write (Phase 4), so a live deployment is never
    caught between "column requires a value" and "application code doesn't
    send one yet". This migration alone is invisible to the running
    application: a new nullable column with no default does not affect any
    existing INSERT/UPDATE/SELECT.
    """
    for table in TENANT_SCOPED_TABLES:
        op.add_column(table, sa.Column("organization_id", UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_organization_id_organizations",
            table,
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])

    for table in TENANT_SCOPED_TABLES:
        op.execute(
            f"UPDATE {table} SET organization_id = '{DEFAULT_ORGANIZATION_ID}' "
            f"WHERE organization_id IS NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(TENANT_SCOPED_TABLES):
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_constraint(f"fk_{table}_organization_id_organizations", table, type_="foreignkey")
        op.drop_column(table, "organization_id")
