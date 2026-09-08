"""StaffAvailabilityBlock model — §32 #17 / §32 #19.

Dedicated table for H4 (faculty blocked slots).
tenant_id added in migration 002 (§32 #19) for uniform RLS.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, new_uuid


class StaffAvailabilityBlock(Base):
    __tablename__ = "staff_availability_block"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    # tenant_id is denormalized from staff_profile.tenant_id for uniform RLS (§32 #19)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    weekday = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    period_index = Column(Integer, nullable=False)
    block_type = Column(String, nullable=False)  # unavailable|admin|reserved
