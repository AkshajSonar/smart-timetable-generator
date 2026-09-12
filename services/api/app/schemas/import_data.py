from pydantic import BaseModel

class EnrollmentImportRow(BaseModel):
    student_external_id: str
    elective_section_external_id: str

class EnrollmentImportRequest(BaseModel):
    rows: list[EnrollmentImportRow]

class FacultyImportRow(BaseModel):
    external_id: str | None = None
    full_name: str
    email: str
    workload_cap_week: int = 20
    workload_cap_day: int = 6
    employment_type: str = "full_time"

class FacultyImportRequest(BaseModel):
    rows: list[FacultyImportRow]

class CourseImportRow(BaseModel):
    code: str | None = None
    name: str
    department: str | None = None
    type: str = "core"
    hours_per_week: int = 3
    block_size: int = 1

class CourseImportRequest(BaseModel):
    rows: list[CourseImportRow]

class RoomImportRow(BaseModel):
    name: str
    building: str | None = None
    room_type: str = "lecture_hall"
    capacity: int = 60
    equipment_tags: list[str] = []

class RoomImportRequest(BaseModel):
    rows: list[RoomImportRow]

class ImportResult(BaseModel):
    success_count: int
    errors: list[dict[str, str]]
