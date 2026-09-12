"""EnrollmentRecord model — §28."""

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class EnrollmentRecord(Base, TenantMixin):
    __tablename__ = "enrollment_record"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    student_profile_id = Column(UUID(as_uuid=True), ForeignKey("student_profile.id"), nullable=False)
    elective_section_id = Column(UUID(as_uuid=True), ForeignKey("elective_section.id"), nullable=False)
