from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class ExamTimetableVersion(Base, TenantMixin):
    __tablename__ = "exam_timetable_version"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_term.id"), nullable=True)
    state = Column(String, nullable=False, server_default="draft")
    created_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    version_no = Column(Integer, nullable=False, server_default="1")
