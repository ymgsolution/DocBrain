"""add platform_admins table

Revision ID: a3b7efaeff2c
Revises: 8ebd25762f70
Create Date: 2026-07-29 20:10:54.145565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a3b7efaeff2c'
down_revision: Union[str, Sequence[str], None] = '8ebd25762f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Phase A of the Super Admin feature. Schema only — no seed row here on
# purpose: unlike the Accenture organization (a harmless name+slug), a
# platform admin needs a real password, and hardcoding a credential's hash
# into a migration means it lives in git history forever. The bootstrap
# account is created by scripts/create_platform_admin.py instead, the same
# separation already used for regular users (seed.py creates the accounts,
# set_demo_passwords.py sets their credentials — never a migration).
#
# No organization_id column, and never will be one: that's the entire point
# of this table existing separately from users (see the model's docstring).


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "platform_admins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_platform_admins_email"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("platform_admins")
