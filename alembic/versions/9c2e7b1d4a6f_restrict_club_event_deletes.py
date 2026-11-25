"""club_events.club_id: ON DELETE RESTRICT instead of CASCADE

Revision ID: 9c2e7b1d4a6f
Revises: f3b8d2a6c9e1
Create Date: 2026-11-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c2e7b1d4a6f"
down_revision: Union[str, Sequence[str], None] = "f3b8d2a6c9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = "fk_club_events_club_id"


def upgrade() -> None:
    """Upgrade schema."""
    # The append-only trigger already blocks deleting events, so CASCADE could
    # never succeed; RESTRICT states the same rule in the schema itself.
    op.drop_constraint(CONSTRAINT, "club_events", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT, "club_events", "clubs", ["club_id"], ["id"], ondelete="RESTRICT"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(CONSTRAINT, "club_events", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT, "club_events", "clubs", ["club_id"], ["id"], ondelete="CASCADE"
    )
