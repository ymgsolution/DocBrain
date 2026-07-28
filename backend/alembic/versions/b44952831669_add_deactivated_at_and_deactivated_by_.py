"""add deactivated_at and deactivated_by to users

Revision ID: b44952831669
Revises: 3711e1bdb61b
Create Date: 2026-07-28 23:56:55.869498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b44952831669'
down_revision: Union[str, Sequence[str], None] = '3711e1bdb61b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Who cut someone off, and when — the same audit pair documents already carry as
# deleted_at/deleted_by. is_active alone answers "can they get in", never "who
# decided that", which is the question actually asked after the fact.
#
# deactivated_by is ON DELETE SET NULL rather than RESTRICT: an admin leaving
# must not be blocked by, or erase, the record of people they deactivated. The
# timestamp survives even when the actor doesn't.
#
# Both nullable — an active user has neither, and every existing row predates
# the concept.


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('deactivated_by', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_users_deactivated_by_users',
        'users',
        'users',
        ['deactivated_by'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_users_deactivated_by_users', 'users', type_='foreignkey')
    op.drop_column('users', 'deactivated_by')
    op.drop_column('users', 'deactivated_at')
