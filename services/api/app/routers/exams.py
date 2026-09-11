"""Exams router — generate + GET under /api/v1/tenants/{tenantId}/exams."""

from uuid import UUID, uuid4

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_jwt
from app.core.tenant_context import set_tenant_context
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.eligibility import Eligibility
from app.models.period_template import PeriodTemplate
from app.models.room import Room
from app.models.staff_availability_block import StaffAvailabilityBlock
from app.models.staff_profile import StaffProfile
from app.models.exam_timetable_version import ExamTimetableVersion
from app.models.exam_session import ExamSession
from app.models.stubs import ExceptionCalendar
from app.models.student_profile import StudentProfile
from app.models.enrollment_record import EnrollmentRecord
from app.models.elective_section import ElectiveSection
from app.schemas.exam import ExamGenerateRequest, ExamGenerateResponse, ExamSessionRead
from app.schemas.timetable import PublishedScheduleResponse
from app.schemas.timetable import StateTransitionRequest

# Import solver
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "solver"))

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/exams", tags=["exams"])


from app.rbac.dependencies import require_role

@router.post("/generate", response_model=ExamGenerateResponse)
async def generate_exam_timetable(
    tenantId: UUID,
    body: ExamGenerateRequest,
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"]))
):
    """Phase 4: Generate exam timetable.
    
    Pre-processing:
    - Sort enrolled students by external_student_code ascending.
    - Fill rooms in fixed order (largest capacity first) until full.
    - Spills into next exam_session row.
    - Exams apply to type='core' and type='elective' only. type='lab' is excluded.
    """
    from solver.data_types import (
        SolverInput, FacultyData, CourseData, CohortData,
        RoomData, PeriodSlot, BlockedSlot, ExamSessionData, StudentExamData
    )
    from solver.model import solve

    # 1. Load Data
    cohort_result = await db.execute(select(Cohort))
    cohorts = list(cohort_result.scalars().all())

    elig_result = await db.execute(select(Eligibility))
    eligibilities = list(elig_result.scalars().all())

    # Exclude lab courses
    course_ids = list(set(e.course_id for e in eligibilities))
    courses_result = await db.execute(select(Course).where(Course.id.in_(course_ids), Course.type.in_(["core", "elective"])))
    courses = {c.id: c for c in courses_result.scalars().all()}
    
    # We only care about eligibilities for courses we kept
    eligibilities = [e for e in eligibilities if e.course_id in courses]

    faculty_ids = list(set(e.staff_profile_id for e in eligibilities))
    faculty_result = await db.execute(select(StaffProfile).where(StaffProfile.id.in_(faculty_ids)))
    faculty = {f.id: f for f in faculty_result.scalars().all()}

    rooms_result = await db.execute(select(Room))
    rooms = list(rooms_result.scalars().all())

    # 1.5 Load Exam Periods from ExceptionCalendar
    exc_result = await db.execute(select(ExceptionCalendar).where(ExceptionCalendar.type == "exam_period"))
    exam_dates = list(exc_result.scalars().all())
    exam_weekdays = {d.date.weekday() for d in exam_dates} if exam_dates else set(range(7)) # Default to all if none seeded

    pt_result = await db.execute(select(PeriodTemplate).order_by(PeriodTemplate.weekday, PeriodTemplate.period_index))
    period_templates = [pt for pt in pt_result.scalars().all() if pt.weekday in exam_weekdays]

    blocked_result = await db.execute(
        select(StaffAvailabilityBlock).where(
            StaffAvailabilityBlock.staff_profile_id.in_(faculty_ids)
        )
    )
    blocked_slots = list(blocked_result.scalars().all())

    stud_result = await db.execute(select(StudentProfile))
    db_students = list(stud_result.scalars().all())

    enr_result = await db.execute(select(EnrollmentRecord))
    db_enrollments = list(enr_result.scalars().all())

    es_result = await db.execute(select(ElectiveSection))
    db_elective_sections = {es.id: es for es in es_result.scalars().all()}

    # Map student -> elective courses
    student_electives: dict[UUID, list[UUID]] = {}
    for enr in db_enrollments:
        es = db_elective_sections.get(enr.elective_section_id)
        if es:
            student_electives.setdefault(enr.student_profile_id, []).append(es.course_id)

    # 2. Determine student enrollments for exams
    # course_id -> cohort_id -> list of student profiles
    course_cohort_students: dict[tuple[UUID, UUID], list[StudentProfile]] = {}

    for s in db_students:
        for e in eligibilities:
            if e.cohort_id != s.cohort_id:
                continue
            
            course = courses.get(e.course_id)
            if not course:
                continue
                
            is_enrolled = False
            if course.type == "elective":
                if course.id in student_electives.get(s.id, []):
                    is_enrolled = True
            else:
                is_enrolled = True
                
            if is_enrolled:
                key = (course.id, s.cohort_id)
                course_cohort_students.setdefault(key, []).append(s)

    # 3. Pre-process rooms
    sorted_rooms = sorted(rooms, key=lambda r: r.capacity, reverse=True)
    if not sorted_rooms:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "No rooms available for exams"}})

    solver_exam_sessions = []
    student_exam_map: dict[UUID, list[str]] = {s.id: [] for s in db_students}

    for (course_id, cohort_id), students in course_cohort_students.items():
        # Sort students deterministically
        students.sort(key=lambda s: s.external_student_code or str(s.id))
        
        remaining_students = students.copy()
        
        while remaining_students:
            # Find a room to put them in
            room = None
            # Just take the first room that can fit them, or the largest room if none can fit them fully
            for r in sorted_rooms:
                room = r
                break # Just use largest room first and spill
                
            if not room:
                break
                
            chunk = remaining_students[:room.capacity]
            remaining_students = remaining_students[room.capacity:]
            
            session_id = str(uuid4())
            solver_exam_sessions.append(ExamSessionData(
                id=session_id,
                course_id=str(course_id),
                cohort_id=str(cohort_id),
                room_id=str(room.id),
                num_students=len(chunk)
            ))
            
            for st in chunk:
                student_exam_map[st.id].append(session_id)

    # 4. Build Solver Input
    solver_faculty = [FacultyData(id=str(f.id), workload_cap_week=f.workload_cap_week, workload_cap_day=f.workload_cap_day) for f in faculty.values()]
    solver_courses = [CourseData(id=str(c.id), type=c.type, hours_per_week=c.hours_per_week, block_size=c.block_size, required_equipment_tags=[]) for c in courses.values()]
    solver_cohorts = [CohortData(id=str(c.id), name=c.name) for c in cohorts]
    solver_rooms = [RoomData(id=str(r.id), type=r.type, capacity=r.capacity, equipment_tags=[]) for r in rooms]

    slots_by_day: dict[int, list[int]] = {}
    slot_index = 0
    slot_map: dict[tuple[int, int], int] = {}
    for pt in period_templates:
        slot_map[(pt.weekday, pt.period_index)] = slot_index
        slots_by_day.setdefault(pt.weekday, []).append(slot_index)
        slot_index += 1

    period_slots = [PeriodSlot(slot_index=slot_map[(pt.weekday, pt.period_index)], weekday=pt.weekday, period_index=pt.period_index) for pt in period_templates]
    
    solver_blocked = []
    for b in blocked_slots:
        key = (b.weekday, b.period_index)
        if key in slot_map:
            solver_blocked.append(BlockedSlot(faculty_id=str(b.staff_profile_id), slot_index=slot_map[key]))

    solver_students_exams = [StudentExamData(id=str(s_id), exam_session_ids=e_ids) for s_id, e_ids in student_exam_map.items()]

    # Fetch confirmed rules
    from app.models.constraint_rule import ConstraintRule
    from solver.data_types import RuleData
    rules_query = await db.execute(
        select(ConstraintRule).where(
            ConstraintRule.tenant_id == tenantId,
            ConstraintRule.status == "confirmed"
        )
    )
    solver_rules = []
    for r in rules_query.scalars().all():
        solver_rules.append(RuleData(
            rule_type=r.rule_type,
            scope=r.scope,
            target_id=str(r.target_id) if r.target_id else None,
            threshold=float(r.threshold) if r.threshold is not None else None,
            unit=r.unit,
            polarity=r.polarity,
            weight=float(r.weight) if r.weight is not None else None
        ))

    solver_input = SolverInput(
        faculty=solver_faculty,
        courses=solver_courses,
        cohorts=solver_cohorts,
        rooms=solver_rooms,
        eligibility=[], # Not used for exams
        period_slots=period_slots,
        blocked_slots=solver_blocked,
        slots_per_day=slots_by_day,
        num_slots=slot_index,
        is_exam=True,
        exam_sessions=solver_exam_sessions,
        students_exams=solver_students_exams,
        rules=solver_rules,
    )

    # 5. Solve
    results = solve(solver_input)
    if results is None:
        raise HTTPException(status_code=409, detail={"error": {"code": "INFEASIBLE_CONFIGURATION", "message": "Solver could not find a feasible exam timetable."}})

    # 6. Save results
    tv = ExamTimetableVersion(
        tenant_id=tenantId,
        term_id=UUID(body.term_id),
        state="draft",
        version_no=1,
    )
    db.add(tv)
    await db.flush()

    sessions_out = []
    for r in results:
        session_row = ExamSession(
            id=UUID(r.id),
            tenant_id=tenantId,
            exam_timetable_version_id=tv.id,
            course_id=UUID([s for s in solver_exam_sessions if s.id == r.id][0].course_id),
            cohort_id=UUID([s for s in solver_exam_sessions if s.id == r.id][0].cohort_id),
            room_id=UUID(r.room_id),
            invigilator_staff_profile_id=UUID(r.invigilator_staff_profile_id) if r.invigilator_staff_profile_id else None,
            slot_start=r.slot_index,
        )
        db.add(session_row)
        sessions_out.append(ExamSessionRead(
            id=session_row.id,
            exam_timetable_version_id=session_row.exam_timetable_version_id,
            course_id=session_row.course_id,
            cohort_id=session_row.cohort_id,
            room_id=session_row.room_id,
            invigilator_staff_profile_id=session_row.invigilator_staff_profile_id,
            slot_start=session_row.slot_start,
        ))

    await db.commit()
    return ExamGenerateResponse(success=True, version_id=tv.id, sessions=sessions_out)

@router.get("/sessions", response_model=list[PublishedScheduleResponse])
async def get_exam_sessions(
    tenantId: UUID,
    versionId: UUID = Query(..., description="The exam timetable version ID to fetch sessions for"),
    db: AsyncSession = Depends(set_tenant_context),
    _role: set[str] = Depends(require_role(["institution_admin", "department_head", "reviewer", "faculty", "student"]))
):
    """
    Get all exam sessions for the given version.
    """
    from app.models.exam_timetable_version import ExamTimetableVersion
    ev_result = await db.execute(select(ExamTimetableVersion).where(ExamTimetableVersion.id == versionId))
    ev = ev_result.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Exam timetable version not found"}})
        
    if not ("institution_admin" in _role or "department_head" in _role or "reviewer" in _role):
        if ev.state != "published":
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Only admins can view draft exam schedules"}})
            
    from app.services.schedule_mapper import get_dual_routed_schedules
    return await get_dual_routed_schedules(db, versionId, ev.state, 'exam')

@router.post("/timetables/{versionId}/approve")
async def approve_exam_timetable(
    tenantId: UUID,
    versionId: UUID,
    body: StateTransitionRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["reviewer"])),
):
    from app.models.exam_timetable_version import ExamTimetableVersion
    from app.models.stubs import AuditLog

    result = await db.execute(select(ExamTimetableVersion).where(ExamTimetableVersion.id == versionId))
    tv = result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Exam timetable version not found"}})
    
    if tv.version_no != body.version_no:
        raise HTTPException(status_code=409, detail={"error": {"code": "CONFLICT", "message": f"Stale version_no. DB has {tv.version_no}"}})

    before_state = {"state": tv.state, "approved_by": str(tv.approved_by) if tv.approved_by else None}

    tv.approved_by = identity_id
    if tv.state == "draft":
        tv.state = "under_review"
    tv.version_no += 1

    after_state = {"state": tv.state, "approved_by": str(tv.approved_by)}

    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="approve",
        entity_type="exam_timetable_version",
        entity_id=versionId,
        before=before_state,
        after=after_state,
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    await db.commit()
    return {"status": "success", "new_version_no": tv.version_no}


@router.post("/timetables/{versionId}/publish")
async def publish_exam_timetable(
    tenantId: UUID,
    versionId: UUID,
    body: StateTransitionRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["institution_admin"])),
):
    from app.models.exam_timetable_version import ExamTimetableVersion
    from app.models.stubs import AuditLog
    from app.models.exam_session import ExamSession
    from app.models.published_schedule import PublishedSchedule
    from app.models.staff_profile import StaffProfile
    from app.models.identity import Identity
    from app.models.course import Course
    from app.models.cohort import Cohort
    from app.models.room import Room

    result = await db.execute(select(ExamTimetableVersion).where(ExamTimetableVersion.id == versionId))
    tv = result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Exam timetable version not found"}})
    
    if tv.version_no != body.version_no:
        raise HTTPException(status_code=409, detail={"error": {"code": "CONFLICT", "message": f"Stale version_no. DB has {tv.version_no}"}})

    if tv.approved_by is None:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "Must be approved before publish"}})

    before_state = {"state": tv.state}
    tv.state = "published"
    tv.version_no += 1
    after_state = {"state": tv.state}

    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="publish",
        entity_type="exam_timetable_version",
        entity_id=versionId,
        before=before_state,
        after=after_state,
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    
    # Denormalize
    await db.execute(
        PublishedSchedule.__table__.delete().where(PublishedSchedule.exam_timetable_version_id == versionId)
    )

    assignments_query = await db.execute(
        select(ExamSession).where(ExamSession.exam_timetable_version_id == versionId)
    )
    assignments = assignments_query.scalars().all()

    for assign in assignments:
        staff_name = None
        if assign.invigilator_staff_profile_id:
            staff_q = await db.execute(
                select(Identity.full_name).join(StaffProfile, Identity.id == StaffProfile.identity_id)
                .where(StaffProfile.id == assign.invigilator_staff_profile_id)
            )
            staff_name = staff_q.scalar_one_or_none()

        course_q = await db.execute(select(Course.name).where(Course.id == assign.course_id))
        course_name = course_q.scalar_one_or_none()

        cohort_q = await db.execute(select(Cohort.name).where(Cohort.id == assign.cohort_id))
        cohort_name = cohort_q.scalar_one_or_none()

        room_q = await db.execute(select(Room.name).where(Room.id == assign.room_id))
        room_name = room_q.scalar_one_or_none()

        published_row = PublishedSchedule(
            tenant_id=tenantId,
            exam_timetable_version_id=versionId,
            type='exam',
            staff_profile_id=assign.invigilator_staff_profile_id,
            cohort_id=assign.cohort_id,
            course_id=assign.course_id,
            room_id=assign.room_id,
            staff_name=staff_name,
            cohort_name=cohort_name,
            course_name=course_name,
            room_name=room_name,
            slot_index=assign.slot_start,
            slot_span=1
        )
        db.add(published_row)

    await db.commit()
    return {"status": "success", "new_version_no": tv.version_no}
