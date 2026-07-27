"""add share_links table

Revision ID: acd53d2f12ab
Revises: 516ce3585a6e
Create Date: 2026-07-27 22:07:38.886193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acd53d2f12ab'
down_revision: Union[str, Sequence[str], None] = '516ce3585a6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Note: autogenerate again flagged ux_categories_name_lower, ix_documents_active_updated_at,
# ix_documents_search_vector, and ix_document_vector_embeddings_embedding_hnsw as "removed" — the
# same pre-existing false positive documented in every migration since a8e785ca1e16 (hand-added via
# op.execute()/postgresql_using, invisible to the ORM's Index() metadata). Stripped below.
#
# External share links: purely additive — one new table, no changes to any existing table, so
# every current query and endpoint behaves identically before and after this migration.
# Both FKs cascade, so hard-deleting a document takes its share links with it and can't leave a
# live link pointing at content that no longer exists.


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('share_links',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('document_version_id', sa.UUID(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('view_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_share_links_document_id'), 'share_links', ['document_id'], unique=False)
    # Unique: the token hash is how a public request finds its link, and two
    # links must never resolve to the same lookup.
    op.create_index(op.f('ix_share_links_token_hash'), 'share_links', ['token_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_share_links_token_hash'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_document_id'), table_name='share_links')
    op.drop_table('share_links')
