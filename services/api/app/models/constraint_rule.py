"""ConstraintRule model — §17."""

from sqlalchemy import Column, Numeric, String, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, new_uuid


class ConstraintRule(Base, TenantMixin):
    __tablename__ = "constraint_rule"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rule_type = Column(String, nullable=False)  # enum §30
    scope = Column(String, nullable=False)  # tenant|department|faculty|course|cohort
    target_id = Column(UUID(as_uuid=True), nullable=True)
    threshold = Column(Numeric, nullable=True)
    unit = Column(String, nullable=True)
    polarity = Column(String, nullable=True)  # max|min|forbid|require
    weight = Column(Numeric, nullable=True)
    source = Column(String, nullable=True)  # structured|nl
    raw_input_text = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="confirmed")

    __table_args__ = (
        CheckConstraint(
            status.in_(["pending_confirmation", "confirmed"]),
            name="constraint_rule_status_check"
        ),
    )
