"""AcademicTerm model — §32 #16."""

from sqlalchemy import Column, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class AcademicTerm(Base, TenantMixin):
    __tablename__ = "academic_term"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
