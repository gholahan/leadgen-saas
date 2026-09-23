"""remove user_id from leads

Revision ID: 7b6c4d2e1f90
Revises: 30353b54044b
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b6c4d2e1f90"
down_revision: Union[str, Sequence[str], None] = "30353b54044b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_leads_user_id", table_name="leads")
    op.drop_column("leads", "user_id")


def downgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "leads_user_id_fkey",
        "leads",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_leads_user_id", "leads", ["user_id"])