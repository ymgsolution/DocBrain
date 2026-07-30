"""add password_hash to users

Revision ID: 866a737e169d
Revises: b7c1e4a9d520
Create Date: 2026-07-28 19:21:00.562611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '866a737e169d'
down_revision: Union[str, Sequence[str], None] = 'b7c1e4a9d520'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Nullable on purpose — see the column's comment in app/db/models/user.py: an invited user
# exists before they have a password, and every existing row predates passwords entirely.
# Making it NOT NULL would need a backfill and would still be wrong for pending invites.
#
# (Autogenerate again flagged the four hand-written indexes as "removed"; stripped, same as
# every migration since a8e785ca1e16.)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'password_hash')
