from pydantic import BaseModel
from uuid import UUID

class EnrollmentImportRow(BaseModel):
    student_code: str
    course_name: str
    term_id: UUID

class EnrollmentImportRequest(BaseModel):
    rows: list[EnrollmentImportRow]

class ImportResult(BaseModel):
    success_count: int
    errors: list[dict[str, str]]  # e.g. [{"row": "S001 - AI Elective", "error": "Student not found"}]
