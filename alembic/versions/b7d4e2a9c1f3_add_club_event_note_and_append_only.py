"""add club_events.note and make club_events append-only

Revision ID: b7d4e2a9c1f3
Revises: a3f1c9d2e5b7
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d4e2a9c1f3'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d2e5b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('club_events', sa.Column('note', sa.String(), nullable=True))

    # History is permanent: reject any UPDATE or DELETE on an existing event row
    # at the database level, so no code path (or manual query) can rewrite it.
    op.execute(
        """
        CREATE FUNCTION club_events_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'club_events is append-only: % is not allowed', TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER club_events_append_only
        BEFORE UPDATE OR DELETE ON club_events
        FOR EACH ROW EXECUTE FUNCTION club_events_append_only()
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER club_events_append_only ON club_events")
    op.execute("DROP FUNCTION club_events_append_only()")
    op.drop_column('club_events', 'note')
