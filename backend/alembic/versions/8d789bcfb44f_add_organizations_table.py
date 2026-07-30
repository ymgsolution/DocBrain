"""add organizations table

Revision ID: 8d789bcfb44f
Revises: b44952831669
Create Date: 2026-07-29 18:54:25.745411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '8d789bcfb44f'
down_revision: Union[str, Sequence[str], None] = 'b44952831669'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Phase 1 of the multi-tenant migration (docs/MULTI-TENANT-ARCHITECTURE-REVIEW.md).
# This migration only creates the table and seeds the one organization every
# existing row will be backfilled onto in Phase 2. No existing table changes,
# no application code reads this table yet — purely additive, zero behavior
# change for the single tenant that exists today.
DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_ORGANIZATION_NAME = "Accenture"
DEFAULT_ORGANIZATION_SLUG = "accenture"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    organizations = sa.table(
        "organizations",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
    )
    op.bulk_insert(
        organizations,
        [
            {
                "id": DEFAULT_ORGANIZATION_ID,
                "name": DEFAULT_ORGANIZATION_NAME,
                "slug": DEFAULT_ORGANIZATION_SLUG,
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("organizations")
