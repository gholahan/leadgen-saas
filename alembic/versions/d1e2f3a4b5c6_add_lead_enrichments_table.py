"""add lead_enrichments table

Revision ID: d1e2f3a4b5c6
Revises: 30353b54044b
Create Date: 2026-09-26 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "30353b54044b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead_enrichments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("email_type", sa.Text(), nullable=True),
        sa.Column("email_score", sa.Integer(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("FOUND", "NOT_FOUND", "FAILED", name="enrichment_status"),
            nullable=False,
            server_default="NOT_FOUND",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("lead_enrichments")
