"""make campaign recipients idempotent

Revision ID: e5f6a7b8c9d0
Revises: a3c9e2f1b847
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "a3c9e2f1b847"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM campaign_recipients AS recipient
        USING (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY campaign_id, enrichment_id
                       ORDER BY CASE WHEN status::text = 'SENT' THEN 0 ELSE 1 END,
                                created_at,
                                id
                   ) AS row_number
            FROM campaign_recipients
        ) AS duplicates
        WHERE recipient.id = duplicates.id AND duplicates.row_number > 1
        """
    )
    op.create_unique_constraint(
        "uq_campaign_recipient_enrichment",
        "campaign_recipients",
        ["campaign_id", "enrichment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_campaign_recipient_enrichment",
        "campaign_recipients",
        type_="unique",
    )
