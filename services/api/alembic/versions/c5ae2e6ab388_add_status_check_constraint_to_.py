"""Add status check constraint to constraint_rule

Revision ID: c5ae2e6ab388
Revises: 93693f792aa4
Create Date: 2026-09-10 16:33:12.377150

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c5ae2e6ab388'
down_revision: Union[str, None] = '93693f792aa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "constraint_rule_status_check",
        "constraint_rule",
        "status IN ('pending_confirmation', 'confirmed')"
    )

def downgrade() -> None:
    op.drop_constraint("constraint_rule_status_check", "constraint_rule", type_="check")
