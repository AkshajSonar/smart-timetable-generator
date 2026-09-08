"""Timetable schemas."""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AssignmentRead(BaseModel):
    id: UUID
    staff_profile_id: UUID
    course_id: UUID
    cohort_id: UUID
    room_id: UUID
    slot_start: int
    slot_span: int
    batch_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


class TimetableRead(BaseModel):
    id: UUID
    tenant_id: UUID
    state: str
    version_no: int
    assignments: list[AssignmentRead] = []


class GenerateRequest(BaseModel):
    term_id: Optional[UUID] = None


class GenerateResponse(BaseModel):
    timetable_version_id: UUID
    status: str
    violations: list[dict] = []
