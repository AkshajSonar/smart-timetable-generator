"""Add batch_id to assignment

Revision ID: 9452e804bdfc
Revises: 002
Create Date: 2026-09-08 17:13:30.925078

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '9452e804bdfc'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('assignment', sa.Column('batch_id', sa.UUID(as_uuid=True), sa.ForeignKey('batch.id'), nullable=True))
    op.add_column('eligibility', sa.Column('batch_id', sa.UUID(as_uuid=True), sa.ForeignKey('batch.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('eligibility', 'batch_id')
    op.drop_column('assignment', 'batch_id')
