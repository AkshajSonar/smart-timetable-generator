"""Assignment model — §17 DDL + §32 #18 (denormalized tenant_id)."""

from sqlalchemy import Column, ForeignKey, Integer
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
