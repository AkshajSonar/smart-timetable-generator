"""StaffProfile schemas."""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class StaffProfileCreate(BaseModel):
    identity_id: UUID
    employment_type: str  # full_time|part_time|visiting
    workload_cap_week: int
    workload_cap_day: int
    roles: list[str] = []


class StaffProfileUpdate(BaseModel):
    employment_type: Optional[str] = None
    workload_cap_week: Optional[int] = None
    workload_cap_day: Optional[int] = None
    roles: Optional[list[str]] = None


class StaffProfileRead(BaseModel):
    id: UUID
    tenant_id: UUID
    identity_id: UUID
    employment_type: str
    workload_cap_week: int
    workload_cap_day: int
    roles: list[str]

    model_config = {"from_attributes": True}
