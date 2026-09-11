from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.assignment import Assignment
from app.models.published_schedule import PublishedSchedule
from app.models.staff_profile import StaffProfile
from app.models.identity import Identity
from app.models.course import Course
from app.models.cohort import Cohort
from app.models.room import Room
from app.models.batch import Batch
from app.schemas.timetable import PublishedScheduleResponse

async def get_dual_routed_schedules(db: AsyncSession, version_id: UUID, state: str, type_filter: str = 'class') -> list[PublishedScheduleResponse]:
    """
    Returns schedules dual-routed either from PublishedSchedule (if published/archived)
    or from Assignment (if draft/under_review), mapping them to the identical Pydantic response shape.
    """
    if state in ("published", "archived"):
        q = select(PublishedSchedule).where(
            PublishedSchedule.timetable_version_id == version_id,
            PublishedSchedule.type == type_filter
        )
        res = await db.execute(q)
        rows = res.scalars().all()
        return [PublishedScheduleResponse.model_validate(r) for r in rows]
    else:
        # Query raw assignments or exam sessions
        if type_filter == 'class':
            q = select(Assignment).where(Assignment.timetable_version_id == version_id)
        else:
            from app.models.exam_session import ExamSession
            q = select(ExamSession).where(ExamSession.exam_timetable_version_id == version_id)
            
        res = await db.execute(q)
        assignments = res.scalars().all()

        staff_ids = set()
        course_ids = set()
        cohort_ids = set()
        room_ids = set()
        batch_ids = set()
        
        for a in assignments:
            if type_filter == 'exam':
                if a.invigilator_staff_profile_id: staff_ids.add(a.invigilator_staff_profile_id)
                if a.course_id: course_ids.add(a.course_id)
                if a.cohort_id: cohort_ids.add(a.cohort_id)
                if a.room_id: room_ids.add(a.room_id)
            else:
                if a.staff_profile_id: staff_ids.add(a.staff_profile_id)
                if a.course_id: course_ids.add(a.course_id)
                if a.cohort_id: cohort_ids.add(a.cohort_id)
                if a.room_id: room_ids.add(a.room_id)
                if getattr(a, 'batch_id', None): batch_ids.add(a.batch_id)

        staff_names = {}
        if staff_ids:
            # Post Phase 7: Identity full_name is the source of truth
            staff_q = await db.execute(
                select(StaffProfile.id, Identity.full_name)
                .join(Identity, StaffProfile.identity_id == Identity.id)
                .where(StaffProfile.id.in_(staff_ids))
            )
            staff_names = {row.id: row.full_name for row in staff_q.all()}
            
        course_names = {}
        if course_ids:
            course_q = await db.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids)))
            course_names = {row.id: row.name for row in course_q.all()}
            
        cohort_names = {}
        if cohort_ids:
            cohort_q = await db.execute(select(Cohort.id, Cohort.name).where(Cohort.id.in_(cohort_ids)))
            cohort_names = {row.id: row.name for row in cohort_q.all()}
            
        room_names = {}
        if room_ids:
            room_q = await db.execute(select(Room.id, Room.name).where(Room.id.in_(room_ids)))
            room_names = {row.id: row.name for row in room_q.all()}
            
        batch_names = {}
        if batch_ids:
            batch_q = await db.execute(select(Batch.id, Batch.label).where(Batch.id.in_(batch_ids)))
            batch_names = {row.id: row.label for row in batch_q.all()}

        schedules = []
        for a in assignments:
            if type_filter == 'exam':
                schedules.append(
                    PublishedScheduleResponse(
                        id=a.id,
                        type=type_filter,
                        staff_profile_id=a.invigilator_staff_profile_id,
                        cohort_id=a.cohort_id,
                        course_id=a.course_id,
                        room_id=a.room_id,
                        batch_id=None,
                        staff_name=staff_names.get(a.invigilator_staff_profile_id) if a.invigilator_staff_profile_id else None,
                        cohort_name=cohort_names.get(a.cohort_id),
                        course_name=course_names.get(a.course_id),
                        room_name=room_names.get(a.room_id),
                        batch_name=None,
                        slot_index=a.slot_start,
                        slot_span=1,
                        is_locked=False
                    )
                )
            else:
                schedules.append(
                    PublishedScheduleResponse(
                        id=a.id,
                        type=type_filter,
                        staff_profile_id=a.staff_profile_id,
                        cohort_id=a.cohort_id,
                        course_id=a.course_id,
                        room_id=a.room_id,
                        batch_id=a.batch_id,
                        staff_name=staff_names.get(a.staff_profile_id) if a.staff_profile_id else None,
                        cohort_name=cohort_names.get(a.cohort_id),
                        course_name=course_names.get(a.course_id),
                        room_name=room_names.get(a.room_id),
                        batch_name=batch_names.get(a.batch_id) if getattr(a, 'batch_id', None) else None,
                        slot_index=a.slot_start,
                        slot_span=a.slot_span,
                        is_locked=a.is_locked
                    )
                )
        return schedules

