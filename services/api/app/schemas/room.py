"""Room schemas."""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class RoomCreate(BaseModel):
    campus_id: Optional[UUID] = None
    name: str
    type: str  # classroom|lab|seminar_hall|auditorium
    capacity: int
    equipment_tags: list[str] = []
    accessible: bool = False


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    capacity: Optional[int] = None
    equipment_tags: Optional[list[str]] = None
    accessible: Optional[bool] = None


class RoomRead(BaseModel):
    id: UUID
    tenant_id: UUID
    campus_id: Optional[UUID] = None
    name: str
    type: str
    capacity: int
    equipment_tags: list[str]
    accessible: bool

    model_config = {"from_attributes": True}
