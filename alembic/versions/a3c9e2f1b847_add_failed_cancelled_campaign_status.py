"""add FAILED and CANCELLED to campaign_status enum

Revision ID: a3c9e2f1b847
Revises: f42a8c1d9e30
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a3c9e2f1b847"
down_revision: Union[str, Sequence[str], None] = "f42a8c1d9e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'FAILED'")
    op.execute("ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without recreating the type.
    pass
