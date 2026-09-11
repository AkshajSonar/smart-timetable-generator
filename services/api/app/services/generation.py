from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.cohort import Cohort
from app.models.batch import Batch
from app.models.eligibility import Eligibility
from app.models.course import Course
from app.models.staff_profile import StaffProfile
from app.models.room import Room
from app.models.period_template import PeriodTemplate
from app.models.staff_availability_block import StaffAvailabilityBlock
from app.models.student_profile import StudentProfile
from app.models.batch_membership import BatchMembership
from app.models.enrollment_record import EnrollmentRecord
from app.models.elective_section import ElectiveSection
from app.models.constraint_rule import ConstraintRule
from app.models.timetable_version import TimetableVersion
from app.models.assignment import Assignment
from app.models.identity import Identity

from solver.data_types import (
    SolverInput, FacultyData, CourseData, CohortData,
    BatchData, RoomData, EligibilityData, PeriodSlot, BlockedSlot,
    StudentData, StudentCourseData, RuleData, AssignmentResult
)

async def build_solver_input(
    db: AsyncSession, 
    tenantId: UUID, 
    term_id: UUID | None = None, 
    prior_version_id: UUID | None = None
) -> tuple[SolverInput, dict, dict, dict, dict, dict]:
    # Returns (solver_input, courses, cohorts, batches, rooms, faculty_names)
    
    # Load all master data for the tenant
    cohort_result = await db.execute(select(Cohort))
    cohorts = list(cohort_result.scalars().all())
    if not cohorts:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "No cohorts found for tenant"}})

    # Batches
    batch_result = await db.execute(select(Batch))
    batches = list(batch_result.scalars().all())

    # Eligibility for all cohorts/batches
    elig_result = await db.execute(select(Eligibility))
    eligibilities = list(elig_result.scalars().all())
    if not eligibilities:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "No eligibility records found"}})

    # Courses involved
    course_ids = list(set(e.course_id for e in eligibilities))
    courses_result = await db.execute(select(Course).where(Course.id.in_(course_ids)))
    courses = {c.id: c for c in courses_result.scalars().all()}

    # Faculty involved
    faculty_ids = list(set(e.staff_profile_id for e in eligibilities))
    faculty_result = await db.execute(select(StaffProfile).where(StaffProfile.id.in_(faculty_ids)))
    faculty = {f.id: f for f in faculty_result.scalars().all()}
    
    # Fetch faculty names from Identity
    identity_ids = list(set(f.identity_id for f in faculty.values() if f.identity_id))
    id_result = await db.execute(select(Identity).where(Identity.id.in_(identity_ids)))
    identities = {i.id: i for i in id_result.scalars().all()}
    faculty_names = {fid: identities[f.identity_id].full_name for fid, f in faculty.items() if f.identity_id and f.identity_id in identities}

    # Rooms
    rooms_result = await db.execute(select(Room))
    rooms = {r.id: r for r in rooms_result.scalars().all()}

    # Period templates
    pt_result = await db.execute(select(PeriodTemplate).order_by(PeriodTemplate.weekday, PeriodTemplate.period_index))
    period_templates = list(pt_result.scalars().all())

    # Blocked slots
    blocked_result = await db.execute(
        select(StaffAvailabilityBlock).where(
            StaffAvailabilityBlock.staff_profile_id.in_(faculty_ids)
        )
    )
    blocked_slots = list(blocked_result.scalars().all())

    # Build solver input
    solver_faculty = []
    for fid, f in faculty.items():
        solver_faculty.append(FacultyData(
            id=str(fid),
            workload_cap_week=f.workload_cap_week,
            workload_cap_day=f.workload_cap_day,
        ))

    solver_courses = []
    for cid, c in courses.items():
        solver_courses.append(CourseData(
            id=str(cid),
            type=c.type,
            hours_per_week=c.hours_per_week,
            block_size=c.block_size,
            required_equipment_tags=c.required_equipment_tags or [],
        ))

    solver_cohorts = [CohortData(id=str(c.id), name=c.name) for c in cohorts]
    
    solver_batches = [BatchData(
        id=str(b.id),
        label=b.label,
        cohort_id=str(b.cohort_id),
        course_id=str(b.course_id),
    ) for b in batches]

    solver_rooms = []
    for rid, r in rooms.items():
        solver_rooms.append(RoomData(
            id=str(rid),
            type=r.type,
            capacity=r.capacity,
            equipment_tags=r.equipment_tags or [],
        ))

    solver_elig = []
    for e in eligibilities:
        solver_elig.append(EligibilityData(
            faculty_id=str(e.staff_profile_id),
            course_id=str(e.course_id),
            cohort_id=str(e.batch_id) if e.batch_id else str(e.cohort_id),
        ))

    # Build period slots
    slots_by_day: dict[int, list[int]] = {}
    slot_index = 0
    slot_map: dict[tuple[int, int], int] = {}
    for pt in period_templates:
        slot_map[(pt.weekday, pt.period_index)] = slot_index
        slots_by_day.setdefault(pt.weekday, []).append(slot_index)
        slot_index += 1

    period_slots = [
        PeriodSlot(slot_index=slot_map[(pt.weekday, pt.period_index)], weekday=pt.weekday, period_index=pt.period_index)
        for pt in period_templates
    ]

    solver_blocked = []
    for b in blocked_slots:
        key = (b.weekday, b.period_index)
        if key in slot_map:
            solver_blocked.append(BlockedSlot(
                faculty_id=str(b.staff_profile_id),
                slot_index=slot_map[key],
            ))

    room_type_counts = {}
    for r in rooms.values():
        room_type_counts[r.type] = room_type_counts.get(r.type, 0) + 1

    # Load Student Data
    stud_result = await db.execute(select(StudentProfile))
    db_students = list(stud_result.scalars().all())

    bm_result = await db.execute(select(BatchMembership))
    db_batch_memberships = list(bm_result.scalars().all())

    enr_result = await db.execute(select(EnrollmentRecord))
    db_enrollments = list(enr_result.scalars().all())

    es_result = await db.execute(select(ElectiveSection))
    db_elective_sections = {es.id: es for es in es_result.scalars().all()}

    student_batches: dict[UUID, list[UUID]] = {}
    for bm in db_batch_memberships:
        student_batches.setdefault(bm.student_profile_id, []).append(bm.batch_id)

    student_electives: dict[UUID, list[UUID]] = {}
    for enr in db_enrollments:
        es = db_elective_sections.get(enr.elective_section_id)
        if es:
            student_electives.setdefault(enr.student_profile_id, []).append(es.course_id)

    solver_students = []
    for s in db_students:
        s_courses = []
        for e in eligibilities:
            if e.cohort_id != s.cohort_id:
                continue

            course = courses.get(e.course_id)
            if not course:
                continue

            batches_for_course = [b for b in batches if b.course_id == e.course_id and b.cohort_id == s.cohort_id]
            
            if batches_for_course:
                student_bms = student_batches.get(s.id, [])
                for b in batches_for_course:
                    if b.id in student_bms:
                        s_courses.append(StudentCourseData(course_id=str(course.id), cohort_id=str(s.cohort_id), batch_id=str(b.id)))
                        break
            else:
                if course.type == "elective":
                    if course.id in student_electives.get(s.id, []):
                        s_courses.append(StudentCourseData(course_id=str(course.id), cohort_id=str(s.cohort_id), batch_id=None))
                else:
                    s_courses.append(StudentCourseData(course_id=str(course.id), cohort_id=str(s.cohort_id), batch_id=None))

        solver_students.append(StudentData(id=str(s.id), courses=s_courses))

    # Load locked assignments
    locked_results = []
    if not prior_version_id and term_id:
        latest_version = await db.execute(
            select(TimetableVersion.id).where(
                TimetableVersion.tenant_id == tenantId,
                TimetableVersion.term_id == term_id
            ).order_by(TimetableVersion.version_no.desc()).limit(1)
        )
        prior_version_id = latest_version.scalar_one_or_none()
        
    if prior_version_id:
        locked_assign_result = await db.execute(
            select(Assignment).where(
                Assignment.timetable_version_id == prior_version_id,
                Assignment.is_locked == True
            )
        )
        for la in locked_assign_result.scalars().all():
            locked_results.append(AssignmentResult(
                faculty_id=str(la.staff_profile_id),
                course_id=str(la.course_id),
                cohort_id=str(la.cohort_id),
                room_id=str(la.room_id),
                slot_index=la.slot_start,
                slot_span=la.slot_span,
                batch_id=str(la.batch_id) if la.batch_id else None
            ))

    # Rules
    rules_query = await db.execute(select(ConstraintRule).where(ConstraintRule.status == "confirmed"))
    solver_rules = []
    for r in rules_query.scalars().all():
        solver_rules.append(RuleData(
            rule_type=r.rule_type,
            scope=r.scope,
            target_id=str(r.target_id) if r.target_id else None,
            threshold=float(r.threshold) if r.threshold is not None else None,
            unit=r.unit,
            polarity=r.polarity,
            weight=float(r.weight) if r.weight is not None else None,
        ))
    
    solver_input = SolverInput(
        faculty=solver_faculty,
        courses=solver_courses,
        cohorts=solver_cohorts,
        batches=solver_batches,
        rooms=solver_rooms,
        eligibility=solver_elig,
        period_slots=period_slots,
        blocked_slots=solver_blocked,
        slots_per_day=slots_by_day,
        num_slots=slot_index,
        room_type_counts=room_type_counts,
        students=solver_students,
        locked_assignments=locked_results,
        rules=solver_rules,
    )

    cohort_dict = {c.id: c for c in cohorts}
    batch_dict = {b.id: b for b in batches}
    
    return solver_input, courses, cohort_dict, batch_dict, rooms, faculty_names

