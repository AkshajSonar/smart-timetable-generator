"""Tenant model — §17."""

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TenantMixin, new_uuid


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    institution_type = Column(String, nullable=False)  # school|college|university|coaching
    timezone = Column(String, nullable=False, server_default="UTC")
    enabled_modules = Column(JSONB, nullable=False, server_default='{}')
    isolation_mode = Column(String, nullable=False, server_default="row")  # row|schema
