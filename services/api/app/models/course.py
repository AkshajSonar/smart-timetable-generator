"""Course model — §17 + §32 #15 (required_equipment_tags)."""

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TenantMixin, new_uuid


class Course(Base, TenantMixin):
    __tablename__ = "course"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # core|elective|lab
    credit_value = Column(Numeric, nullable=True)
    hours_per_week = Column(Integer, nullable=False)
    block_size = Column(Integer, nullable=False, server_default="1")
    # §32 #15: exists from Phase 1, populated from Phase 2+
    required_equipment_tags = Column(JSONB, nullable=False, server_default='[]')
