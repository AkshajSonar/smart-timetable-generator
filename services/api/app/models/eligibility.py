"""Eligibility model — §17 + §32 #18 (denormalized tenant_id)."""

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class Eligibility(Base, TenantMixin):
    __tablename__ = "eligibility"

    # Composite natural key, but we add a surrogate PK for simpler ORM handling
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.id"), nullable=False)
    cohort_id = Column(UUID(as_uuid=True), ForeignKey("cohort.id"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batch.id"), nullable=True)
