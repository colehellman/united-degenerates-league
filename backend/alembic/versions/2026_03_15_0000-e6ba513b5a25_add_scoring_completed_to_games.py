"""add scoring_completed flag to games

Revision ID: e6ba513b5a25
Revises: 83f04277ba07
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6ba513b5a25'
down_revision: Union[str, None] = '83f04277ba07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('games', sa.Column('scoring_completed', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_games_scoring_completed', 'games', ['scoring_completed'])
    # Backfill: mark all existing FINAL games as scored (they were scored
    # under the old logic, or their scoring window has passed).
    # Use sa.text() with a bind parameter to avoid asyncpg enum casting issues.
    op.execute(sa.text("UPDATE games SET scoring_completed = true WHERE status = CAST(:s AS gamestatus)").bindparams(s="final"))


def downgrade() -> None:
    op.drop_index('ix_games_scoring_completed', 'games')
    op.drop_column('games', 'scoring_completed')
