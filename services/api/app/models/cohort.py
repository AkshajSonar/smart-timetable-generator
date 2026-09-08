"""Cohort model — §17."""

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class Cohort(Base, TenantMixin):
    __tablename__ = "cohort"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, server_default="fixed")  # fixed|elective_derived
