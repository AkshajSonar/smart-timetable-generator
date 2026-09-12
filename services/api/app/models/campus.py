"""Campus model — §28."""

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class Campus(Base, TenantMixin):
    __tablename__ = "campus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=True)  # overrides tenant.timezone if set
