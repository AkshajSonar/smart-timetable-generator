"""Stub models for §28 tables — populated in later phases."""

from sqlalchemy import Column, Date, ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TenantMixin, new_uuid




class ExceptionCalendar(Base, TenantMixin):
    __tablename__ = "exception_calendar"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    date = Column(Date, nullable=False)
    type = Column(String, nullable=False)  # holiday|exam_period|event|half_day
    description = Column(String, nullable=True)


class ExamTimetableVersion(Base, TenantMixin):
    __tablename__ = "exam_timetable_version"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_term.id"), nullable=True)
    state = Column(String, nullable=False, server_default="draft")
    created_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    version_no = Column(Integer, nullable=False, server_default="1")


class ExamSession(Base):
    __tablename__ = "exam_session"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    exam_timetable_version_id = Column(UUID(as_uuid=True), ForeignKey("exam_timetable_version.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.id"), nullable=False)
    cohort_id = Column(UUID(as_uuid=True), ForeignKey("cohort.id"), nullable=False)
    room_id = Column(UUID(as_uuid=True), ForeignKey("room.id"), nullable=False)
    invigilator_staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=True)
    slot_start = Column(Integer, nullable=False)


class SubstitutionLog(Base, TenantMixin):
    __tablename__ = "substitution_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    original_staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    substitute_staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignment.id"), nullable=False)
    date = Column(Date, nullable=False)


class AuditLog(Base, TenantMixin):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    actor_identity_id = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    at = Column(DateTime, nullable=False)


class Notification(Base, TenantMixin):
    __tablename__ = "notification"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=False)
    channel = Column(String, nullable=False)  # email|push|sms
    subject = Column(String, nullable=True)
    body = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="queued")  # queued|sent|failed
    created_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
