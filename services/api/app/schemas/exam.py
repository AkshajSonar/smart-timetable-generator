from uuid import UUID
from pydantic import BaseModel
from typing import Optional

class ExamGenerateRequest(BaseModel):
    term_id: str

class ExamSessionRead(BaseModel):
    id: UUID
    exam_timetable_version_id: UUID
    course_id: UUID
    cohort_id: UUID
    room_id: UUID
    invigilator_staff_profile_id: Optional[UUID] = None
    slot_start: int

class ExamGenerateResponse(BaseModel):
    success: bool
    version_id: Optional[UUID] = None
    error: Optional[str] = None
    sessions: list[ExamSessionRead] = []
