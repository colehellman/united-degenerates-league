"""Add bug_reports table

Revision ID: 002_add_bug_reports_table
Revises: 001_initial_schema
Create Date: 2026-03-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_bug_reports_table'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bugreportstatus_enum = sa.Enum(
        'OPEN', 'IN_REVIEW', 'RESOLVED', 'CLOSED',
        name='bugreportstatus',
    )
    bugreportcategory_enum = sa.Enum(
        'UI', 'PERFORMANCE', 'DATA', 'AUTH', 'OTHER',
        name='bugreportcategory',
    )

    op.create_table(
        'bug_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000), nullable=False),
        sa.Column('status', bugreportstatus_enum, nullable=False, server_default='OPEN'),
        sa.Column('category', bugreportcategory_enum, nullable=False, server_default='OTHER'),
        sa.Column('page_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_bug_reports_id', 'bug_reports', ['id'])
    op.create_index('ix_bug_reports_user_id', 'bug_reports', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_bug_reports_user_id', table_name='bug_reports')
    op.drop_index('ix_bug_reports_id', table_name='bug_reports')
    op.drop_table('bug_reports')
    op.execute("DROP TYPE IF EXISTS bugreportstatus")
    op.execute("DROP TYPE IF EXISTS bugreportcategory")
