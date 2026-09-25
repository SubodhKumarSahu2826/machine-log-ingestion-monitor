"""add failed to incidentstate enum

Revision ID: c9e52f118da1
Revises: a7a413cb9508
Create Date: 2026-09-25 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c9e52f118da1'
down_revision: Union[str, Sequence[str], None] = 'a7a413cb9508'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add FAILED value to incidentstate enum."""
    op.execute("ALTER TYPE incidentstate ADD VALUE IF NOT EXISTS 'FAILED'")


def downgrade() -> None:
    """Downgrade schema (Postgres enum values cannot be easily removed without dropping the type)."""
    pass
