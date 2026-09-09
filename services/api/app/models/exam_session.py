from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class ExamSession(Base, TenantMixin):
    __tablename__ = "exam_session"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    exam_timetable_version_id = Column(UUID(as_uuid=True), ForeignKey("exam_timetable_version.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.id"), nullable=False)
    cohort_id = Column(UUID(as_uuid=True), ForeignKey("cohort.id"), nullable=False)
    room_id = Column(UUID(as_uuid=True), ForeignKey("room.id"), nullable=False)
    invigilator_staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=True)
    slot_start = Column(Integer, nullable=False)
