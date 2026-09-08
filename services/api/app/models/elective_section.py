"""ElectiveSection model — §28."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class ElectiveSection(Base, TenantMixin):
    __tablename__ = "elective_section"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.id"), nullable=False)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_term.id"), nullable=False)
    capacity = Column(Integer, nullable=False)
