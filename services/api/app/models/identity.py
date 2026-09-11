"""Identity model — tenant-independent, §17."""

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, new_uuid


class Identity(Base):
    __tablename__ = "identity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=True)
    auth_provider_ref = Column(String, nullable=True)
    platform_role = Column(String, nullable=True)  # 'super_admin' or null
