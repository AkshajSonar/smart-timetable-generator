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


class StaffInviteRequest(BaseModel):
    email: str
    employment_type: str
    workload_cap_week: int
    workload_cap_day: int
    roles: list[str] = []


class StaffInviteResponse(BaseModel):
    staff_profile: 'StaffProfileRead'
    status: str



class StaffProfileRead(BaseModel):
    id: UUID
    tenant_id: UUID
    identity_id: UUID
    employment_type: str
    workload_cap_week: int
    workload_cap_day: int
    roles: list[str]
    full_name: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}
