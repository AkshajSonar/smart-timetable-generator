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


class SubstitutionLog(Base, TenantMixin):
    """§17 substitution_log + two-step flow extensions.

    status lifecycle: suggested → confirmed | cancelled.
    substitute_staff_profile_id is NULL at suggest time; set on confirm.
    Persisting a row at suggest time gives the confirm endpoint a stable ID
    and makes concurrent confirms detectable (second confirm sees status='confirmed' → 409).
    """
    __tablename__ = "substitution_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    original_staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    # Nullable: set at confirm time only
    substitute_staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=True)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignment.id"), nullable=False)
    date = Column(Date, nullable=False)
    # §31 free choice: status enum guards against double-confirm races
    status = Column(String, nullable=False, server_default="suggested")  # suggested|confirmed|cancelled


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
