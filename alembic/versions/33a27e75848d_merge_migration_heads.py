"""merge migration heads

Revision ID: 33a27e75848d
Revises: a1b2c3d4e5f6, d1e2f3a4b5c6
Create Date: 2026-10-01 09:15:22.017061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '33a27e75848d'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'd1e2f3a4b5c6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass