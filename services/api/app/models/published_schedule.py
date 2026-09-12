from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TenantMixin, new_uuid

class PublishedSchedule(Base, TenantMixin):
    __tablename__ = "published_schedule"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    
    # Can link to either timetable_version or exam_timetable_version
    timetable_version_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    exam_timetable_version_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    
    type = Column(String, nullable=False) # 'class' or 'exam'
    
    # Foreign keys for original entities
    staff_profile_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    cohort_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    course_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    room_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    batch_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    
    # Denormalized string values for fast reading (CQRS read model)
    staff_name = Column(String, nullable=True)
    cohort_name = Column(String, nullable=True)
    course_name = Column(String, nullable=True)
    room_name = Column(String, nullable=True)
    batch_name = Column(String, nullable=True)
    
    slot_start = Column(Integer, nullable=False)
    slot_span = Column(Integer, nullable=False, default=1)
