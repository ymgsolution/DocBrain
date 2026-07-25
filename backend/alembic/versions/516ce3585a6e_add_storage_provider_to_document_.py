"""add storage_provider to document_versions

Revision ID: 516ce3585a6e
Revises: ce5e3e5c56bd
Create Date: 2026-07-25 18:29:26.233334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '516ce3585a6e'
down_revision: Union[str, Sequence[str], None] = 'ce5e3e5c56bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Note: autogenerate again flagged ux_categories_name_lower, ix_documents_active_updated_at,
# ix_documents_search_vector, and ix_document_vector_embeddings_embedding_hnsw as "removed" — the
# same pre-existing false positive documented in every migration since a8e785ca1e16 (hand-added via
# op.execute()/postgresql_using, invisible to the ORM's Index() metadata). Stripped below.
#
# Storage migration track: server_default='local' backfills every existing row in the same
# statement that adds the column — no separate data migration needed, since "local" is exactly
# where every version uploaded before this migration actually lives.


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('document_versions', sa.Column('storage_provider', sa.String(), server_default='local', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('document_versions', 'storage_provider')
