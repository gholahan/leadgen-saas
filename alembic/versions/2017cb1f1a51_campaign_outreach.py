"""campaign_outreach

Revision ID: 2017cb1f1a51
Revises: 32d37e9a6889
Create Date: 2026-10-01 17:17:13.136322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2017cb1f1a51'
down_revision: Union[str, Sequence[str], None] = '32d37e9a6889'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'campaign_recipients',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('lead_id', sa.Uuid(), nullable=False),
        sa.Column('enrichment_id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('first_name', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'SENDING', 'SENT', 'FAILED', name='recipient_status'), nullable=False),
        sa.Column('provider_message_id', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['enrichment_id'], ['lead_enrichments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_campaign_recipients_campaign_id', 'campaign_recipients', ['campaign_id'], unique=False)
    op.create_index('idx_campaign_recipients_lead_id', 'campaign_recipients', ['lead_id'], unique=False)
    op.drop_table('campaign_leads')
    op.add_column('campaigns', sa.Column('job_id', sa.Uuid(), nullable=False))
    op.add_column('campaigns', sa.Column('subject', sa.Text(), nullable=False))
    op.add_column('campaigns', sa.Column('body', sa.Text(), nullable=False))
    op.add_column('campaigns', sa.Column('from_email', sa.Text(), nullable=True))
    op.add_column('campaigns', sa.Column('celery_task_id', sa.Text(), nullable=True))
    op.add_column('campaigns', sa.Column('cancel_requested', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('campaigns', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_campaigns_job_id', 'campaigns', 'jobs', ['job_id'], ['id'], ondelete='CASCADE')
    op.drop_column('campaigns', 'name')
    op.add_column('lead_enrichments', sa.Column('first_name', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_enrichments', 'first_name')
    op.add_column('campaigns', sa.Column('name', sa.TEXT(), autoincrement=False, nullable=False))
    op.drop_constraint('fk_campaigns_job_id', 'campaigns', type_='foreignkey')
    op.drop_column('campaigns', 'completed_at')
    op.drop_column('campaigns', 'cancel_requested')
    op.drop_column('campaigns', 'celery_task_id')
    op.drop_column('campaigns', 'from_email')
    op.drop_column('campaigns', 'body')
    op.drop_column('campaigns', 'subject')
    op.drop_column('campaigns', 'job_id')
    op.create_table(
        'campaign_leads',
        sa.Column('campaign_id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('lead_id', sa.UUID(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name='campaign_leads_campaign_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], name='campaign_leads_lead_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('campaign_id', 'lead_id', name='campaign_leads_pkey'),
    )
    op.drop_index('idx_campaign_recipients_lead_id', table_name='campaign_recipients')
    op.drop_index('idx_campaign_recipients_campaign_id', table_name='campaign_recipients')
    op.drop_table('campaign_recipients')
