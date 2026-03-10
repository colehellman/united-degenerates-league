"""add_team_season_record_columns

Revision ID: 56d1db22aeae
Revises: 002_add_bug_reports_table
Create Date: 2026-03-10 08:31:54.227214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56d1db22aeae'
down_revision: Union[str, None] = '002_add_bug_reports_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add season-record columns to teams.  Nullable so existing rows keep
    # working until the next sync populates values.
    op.add_column('teams', sa.Column('wins', sa.Integer(), nullable=True))
    op.add_column('teams', sa.Column('losses', sa.Integer(), nullable=True))
    op.add_column('teams', sa.Column('ties', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('teams', 'ties')
    op.drop_column('teams', 'losses')
    op.drop_column('teams', 'wins')
