"""TimetableVersion model — §17."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class TimetableVersion(Base, TenantMixin):
    __tablename__ = "timetable_version"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_term.id"), nullable=True)
    state = Column(String, nullable=False, server_default="draft")  # draft|under_review|published|archived
    created_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    version_no = Column(Integer, nullable=False, server_default="1")
