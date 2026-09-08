from uuid import UUID
from pydantic import BaseModel, ConfigDict

class StudentRead(BaseModel):
    id: UUID
    identity_id: UUID | None
    external_student_code: str
    cohort_id: UUID
    
    model_config = ConfigDict(from_attributes=True)
