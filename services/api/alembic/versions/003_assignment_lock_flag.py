"""Add is_locked to assignment for FR-9.2 cell locking.

Revision ID: 003_assignment_lock_flag
Revises: da27bdf843b4
Create Date: 2026-09-09

FR-9.2: Regeneration must never overwrite manually-fixed slots.
is_locked=True marks an assignment as manually edited; the solver
treats these as pinned (via AddHint) on re-solve.

locked_by stores the identity_id of the editor for audit purposes
(FR-9.4 audit trail complement to audit_log table).
"""

from alembic import op
import sqlalchemy as sa

revision = "003_assignment_lock_flag"
down_revision = "da27bdf843b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "assignment",
        sa.Column("is_locked", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "assignment",
        sa.Column(
            "locked_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("assignment", "locked_by")
    op.drop_column("assignment", "is_locked")
