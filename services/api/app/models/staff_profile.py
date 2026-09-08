"""StaffProfile model — §17."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TenantMixin, new_uuid


class StaffProfile(Base, TenantMixin):
    __tablename__ = "staff_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("identity.id"), nullable=False)
    employment_type = Column(String, nullable=False)  # full_time|part_time|visiting
    workload_cap_week = Column(Integer, nullable=False)
    workload_cap_day = Column(Integer, nullable=False)
    roles = Column(JSONB, nullable=False, server_default='[]')
