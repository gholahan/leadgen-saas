"""add RUNNING to campaign_status enum

Revision ID: f42a8c1d9e30
Revises: 2017cb1f1a51
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f42a8c1d9e30"
down_revision: Union[str, Sequence[str], None] = "2017cb1f1a51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'RUNNING'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without recreating the type.
    pass
