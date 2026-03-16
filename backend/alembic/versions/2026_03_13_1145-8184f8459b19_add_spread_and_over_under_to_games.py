"""add spread and over_under to games

Revision ID: 8184f8459b19
Revises: eeb5216a1f51
Create Date: 2026-03-13 11:45:50.776561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8184f8459b19'
down_revision: Union[str, None] = 'eeb5216a1f51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
