"""Course schemas."""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class CourseCreate(BaseModel):
    department_id: UUID
    name: str
    type: str  # core|elective|lab
    credit_value: Optional[float] = None
    hours_per_week: int
    block_size: int = 1
    required_equipment_tags: list[str] = []


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    credit_value: Optional[float] = None
    hours_per_week: Optional[int] = None
    block_size: Optional[int] = None
    required_equipment_tags: Optional[list[str]] = None


class CourseRead(BaseModel):
    id: UUID
    tenant_id: UUID
    department_id: UUID
    name: str
    type: str
    credit_value: Optional[float] = None
    hours_per_week: int
    block_size: int
    required_equipment_tags: list[str]

    model_config = {"from_attributes": True}
