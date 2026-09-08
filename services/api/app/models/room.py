"""Room model — §17."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TenantMixin, new_uuid


class Room(Base, TenantMixin):
    __tablename__ = "room"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campus_id = Column(UUID(as_uuid=True), ForeignKey("campus.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # classroom|lab|seminar_hall|auditorium
    capacity = Column(Integer, nullable=False)
    equipment_tags = Column(JSONB, nullable=False, server_default='[]')
    accessible = Column(Boolean, nullable=False, server_default="false")
