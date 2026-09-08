"""Cohort schemas."""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class CohortCreate(BaseModel):
    name: str
    type: str = "fixed"  # fixed|elective_derived


class CohortUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None


class CohortRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    type: str

    model_config = {"from_attributes": True}
