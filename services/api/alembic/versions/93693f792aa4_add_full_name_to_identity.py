"""Add full_name to identity

Revision ID: 93693f792aa4
Revises: 54615ef1f173
Create Date: 2026-09-10 12:00:16.119711

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '93693f792aa4'
down_revision: Union[str, None] = '54615ef1f173'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("identity", sa.Column("full_name", sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column("identity", "full_name")
