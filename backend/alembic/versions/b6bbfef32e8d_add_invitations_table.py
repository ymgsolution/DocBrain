"""add invitations table

Revision ID: b6bbfef32e8d
Revises: 866a737e169d
Create Date: 2026-07-28 22:41:55.276722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


# revision identifiers, used by Alembic.
revision: str = 'b6bbfef32e8d'
down_revision: Union[str, Sequence[str], None] = '866a737e169d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Invite-only signup: this table is the only route to a new account.
#
# Note the user_role enum is reused with create_type=False — it already exists (users.role).
# Plain sa.Enum silently ignores that kwarg, which is what caused the "type already exists"
# failure in ce5e3e5c56bd; postgresql.ENUM is the one that honours it.
#
# (Autogenerate again flagged the four hand-written indexes as "removed"; stripped.)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('invitations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('role', PGEnum('EMPLOYEE', 'REVIEWER', 'ADMIN', name='user_role', create_type=False), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('invited_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('accepted_user_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['accepted_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invitations_email'), 'invitations', ['email'], unique=False)
    op.create_index(op.f('ix_invitations_token_hash'), 'invitations', ['token_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_invitations_token_hash'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_email'), table_name='invitations')
    op.drop_table('invitations')
