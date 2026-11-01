"""add_email_delivery_tracking

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-10-05 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_recipients",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign_recipients",
        sa.Column("bounced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign_recipients",
        sa.Column("bounce_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "campaign_recipients",
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign_recipients",
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaign_recipients",
        sa.Column("complained_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "email_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_recipient_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("provider_event_id", sa.Text(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_recipient_id"],
            ["campaign_recipients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_email_events_campaign_recipient_id",
        "email_events",
        ["campaign_recipient_id"],
    )
    op.create_index(
        "idx_email_events_provider_event_id",
        "email_events",
        ["provider_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_email_events_provider_event_id", table_name="email_events"
    )
    op.drop_index(
        "idx_email_events_campaign_recipient_id", table_name="email_events"
    )
    op.drop_table("email_events")

    op.drop_column("campaign_recipients", "complained_at")
    op.drop_column("campaign_recipients", "clicked_at")
    op.drop_column("campaign_recipients", "opened_at")
    op.drop_column("campaign_recipients", "bounce_type")
    op.drop_column("campaign_recipients", "bounced_at")
    op.drop_column("campaign_recipients", "delivered_at")
