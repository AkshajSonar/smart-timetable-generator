"""
Demo dataset seeder — scale calibrated so CP-SAT solves in <30 s.

3 departments x 3 cohort-years = 9 cohorts
3 courses per cohort (core, lab+batches, block-size-3 studio)
8 faculty per dept, 2 eligible per course-cohort pair
12 classrooms + 6 labs
5 days x 8 periods = 40 slots
3 cross-department electives
4 exam sessions (2-room split + 2 single)
Estimated vars: ~90 elig x 40 slots x ~12 rooms ~ 43 000 (tractable)
"""
import asyncio
import os
import sys
import datetime
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text, select
from app.models.identity import Identity
from app.models.tenant import Tenant
from app.models.academic_term import AcademicTerm
from app.models.department import Department
from app.models.course import Course
from app.models.room import Room
from app.models.staff_profile import StaffProfile
from app.models.cohort import Cohort
from app.models.batch import Batch
from app.models.student_profile import StudentProfile
from app.models.elective_section import ElectiveSection
from app.models.enrollment_record import EnrollmentRecord
from app.models.batch_membership import BatchMembership
from app.models.eligibility import Eligibility
from app.models.stubs import ExceptionCalendar
from app.models.period_template import PeriodTemplate
from app.models.exam_timetable_version import ExamTimetableVersion
from app.models.exam_session import ExamSession


async def seed_demo_dataset():
    async with AsyncSessionLocal() as session:
        # ── Identities ────────────────────────────────────────────────────────────
        identities_data = [
            {"email": "admin@timetable.local",     "auth_provider_ref": "institution_admin",    "full_name": "Alice Admin",     "platform_role": None},
            {"email": "head@timetable.local",       "auth_provider_ref": "department_head",      "full_name": "David DeptHead",  "platform_role": None},
            {"email": "reviewer@timetable.local",   "auth_provider_ref": "reviewer",             "full_name": "Rachel Reviewer", "platform_role": None},
            {"email": "faculty@timetable.local",    "auth_provider_ref": "faculty",              "full_name": "Frank Faculty",   "platform_role": None},
            {"email": "superadmin@timetable.local", "auth_provider_ref": "platform_super_admin", "full_name": "Sam Super",       "platform_role": "platform_super_admin"},
            {"email": "student@timetable.local",    "auth_provider_ref": "student",              "full_name": "Sally Student",   "platform_role": None},
        ]

        admin_id = None
        for data in identities_data:
            result = await session.execute(select(Identity).where(Identity.email == data["email"]))
            identity = result.scalar_one_or_none()
            if not identity:
                identity = Identity(
                    email=data["email"],
                    auth_provider_ref=data["auth_provider_ref"],
                    full_name=data["full_name"],
                    platform_role=data["platform_role"]
                )
                session.add(identity)
                await session.flush()
            if data["auth_provider_ref"] == "institution_admin":
                admin_id = identity.id

        # ── Tenant ────────────────────────────────────────────────────────────────
        t_id = uuid.uuid4()
        tenant = Tenant(id=t_id, tenant_id=t_id, name="Demo University", institution_type="university", isolation_mode="row")
        session.add(tenant)
        await session.flush()

        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant.id)}
        )

        term = AcademicTerm(
            tenant_id=tenant.id, name="Fall 2026",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2026, 12, 15)
        )
        session.add(term)
        await session.flush()

        # ── Period Templates (Mon-Fri, 8 periods/day = 40 slots) ─────────────────
        pts = []
        for d in range(1, 6):
            for p in range(8):
                pts.append(PeriodTemplate(
                    tenant_id=tenant.id, weekday=d, period_index=p,
                    start_time=datetime.time(8 + p, 0),
                    end_time=datetime.time(9 + p, 0),
                    shift="Day"
                ))
        session.add_all(pts)

        # ── Rooms: 12 classrooms + 6 labs ────────────────────────────────────────
        # 6 labs exercises H10 (shared-lab-capacity) with 9 cohorts x 2 batches
        rooms = []
        classroom_rooms = []
        lab_rooms = []
        for i in range(12):
            r = Room(tenant_id=tenant.id, name=f"Classroom {i+1}", type="classroom", capacity=60, accessible=True)
            rooms.append(r); classroom_rooms.append(r)
        for i in range(6):
            r = Room(tenant_id=tenant.id, name=f"Lab {i+1}", type="lab", capacity=30, accessible=True)
            rooms.append(r); lab_rooms.append(r)
        session.add_all(rooms)
        await session.flush()

        # ── 3 Departments, 3 years each, 8 faculty each ───────────────────────────
        dept_names = ["Computer Science", "Mathematics", "Physics"]
        departments = []
        all_faculty = []
        all_cohorts = []
        student_counter = 1

        for dept_name in dept_names:
            dept = Department(tenant_id=tenant.id, name=dept_name)
            session.add(dept)
            await session.flush()
            departments.append(dept)

            dept_faculty = []
            for i in range(8):
                f = StaffProfile(
                    tenant_id=tenant.id, identity_id=admin_id,
                    employment_type="full_time", workload_cap_week=20, workload_cap_day=6
                )
                session.add(f)
                dept_faculty.append(f)
                all_faculty.append(f)
            await session.flush()

            for y in range(1, 4):
                cohort = Cohort(tenant_id=tenant.id, name=f"{dept_name} Year {y}", type="fixed")
                session.add(cohort)
                await session.flush()
                all_cohorts.append(cohort)

                pfx = dept_name[:3].upper()
                c_core = Course(
                    tenant_id=tenant.id, department_id=dept.id,
                    name=f"{pfx}{y}01 Core", type="classroom",
                    credit_value=3, hours_per_week=3, block_size=1
                )
                c_lab = Course(
                    tenant_id=tenant.id, department_id=dept.id,
                    name=f"{pfx}{y}02 Lab", type="lab",
                    credit_value=1, hours_per_week=2, block_size=1
                )
                c_block = Course(
                    tenant_id=tenant.id, department_id=dept.id,
                    name=f"{pfx}{y}03 Studio", type="classroom",
                    credit_value=3, hours_per_week=3, block_size=3
                )
                session.add_all([c_core, c_lab, c_block])
                await session.flush()

                b1 = Batch(tenant_id=tenant.id, cohort_id=cohort.id, course_id=c_lab.id, label="Batch A")
                b2 = Batch(tenant_id=tenant.id, cohort_id=cohort.id, course_id=c_lab.id, label="Batch B")
                session.add_all([b1, b2])
                await session.flush()

                cohort_students = []
                for _ in range(10):
                    s = StudentProfile(
                        tenant_id=tenant.id,
                        external_student_code=f"S{student_counter:04d}",
                        cohort_id=cohort.id
                    )
                    student_counter += 1
                    session.add(s)
                    cohort_students.append(s)
                await session.flush()

                for idx, s in enumerate(cohort_students):
                    b_id = b1.id if idx % 2 == 0 else b2.id
                    session.add(BatchMembership(
                        tenant_id=tenant.id, student_profile_id=s.id, batch_id=b_id
                    ))

                # 2 eligible faculty per course assignment (redundancy fix; prevents 1:1 bottleneck)
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[0].id, course_id=c_core.id,  cohort_id=cohort.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[4].id, course_id=c_core.id,  cohort_id=cohort.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[1].id, course_id=c_lab.id,   cohort_id=cohort.id, batch_id=b1.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[5].id, course_id=c_lab.id,   cohort_id=cohort.id, batch_id=b1.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[2].id, course_id=c_lab.id,   cohort_id=cohort.id, batch_id=b2.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[6].id, course_id=c_lab.id,   cohort_id=cohort.id, batch_id=b2.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[3].id, course_id=c_block.id, cohort_id=cohort.id))
                session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=dept_faculty[7].id, course_id=c_block.id, cohort_id=cohort.id))

        # ── Cross-department electives (3 sections) ───────────────────────────────
        elective_names = ["Ethics in Tech", "Global History", "Basic Economics"]
        electives = []
        elective_sections = []

        for i, name in enumerate(elective_names):
            c_elec = Course(
                tenant_id=tenant.id, department_id=departments[0].id,
                name=name, type="classroom",
                credit_value=2, hours_per_week=2, block_size=1
            )
            session.add(c_elec)
            electives.append(c_elec)
        await session.flush()

        for i, c_elec in enumerate(electives):
            e_sec = ElectiveSection(
                tenant_id=tenant.id, course_id=c_elec.id, term_id=term.id, capacity=80
            )
            session.add(e_sec)
            elective_sections.append(e_sec)
            # 3 eligible faculty per elective (from across depts)
            session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=all_faculty[i * 3    ].id, course_id=c_elec.id, cohort_id=all_cohorts[0].id))
            session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=all_faculty[i * 3 + 1].id, course_id=c_elec.id, cohort_id=all_cohorts[0].id))
            session.add(Eligibility(tenant_id=tenant.id, staff_profile_id=all_faculty[i * 3 + 2].id, course_id=c_elec.id, cohort_id=all_cohorts[0].id))
        await session.flush()

        # Enroll students from ALL 3 departments round-robin (cross-dept requirement)
        all_students_res = await session.execute(
            select(StudentProfile).where(StudentProfile.tenant_id == tenant.id)
        )
        all_students = all_students_res.scalars().all()
        for idx, st in enumerate(all_students):
            sec = elective_sections[idx % 3]
            session.add(EnrollmentRecord(
                tenant_id=tenant.id, student_profile_id=st.id, elective_section_id=sec.id
            ))

        # ── Exam exception days ───────────────────────────────────────────────────
        exam_start = datetime.date(2026, 12, 10)
        for i in range(5):
            session.add(ExceptionCalendar(
                tenant_id=tenant.id,
                date=exam_start + datetime.timedelta(days=i),
                type="exam_period",
                description=f"Fall 2026 Final Exams Day {i + 1}"
            ))

        # ── Exam timetable version + 4 sessions ──────────────────────────────────
        exam_tv = ExamTimetableVersion(
            tenant_id=tenant.id, term_id=term.id, state="draft", version_no=1
        )
        session.add(exam_tv)
        await session.flush()

        # 2-room split for elective 0 (multi-room-split exercise, Phase 4)
        session.add(ExamSession(
            tenant_id=tenant.id, exam_timetable_version_id=exam_tv.id,
            course_id=electives[0].id, cohort_id=all_cohorts[0].id,
            room_id=lab_rooms[0].id,
            invigilator_staff_profile_id=all_faculty[0].id,
            slot_start=0
        ))
        session.add(ExamSession(
            tenant_id=tenant.id, exam_timetable_version_id=exam_tv.id,
            course_id=electives[0].id, cohort_id=all_cohorts[0].id,
            room_id=lab_rooms[1].id,
            invigilator_staff_profile_id=all_faculty[1].id,
            slot_start=0
        ))
        # Single-room sessions for electives 1 and 2
        session.add(ExamSession(
            tenant_id=tenant.id, exam_timetable_version_id=exam_tv.id,
            course_id=electives[1].id, cohort_id=all_cohorts[0].id,
            room_id=classroom_rooms[0].id,
            invigilator_staff_profile_id=all_faculty[2].id,
            slot_start=1
        ))
        session.add(ExamSession(
            tenant_id=tenant.id, exam_timetable_version_id=exam_tv.id,
            course_id=electives[2].id, cohort_id=all_cohorts[0].id,
            room_id=classroom_rooms[1].id,
            invigilator_staff_profile_id=all_faculty[3].id,
            slot_start=2
        ))

        await session.commit()
        print(
            f"Seed complete.\n"
            f"  Tenant ID        : {tenant.id}\n"
            f"  Term ID          : {term.id}\n"
            f"  Depts            : {len(departments)}\n"
            f"  Cohorts          : {len(all_cohorts)}\n"
            f"  Faculty          : {len(all_faculty)}\n"
            f"  Rooms            : {len(rooms)} (12 classroom + 6 lab)\n"
            f"  Students         : {student_counter - 1}\n"
            f"  Elective sections: {len(elective_sections)}\n"
            f"  Exam sessions    : 4 (2-room split + 2 single)\n"
        )


if __name__ == "__main__":
    asyncio.run(seed_demo_dataset())
