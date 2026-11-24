"""store user emails lowercased

Revision ID: e7a2c4f9d1b3
Revises: d4f8a1c6b3e2
Create Date: 2026-11-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7a2c4f9d1b3'
down_revision: Union[str, Sequence[str], None] = 'd4f8a1c6b3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fails on uq_users_email if two accounts differ only by case; those need a
    # human to decide which one survives, so stopping is the right outcome.
    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")
    op.create_check_constraint(
        op.f('ck_users_email_lowercase'), 'users', 'email = lower(email)'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('ck_users_email_lowercase'), 'users', type_='check')
