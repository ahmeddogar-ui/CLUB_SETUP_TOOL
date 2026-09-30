"""add requirement_id and link_url to club_events for requirement-level history

Revision ID: c5e8f1a3b2d4
Revises: b7d4e2a9c1f3
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e8f1a3b2d4'
down_revision: Union[str, Sequence[str], None] = 'b7d4e2a9c1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('club_events', sa.Column('requirement_id', sa.Integer(), nullable=True))
    op.add_column('club_events', sa.Column('link_url', sa.String(), nullable=True))
    op.create_foreign_key(
        op.f('fk_club_events_requirement_id'),
        'club_events',
        'requirements',
        ['requirement_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f('fk_club_events_requirement_id'), 'club_events', type_='foreignkey'
    )
    op.drop_column('club_events', 'link_url')
    op.drop_column('club_events', 'requirement_id')
