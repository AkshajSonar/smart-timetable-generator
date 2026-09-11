"""Report schemas."""

from uuid import UUID
from pydantic import BaseModel


class LoadVerificationItem(BaseModel):
    id: UUID
    name: str
    required_hours: int
    scheduled_hours: int
    difference: int


class LoadVerificationReport(BaseModel):
    faculty_load: list[LoadVerificationItem]
    cohort_load: list[LoadVerificationItem]


class RoomUtilizationItem(BaseModel):
    room_id: UUID
    room_name: str
    capacity: int
    available_hours: int
    scheduled_hours: int
    utilization_percentage: float


class RoomUtilizationReport(BaseModel):
    rooms: list[RoomUtilizationItem]

