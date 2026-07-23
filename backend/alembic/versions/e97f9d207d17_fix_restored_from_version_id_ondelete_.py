"""fix restored_from_version_id ondelete to SET NULL

Revision ID: e97f9d207d17
Revises: d3070d18c042
Create Date: 2026-07-23 18:06:58.205275

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e97f9d207d17'
down_revision: Union[str, Sequence[str], None] = 'd3070d18c042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Note: autogenerate also flagged ux_categories_name_lower, ix_documents_active_updated_at,
# and ix_documents_search_vector as "removed" — that's noise, not a real diff. Those three
# were added by hand via op.execute()/postgresql_using in the initial migration, so they
# aren't represented in the ORM's Index() metadata and autogenerate can't see they still
# exist. Left untouched here; only the FK fix below is real.


def upgrade() -> None:
    op.drop_constraint(
        'document_versions_restored_from_version_id_fkey', 'document_versions', type_='foreignkey'
    )
    op.create_foreign_key(
        'document_versions_restored_from_version_id_fkey',
        'document_versions', 'document_versions',
        ['restored_from_version_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'document_versions_restored_from_version_id_fkey', 'document_versions', type_='foreignkey'
    )
    op.create_foreign_key(
        'document_versions_restored_from_version_id_fkey',
        'document_versions', 'document_versions',
        ['restored_from_version_id'], ['id'],
    )
