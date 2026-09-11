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
    is_locked: bool = False

    model_config = {"from_attributes": True}

class PublishedScheduleResponse(BaseModel):
    id: UUID
    type: str
    staff_profile_id: Optional[UUID] = None
    cohort_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    staff_name: Optional[str] = None
    cohort_name: Optional[str] = None
    course_name: Optional[str] = None
    room_name: Optional[str] = None
    batch_name: Optional[str] = None
    slot_index: int
    slot_span: int
    is_locked: bool = False

    model_config = {"from_attributes": True}

class TimetableRead(BaseModel):
    id: UUID
    tenant_id: UUID
    state: str
    version_no: int
    schedules: list[PublishedScheduleResponse] = []


class GenerateRequest(BaseModel):
    term_id: Optional[UUID] = None
    prior_version_id: Optional[UUID] = None  # To load is_locked assignments from


class GenerateResponse(BaseModel):
    timetable_version_id: UUID
    status: str
    violations: list[dict] = []


class WhatIfResponse(BaseModel):
    status: str
    violations: list[dict] = []
    assignments: list[PublishedScheduleResponse] = []


class EditAssignmentRequest(BaseModel):
    """FR-9.1 manual edit request.

    version_no: the version_no the client last read from the timetable_version row.
    A mismatch with the DB's current version_no returns CONFLICT (invariant #7).

    assignment_id: the specific assignment row to change.

    Only the fields being changed need to be provided; omitted fields are unchanged.
    At least one of staff_profile_id, room_id, slot_start must be non-None.
    """
    version_no: int
    assignment_id: UUID
    staff_profile_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    slot_start: Optional[int] = None


class EditAssignmentResponse(BaseModel):
    """Returned on a successful edit. version_no reflects the post-increment value."""
    assignment_id: UUID
    new_version_no: int
    violations: list[dict] = []  # always empty on success (any violation rejects the write)

class StateTransitionRequest(BaseModel):
    version_no: int
