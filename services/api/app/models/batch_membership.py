"""BatchMembership model — §32 #20."""

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class BatchMembership(Base, TenantMixin):
    __tablename__ = "batch_membership"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    student_profile_id = Column(UUID(as_uuid=True), ForeignKey("student_profile.id"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batch.id"), nullable=False)
