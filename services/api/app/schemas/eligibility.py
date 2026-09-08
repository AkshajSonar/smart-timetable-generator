"""Eligibility schemas."""

from uuid import UUID
from pydantic import BaseModel


class EligibilityCreate(BaseModel):
    staff_profile_id: UUID
    course_id: UUID
    cohort_id: UUID


class EligibilityRead(BaseModel):
    id: UUID
    tenant_id: UUID
    staff_profile_id: UUID
    course_id: UUID
    cohort_id: UUID

    model_config = {"from_attributes": True}
