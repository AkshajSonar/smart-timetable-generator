"""Department schemas."""

from uuid import UUID
from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str


class DepartmentUpdate(BaseModel):
    name: str | None = None


class DepartmentRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str

    model_config = {"from_attributes": True}
