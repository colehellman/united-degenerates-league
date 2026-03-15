"""add unique constraint on game competition_id and external_id

Revision ID: 83f04277ba07
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '83f04277ba07'
down_revision: Union[str, None] = '2a5933ecc3a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_game_competition_external_id', 'games', ['competition_id', 'external_id'])


def downgrade() -> None:
    op.drop_constraint('uq_game_competition_external_id', 'games', type_='unique')
