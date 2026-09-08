"""PeriodTemplate model — §17."""

from sqlalchemy import Column, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class PeriodTemplate(Base, TenantMixin):
    __tablename__ = "period_template"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    weekday = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    period_index = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    shift = Column(String, nullable=True)
