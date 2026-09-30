"""add indexes for the club-history and admin-review-queue access patterns

Revision ID: d4f8a1c6b3e2
Revises: c5e8f1a3b2d4
Create Date: 2026-09-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4f8a1c6b3e2'
down_revision: Union[str, Sequence[str], None] = 'c5e8f1a3b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Serves GET /clubs/{id}/events: filter by club_id, sort by created_at DESC --
    # one index covers both instead of a separate scan-then-sort.
    op.create_index(
        'idx_events_club_time',
        'club_events',
        ['club_id', sa.text('created_at DESC')],
    )
    # Serves the admin review queue (GET /clubs?status=&sort=): filter by status,
    # sort by updated_at.
    op.create_index(
        'idx_clubs_status_updated',
        'clubs',
        ['status', 'updated_at'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_clubs_status_updated', table_name='clubs')
    op.drop_index('idx_events_club_time', table_name='club_events')
