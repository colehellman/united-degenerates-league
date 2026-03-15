"""add unique constraints for fixed team selection exclusivity

Revision ID: a1b2c3d4e5f6
Revises: eeb5216a1f51
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'eeb5216a1f51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enforce exclusivity: only one user can select a given team per competition
    op.create_unique_constraint(
        'uq_fixed_selection_competition_team',
        'fixed_team_selections',
        ['competition_id', 'team_id'],
    )
    # Enforce exclusivity: only one user can select a given golfer per competition
    op.create_unique_constraint(
        'uq_fixed_selection_competition_golfer',
        'fixed_team_selections',
        ['competition_id', 'golfer_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_fixed_selection_competition_golfer', 'fixed_team_selections', type_='unique')
    op.drop_constraint('uq_fixed_selection_competition_team', 'fixed_team_selections', type_='unique')
