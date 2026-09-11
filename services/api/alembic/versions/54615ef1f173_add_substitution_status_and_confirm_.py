"""add_substitution_status_and_confirm_endpoint

Revision ID: 54615ef1f173
Revises: 6ec8a635c353
Create Date: 2026-09-10 11:00:59.266508

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '54615ef1f173'
down_revision: Union[str, None] = '6ec8a635c353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column with check constraint; default 'suggested' for existing rows
    op.add_column(
        "substitution_log",
        sa.Column("status", sa.String(), nullable=False, server_default="suggested"),
    )
    op.create_check_constraint(
        "substitution_log_status_check",
        "substitution_log",
        "status IN ('suggested','confirmed','cancelled')",
    )
    # Make substitute_staff_profile_id nullable (was NOT NULL; set at confirm time, not suggest time)
    op.alter_column(
        "substitution_log",
        "substitute_staff_profile_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.drop_constraint("substitution_log_status_check", "substitution_log", type_="check")
    op.drop_column("substitution_log", "status")
    # Reverting nullable requires any NULLs to be filled first — not safe in prod, but correct for test rollback
    op.alter_column(
        "substitution_log",
        "substitute_staff_profile_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
