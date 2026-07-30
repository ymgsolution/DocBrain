"""add password_reset_tokens table

Revision ID: 3711e1bdb61b
Revises: b6bbfef32e8d
Create Date: 2026-07-28 22:59:19.314804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3711e1bdb61b'
down_revision: Union[str, Sequence[str], None] = 'b6bbfef32e8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deliberately separate from `invitations` rather than sharing one table behind a `purpose`
# column: the two look alike but mean opposite things (create an account vs. change an existing
# one's credentials), and merging them would make it possible for a bug to let one act as the
# other. CASCADE on user_id so deleting a user takes their outstanding reset tokens with them.
#
# (Autogenerate again flagged the four hand-written indexes as "removed"; stripped.)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_token_hash'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
