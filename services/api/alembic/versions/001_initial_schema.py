"""001 initial schema — all §17/§28 tables + §32 additions + RLS policies.

Revision ID: 001
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

# Every tenant-scoped table gets this RLS policy in the same migration (invariant #3).
# Excludes: identity (tenant-independent), staff_availability_block (tenant_id added in
# migration 002 — §32 #19), exam_session (scoped via FK), and tenant itself (self-ref).
TENANT_SCOPED_TABLES = [
    "academic_term",
    "campus",
    "department",
    "course",
    "cohort",
    "batch",
    "room",
    "staff_profile",
    "student_profile",
    "eligibility",
    "period_template",
    "constraint_rule",
    "elective_section",
    "enrollment_record",
    "exception_calendar",
    "timetable_version",
    "assignment",
    "exam_timetable_version",
    "substitution_log",
    "audit_log",
    "notification",
]


def upgrade() -> None:
    # --- identity (tenant-independent, no RLS) ---
    op.create_table(
        "identity",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("auth_provider_ref", sa.String, nullable=True),
        sa.Column("platform_role", sa.String, nullable=True),
    )

    # --- tenant ---
    op.create_table(
        "tenant",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("institution_type", sa.String, nullable=False),
        sa.Column("timezone", sa.String, nullable=False, server_default="UTC"),
        sa.Column("enabled_modules", JSONB, nullable=False, server_default="{}"),
        sa.Column("isolation_mode", sa.String, nullable=False, server_default="row"),
    )

    # --- academic_term (§32 #16) ---
    op.create_table(
        "academic_term",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
    )

    # --- campus ---
    op.create_table(
        "campus",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("timezone", sa.String, nullable=True),
    )

    # --- department ---
    op.create_table(
        "department",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String, nullable=False),
    )

    # --- course (+ required_equipment_tags §32 #15) ---
    op.create_table(
        "course",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("department.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("credit_value", sa.Numeric, nullable=True),
        sa.Column("hours_per_week", sa.Integer, nullable=False),
        sa.Column("block_size", sa.Integer, nullable=False, server_default="1"),
        sa.Column("required_equipment_tags", JSONB, nullable=False, server_default="[]"),
    )

    # --- cohort ---
    op.create_table(
        "cohort",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("type", sa.String, nullable=False, server_default="fixed"),
    )

    # --- batch (+ denormalized tenant_id §32 #18) ---
    op.create_table(
        "batch",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_id", UUID(as_uuid=True), sa.ForeignKey("cohort.id"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("label", sa.String, nullable=False),
    )

    # --- room ---
    op.create_table(
        "room",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("campus_id", UUID(as_uuid=True), sa.ForeignKey("campus.id"), nullable=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("capacity", sa.Integer, nullable=False),
        sa.Column("equipment_tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("accessible", sa.Boolean, nullable=False, server_default="false"),
    )

    # --- staff_profile ---
    op.create_table(
        "staff_profile",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("identity_id", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=False),
        sa.Column("employment_type", sa.String, nullable=False),
        sa.Column("workload_cap_week", sa.Integer, nullable=False),
        sa.Column("workload_cap_day", sa.Integer, nullable=False),
        sa.Column("roles", JSONB, nullable=False, server_default="[]"),
    )

    # --- staff_availability_block (§32 #17) ---
    op.create_table(
        "staff_availability_block",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("staff_profile_id", UUID(as_uuid=True), sa.ForeignKey("staff_profile.id"), nullable=False),
        sa.Column("weekday", sa.Integer, nullable=False),
        sa.Column("period_index", sa.Integer, nullable=False),
        sa.Column("block_type", sa.String, nullable=False),
    )

    # --- student_profile ---
    op.create_table(
        "student_profile",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("identity_id", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=True),
        sa.Column("external_student_code", sa.String, nullable=True),
        sa.Column("cohort_id", UUID(as_uuid=True), sa.ForeignKey("cohort.id"), nullable=True),
    )

    # --- eligibility (+ denormalized tenant_id §32 #18) ---
    op.create_table(
        "eligibility",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("staff_profile_id", UUID(as_uuid=True), sa.ForeignKey("staff_profile.id"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("cohort_id", UUID(as_uuid=True), sa.ForeignKey("cohort.id"), nullable=False),
        sa.UniqueConstraint("staff_profile_id", "course_id", "cohort_id", name="uq_eligibility_composite"),
    )

    # --- period_template ---
    op.create_table(
        "period_template",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("weekday", sa.Integer, nullable=False),
        sa.Column("period_index", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("shift", sa.String, nullable=True),
    )

    # --- constraint_rule ---
    op.create_table(
        "constraint_rule",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_type", sa.String, nullable=False),
        sa.Column("scope", sa.String, nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("threshold", sa.Numeric, nullable=True),
        sa.Column("unit", sa.String, nullable=True),
        sa.Column("polarity", sa.String, nullable=True),
        sa.Column("weight", sa.Numeric, nullable=True),
        sa.Column("source", sa.String, nullable=True),
        sa.Column("raw_input_text", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="confirmed"),
        sa.CheckConstraint("source IN ('structured', 'nl')", name="ck_constraint_rule_source"),
    )

    # --- elective_section ---
    op.create_table(
        "elective_section",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("term_id", UUID(as_uuid=True), sa.ForeignKey("academic_term.id"), nullable=True),
        sa.Column("capacity", sa.Integer, nullable=True),
    )

    # --- enrollment_record ---
    op.create_table(
        "enrollment_record",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("student_profile_id", UUID(as_uuid=True), sa.ForeignKey("student_profile.id"), nullable=False),
        sa.Column("elective_section_id", UUID(as_uuid=True), sa.ForeignKey("elective_section.id"), nullable=False),
    )

    # --- exception_calendar ---
    op.create_table(
        "exception_calendar",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
    )

    # --- timetable_version ---
    op.create_table(
        "timetable_version",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("term_id", UUID(as_uuid=True), sa.ForeignKey("academic_term.id"), nullable=True),
        sa.Column("state", sa.String, nullable=False, server_default="draft"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=True),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
    )

    # --- assignment (+ denormalized tenant_id §32 #18) ---
    op.create_table(
        "assignment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("timetable_version_id", UUID(as_uuid=True), sa.ForeignKey("timetable_version.id"), nullable=False),
        sa.Column("staff_profile_id", UUID(as_uuid=True), sa.ForeignKey("staff_profile.id"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("cohort_id", UUID(as_uuid=True), sa.ForeignKey("cohort.id"), nullable=False),
        sa.Column("room_id", UUID(as_uuid=True), sa.ForeignKey("room.id"), nullable=False),
        sa.Column("slot_start", sa.Integer, nullable=False),
        sa.Column("slot_span", sa.Integer, nullable=False, server_default="1"),
    )

    # --- exam_timetable_version ---
    op.create_table(
        "exam_timetable_version",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("term_id", UUID(as_uuid=True), sa.ForeignKey("academic_term.id"), nullable=True),
        sa.Column("state", sa.String, nullable=False, server_default="draft"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=True),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
    )

    # --- exam_session ---
    op.create_table(
        "exam_session",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("exam_timetable_version_id", UUID(as_uuid=True), sa.ForeignKey("exam_timetable_version.id"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("cohort_id", UUID(as_uuid=True), sa.ForeignKey("cohort.id"), nullable=False),
        sa.Column("room_id", UUID(as_uuid=True), sa.ForeignKey("room.id"), nullable=False),
        sa.Column("invigilator_staff_profile_id", UUID(as_uuid=True), sa.ForeignKey("staff_profile.id"), nullable=True),
        sa.Column("slot_start", sa.Integer, nullable=False),
    )

    # --- substitution_log ---
    op.create_table(
        "substitution_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("original_staff_profile_id", UUID(as_uuid=True), sa.ForeignKey("staff_profile.id"), nullable=False),
        sa.Column("substitute_staff_profile_id", UUID(as_uuid=True), sa.ForeignKey("staff_profile.id"), nullable=False),
        sa.Column("assignment_id", UUID(as_uuid=True), sa.ForeignKey("assignment.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
    )

    # --- audit_log ---
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("actor_identity_id", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("entity_type", sa.String, nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("before", JSONB, nullable=True),
        sa.Column("after", JSONB, nullable=True),
        sa.Column("at", sa.TIMESTAMP, nullable=False),
    )

    # --- notification ---
    op.create_table(
        "notification",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("identity_id", UUID(as_uuid=True), sa.ForeignKey("identity.id"), nullable=False),
        sa.Column("channel", sa.String, nullable=False),
        sa.Column("subject", sa.String, nullable=True),
        sa.Column("body", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="queued"),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP, nullable=True),
    )

    # ========== RLS POLICIES (invariant #3) ==========
    # Enable RLS and create tenant_isolation policy for every tenant-scoped table.
    # staff_availability_block and exam_session don't have tenant_id directly;
    # staff_availability_block is scoped via staff_profile FK, exam_session via
    # exam_timetable_version FK. We skip RLS on those two and on identity.
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid);"
        )
        # Allow the table owner (migration user) to bypass RLS
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    for table in reversed(TENANT_SCOPED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    tables = [
        "notification", "audit_log", "substitution_log",
        "exam_session", "exam_timetable_version",
        "assignment", "timetable_version",
        "exception_calendar", "enrollment_record", "elective_section",
        "constraint_rule", "period_template", "eligibility",
        "student_profile", "staff_availability_block", "staff_profile",
        "room", "batch", "cohort", "course", "department", "campus",
        "academic_term", "tenant", "identity",
    ]
    for table in tables:
        op.drop_table(table)
