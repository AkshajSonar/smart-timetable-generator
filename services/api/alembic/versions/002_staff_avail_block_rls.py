"""Add tenant_id + RLS to staff_availability_block — §32 #19.

Revision ID: 002_staff_avail_block_rls
Revises: 001
Create Date: 2026-09-08
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tenant_id column, backfill from staff_profile.tenant_id, then constrain NOT NULL.
    op.add_column(
        "staff_availability_block",
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=True),
    )

    # Backfill from parent staff_profile row.
    op.execute(
        """
        UPDATE staff_availability_block sab
        SET tenant_id = sp.tenant_id
        FROM staff_profile sp
        WHERE sab.staff_profile_id = sp.id
        """
    )

    # Now enforce NOT NULL — all rows have been backfilled.
    op.alter_column("staff_availability_block", "tenant_id", nullable=False)

    # Create index for RLS lookups.
    op.create_index(
        "ix_staff_availability_block_tenant_id",
        "staff_availability_block",
        ["tenant_id"],
    )

    # Enable RLS and apply standard tenant_isolation policy (invariant #3, §32 #19).
    op.execute("ALTER TABLE staff_availability_block ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON staff_availability_block "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid);"
    )
    op.execute("ALTER TABLE staff_availability_block FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON staff_availability_block;")
    op.execute("ALTER TABLE staff_availability_block DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_staff_availability_block_tenant_id", table_name="staff_availability_block")
    op.drop_column("staff_availability_block", "tenant_id")
