from pydantic import BaseModel
from uuid import UUID

class EnrollmentImportRow(BaseModel):
    student_external_id: str
    elective_section_external_id: str

class EnrollmentImportRequest(BaseModel):
    rows: list[EnrollmentImportRow]

class ImportResult(BaseModel):
    success_count: int
    errors: list[dict[str, str]]  # e.g. [{"row": "S001 - ES001", "error": "Student not found"}]
