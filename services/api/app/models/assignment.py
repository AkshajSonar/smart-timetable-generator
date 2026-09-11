"""Assignment model — §17 DDL + §32 #18 (denormalized tenant_id).

is_locked / locked_by: FR-9.2 cell locking.
  is_locked=True marks this assignment as manually edited; the solver
  must treat it as a pinned slot (via AddHint or fixed variable) on
  any subsequent regeneration, never overwriting it silently.
  locked_by: identity_id of the editor, for FR-9.4 audit trail.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class Assignment(Base, TenantMixin):
    __tablename__ = "assignment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    timetable_version_id = Column(UUID(as_uuid=True), ForeignKey("timetable_version.id"), nullable=False)
    staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.id"), nullable=False)
    cohort_id = Column(UUID(as_uuid=True), ForeignKey("cohort.id"), nullable=False)
    room_id = Column(UUID(as_uuid=True), ForeignKey("room.id"), nullable=False)
    slot_start = Column(Integer, nullable=False)
    slot_span = Column(Integer, nullable=False, server_default="1")
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batch.id"), nullable=True)
    # FR-9.2: cell locking — regeneration must not overwrite is_locked=True rows
    is_locked = Column(Boolean, nullable=False, server_default="false")
    locked_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
