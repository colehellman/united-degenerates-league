"""Add suspended/banned account statuses and new audit actions

Revision ID: a1b2c3d4e5f6
Revises: f7a8b2c3d4e5
Create Date: 2026-03-15

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f7a8b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new values to accountstatus enum
    op.execute("ALTER TYPE accountstatus ADD VALUE IF NOT EXISTS 'suspended'")
    op.execute("ALTER TYPE accountstatus ADD VALUE IF NOT EXISTS 'banned'")

    # Add new values to auditaction enum
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'participant_removed'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'user_suspended'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'user_banned'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'user_reactivated'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # A full enum replacement would be needed, but since we have no
    # production data yet this is acceptable.
    pass
