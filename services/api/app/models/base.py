"""SQLAlchemy declarative base and tenant mixin."""

import uuid

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Mixin adding tenant_id to every tenant-scoped table."""
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


def new_uuid():
    return uuid.uuid4()
