"""StaffAvailabilityBlock model — §32 #17. Dedicated table for H4."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, new_uuid


class StaffAvailabilityBlock(Base):
    __tablename__ = "staff_availability_block"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    staff_profile_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=False)
    weekday = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    period_index = Column(Integer, nullable=False)
    block_type = Column(String, nullable=False)  # unavailable|admin|reserved
