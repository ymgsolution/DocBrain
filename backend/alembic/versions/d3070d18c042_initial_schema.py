"""initial schema

Revision ID: d3070d18c042
Revises:
Create Date: 2026-07-23 17:34:47.222063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3070d18c042'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### tables ###
    op.create_table('categories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('default_review_period_days', sa.Integer(), nullable=True),
    sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('tags',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('normalized_name', sa.String(), nullable=False),
    sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('normalized_name')
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=False),
    sa.Column('role', sa.Enum('EMPLOYEE', 'REVIEWER', 'ADMIN', name='user_role'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category_id', sa.UUID(), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    # current_version_id's FK to document_versions is added later via a
    # separate ALTER TABLE, once document_versions exists — see below.
    # This is the resolution for the circular FK between the two tables.
    sa.Column('current_version_id', sa.UUID(), nullable=True),
    sa.Column('version_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('review_due_date', sa.Date(), nullable=True),
    sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_reviewed_by', sa.UUID(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'DELETED', name='document_status'), server_default='ACTIVE', nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.UUID(), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
    sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['last_reviewed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_category_id'), 'documents', ['category_id'], unique=False)
    op.create_index(op.f('ix_documents_owner_id'), 'documents', ['owner_id'], unique=False)
    op.create_index(op.f('ix_documents_review_due_date'), 'documents', ['review_due_date'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index(op.f('ix_documents_updated_at'), 'documents', ['updated_at'], unique=False)
    op.create_table('user_preferences',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('theme', sa.Enum('light', 'dark', 'system', name='theme_preference'), server_default='system', nullable=False),
    sa.Column('default_page_size', sa.Integer(), server_default='25', nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('activity_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('actor_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.Enum('CREATED', 'VERSION_UPLOADED', 'VERSION_RESTORED', 'METADATA_UPDATED', 'REVIEWED', 'DELETED', 'RESTORED', name='activity_event_type'), nullable=False),
    sa.Column('summary', sa.String(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_events_occurred_at'), 'activity_events', ['occurred_at'], unique=False)
    op.create_table('document_tags',
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('tag_id', sa.UUID(), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('document_id', 'tag_id')
    )
    op.create_table('document_versions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('version_number', sa.Integer(), nullable=False),
    sa.Column('storage_path', sa.String(), nullable=False),
    sa.Column('original_filename', sa.String(), nullable=False),
    sa.Column('mime_type', sa.String(), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
    sa.Column('change_note', sa.Text(), nullable=True),
    sa.Column('uploaded_by', sa.UUID(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('restored_from_version_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['restored_from_version_id'], ['document_versions.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'version_number', name='uq_document_versions_document_id_version_number')
    )
    op.create_index(op.f('ix_document_versions_document_id'), 'document_versions', ['document_id'], unique=False)

    # Now that document_versions exists, close the circular reference.
    op.create_foreign_key(
        'fk_documents_current_version_id',
        'documents', 'document_versions',
        ['current_version_id'], ['id'],
        ondelete='SET NULL',
    )

    # ### Postgres-specific indexes not expressible from the ORM alone ###

    # Case-insensitive uniqueness on category name (§7.2: "Unique, case-insensitive").
    op.execute("CREATE UNIQUE INDEX ux_categories_name_lower ON categories (lower(name))")

    # Full-text search (§7.2, §18.5): GIN index on the tsvector column.
    op.create_index(
        'ix_documents_search_vector', 'documents', ['search_vector'],
        unique=False, postgresql_using='gin',
    )

    # Partial index (§7.2): the Explorer's default query is "active docs, newest first".
    op.execute(
        "CREATE INDEX ix_documents_active_updated_at ON documents (updated_at DESC) "
        "WHERE status = 'ACTIVE'"
    )

    # ### Triggers: system-owned denormalised state (§7.2, §11.3) ###
    # search_vector is recomputed from title/description/category/tags/current-filename
    # on every insert or update to documents — the tsvector can't be a plain generated
    # column because it depends on other tables (categories, tags via document_tags,
    # document_versions for the current filename).
    op.execute(
        """
        CREATE FUNCTION documents_search_vector_refresh() RETURNS trigger AS $$
        DECLARE
            cat_name text;
            tag_names text;
            file_name text;
        BEGIN
            SELECT name INTO cat_name FROM categories WHERE id = NEW.category_id;
            SELECT string_agg(t.name, ' ') INTO tag_names
                FROM document_tags dt JOIN tags t ON t.id = dt.tag_id
                WHERE dt.document_id = NEW.id;
            SELECT original_filename INTO file_name
                FROM document_versions WHERE id = NEW.current_version_id;

            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(tag_names, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(cat_name, '') || ' ' || coalesce(file_name, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_documents_search_vector
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION documents_search_vector_refresh();
        """
    )

    # Retagging a document must refresh its search_vector (tag names changed) and
    # its updated_at (it's a real change to the document, per §15.4).
    op.execute(
        """
        CREATE FUNCTION document_tags_touch_document() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                UPDATE documents SET updated_at = now() WHERE id = OLD.document_id;
                RETURN OLD;
            ELSE
                UPDATE documents SET updated_at = now() WHERE id = NEW.document_id;
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_tags_touch_document
        AFTER INSERT OR DELETE ON document_tags
        FOR EACH ROW EXECUTE FUNCTION document_tags_touch_document();
        """
    )

    # documents.version_count is denormalised (§7.2) — the DB, not application code,
    # is the arbiter of version state (§11.4), so it's kept in sync here.
    op.execute(
        """
        CREATE FUNCTION document_versions_bump_count() RETURNS trigger AS $$
        BEGIN
            UPDATE documents SET version_count = version_count + 1 WHERE id = NEW.document_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_versions_bump_count
        AFTER INSERT ON document_versions
        FOR EACH ROW EXECUTE FUNCTION document_versions_bump_count();
        """
    )

    # tags.usage_count is denormalised (§7.2) for sort-by-usage in tag admin/autocomplete.
    op.execute(
        """
        CREATE FUNCTION document_tags_adjust_usage_count() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_tags_adjust_usage_count
        AFTER INSERT OR DELETE ON document_tags
        FOR EACH ROW EXECUTE FUNCTION document_tags_adjust_usage_count();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_document_tags_adjust_usage_count ON document_tags")
    op.execute("DROP FUNCTION IF EXISTS document_tags_adjust_usage_count()")
    op.execute("DROP TRIGGER IF EXISTS trg_document_versions_bump_count ON document_versions")
    op.execute("DROP FUNCTION IF EXISTS document_versions_bump_count()")
    op.execute("DROP TRIGGER IF EXISTS trg_document_tags_touch_document ON document_tags")
    op.execute("DROP FUNCTION IF EXISTS document_tags_touch_document()")
    op.execute("DROP TRIGGER IF EXISTS trg_documents_search_vector ON documents")
    op.execute("DROP FUNCTION IF EXISTS documents_search_vector_refresh()")

    op.execute("DROP INDEX IF EXISTS ix_documents_active_updated_at")
    op.drop_index('ix_documents_search_vector', table_name='documents', postgresql_using='gin')
    op.execute("DROP INDEX IF EXISTS ux_categories_name_lower")

    op.drop_constraint('fk_documents_current_version_id', 'documents', type_='foreignkey')

    op.drop_index(op.f('ix_document_versions_document_id'), table_name='document_versions')
    op.drop_table('document_versions')
    op.drop_table('document_tags')
    op.drop_index(op.f('ix_activity_events_occurred_at'), table_name='activity_events')
    op.drop_table('activity_events')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_documents_updated_at'), table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_review_due_date'), table_name='documents')
    op.drop_index(op.f('ix_documents_owner_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_category_id'), table_name='documents')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('tags')
    op.drop_table('categories')
