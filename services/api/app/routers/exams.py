"""Exams router — generate + GET under /api/v1/tenants/{tenantId}/exams."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

# Import solver
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "solver"))

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/exams", tags=["exams"])


@router.post("/generate", response_model=ExamGenerateResponse)
async def generate_exam_timetable(
    tenantId: UUID,
    body: ExamGenerateRequest,
    db: AsyncSession = Depends(set_tenant_context),
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
