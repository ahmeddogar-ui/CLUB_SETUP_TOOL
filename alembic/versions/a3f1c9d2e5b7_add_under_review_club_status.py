"""add under_review club status

Revision ID: a3f1c9d2e5b7
Revises: ea0b0ef2abf6
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d2e5b7'
down_revision: Union[str, Sequence[str], None] = 'ea0b0ef2abf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE clubstatus ADD VALUE IF NOT EXISTS 'under_review' AFTER 'submitted'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE clubstatus RENAME TO clubstatus_old")
    op.execute(
        "CREATE TYPE clubstatus AS ENUM "
        "('drafting', 'submitted', 'changes_requested', 'approved', 'rejected')"
    )
    op.execute(
        "ALTER TABLE clubs ALTER COLUMN status "
        "TYPE clubstatus USING status::text::clubstatus"
    )
    op.execute(
        "ALTER TABLE club_events ALTER COLUMN from_status "
        "TYPE clubstatus USING from_status::text::clubstatus"
    )
    op.execute(
        "ALTER TABLE club_events ALTER COLUMN to_status "
        "TYPE clubstatus USING to_status::text::clubstatus"
    )
    op.execute("DROP TYPE clubstatus_old")
