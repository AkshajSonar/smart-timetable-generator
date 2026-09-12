"""Batch model — §17 + §32 #18 (denormalized tenant_id)."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class Batch(Base, TenantMixin):
    __tablename__ = "batch"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    cohort_id = Column(UUID(as_uuid=True), ForeignKey("cohort.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.id"), nullable=False)
    label = Column(String, nullable=False)
