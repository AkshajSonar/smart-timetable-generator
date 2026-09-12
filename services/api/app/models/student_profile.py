"""StudentProfile model — §28."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class StudentProfile(Base, TenantMixin):
    __tablename__ = "student_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=True)
    external_student_code = Column(String, nullable=False)
    cohort_id = Column(UUID(as_uuid=True), ForeignKey("cohort.id"), nullable=False)
