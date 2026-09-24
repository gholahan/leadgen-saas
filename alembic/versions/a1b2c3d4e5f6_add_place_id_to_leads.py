"""add place_id to leads

Revision ID: a1b2c3d4e5f6
Revises: 7b6c4d2e1f90
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "7b6c4d2e1f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("place_id", sa.Text(), nullable=True))
    op.create_index("idx_leads_place_id", "leads", ["place_id"])


def downgrade() -> None:
    op.drop_index("idx_leads_place_id", table_name="leads")
    op.drop_column("leads", "place_id")
