"""PeriodTemplate schemas."""

import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class PeriodTemplateCreate(BaseModel):
    weekday: int  # 0=Monday
    period_index: int
    start_time: datetime.time
    end_time: datetime.time
    shift: Optional[str] = None


class PeriodTemplateRead(BaseModel):
    id: UUID
    tenant_id: UUID
    weekday: int
    period_index: int
    start_time: datetime.time
    end_time: datetime.time
    shift: Optional[str] = None

    model_config = {"from_attributes": True}
