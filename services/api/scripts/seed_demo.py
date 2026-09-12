import asyncio
import os
import sys

# Add the parent directory to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import AsyncSessionLocal
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

from sqlalchemy import select, text

async def seed_demo_dataset():
    async with AsyncSessionLocal() as session:
        # Create or Get an Identity
        result = await session.execute(select(Identity).where(Identity.email == "admin@demo.com"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = Identity(email="admin@demo.com", auth_provider_ref="demo_admin")
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

        # Create a Tenant
        tenant = Tenant(name="Demo University", institution_type="university", isolation_mode="row")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        # In PostgreSQL, we can use set_config to set the tenant_id for RLS and default triggers if any
        # But wait, our RLS requires the session variable
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant.id)}
        )

        # Create AcademicTerm
        import datetime
        term = AcademicTerm(tenant_id=tenant.id, name="Fall 2026", start_date=datetime.date(2026, 9, 1), end_date=datetime.date(2026, 12, 15))
        session.add(term)
        await session.commit()
        await session.refresh(term)

        # Create Department
        dept = Department(tenant_id=tenant.id, name="Computer Science")
        session.add(dept)
        await session.commit()
        await session.refresh(dept)

        # Create Rooms
        classroom = Room(tenant_id=tenant.id, name="Room 101", type="classroom", capacity=40, accessible=True)
        lab = Room(tenant_id=tenant.id, name="CS Lab A", type="lab", capacity=20, accessible=True)
        session.add_all([classroom, lab])
        
        # Create Courses
        core_course = Course(tenant_id=tenant.id, department_id=dept.id, name="CS101", type="core", credit_value=3, hours_per_week=2, block_size=1)
        lab_course = Course(tenant_id=tenant.id, department_id=dept.id, name="CS101 Lab", type="lab", credit_value=1, hours_per_week=2, block_size=1)
        elective_course = Course(tenant_id=tenant.id, department_id=dept.id, name="AI Elective", type="elective", credit_value=3, hours_per_week=2, block_size=1)
        session.add_all([core_course, lab_course, elective_course])
        
        # Create Staff
        teacher1 = StaffProfile(tenant_id=tenant.id, identity_id=admin.id, employment_type="full_time", workload_cap_week=20, workload_cap_day=6)
        teacher2 = StaffProfile(tenant_id=tenant.id, identity_id=admin.id, employment_type="full_time", workload_cap_week=20, workload_cap_day=6)
        session.add_all([teacher1, teacher2])

        # Create Cohort and Batches
        cohort = Cohort(tenant_id=tenant.id, name="Year 1 CS", type="fixed")
        session.add(cohort)
        await session.commit()
        await session.refresh(cohort)
        
        batch1 = Batch(tenant_id=tenant.id, cohort_id=cohort.id, course_id=lab_course.id, label="Batch A")
        batch2 = Batch(tenant_id=tenant.id, cohort_id=cohort.id, course_id=lab_course.id, label="Batch B")
        session.add_all([batch1, batch2])
        await session.commit()
        await session.refresh(batch1)
        await session.refresh(batch2)

        # Create Students
        students = []
        for i in range(1, 11): # 10 students
            students.append(StudentProfile(tenant_id=tenant.id, external_student_code=f"S{i:03d}", cohort_id=cohort.id))
        session.add_all(students)
        await session.commit()
        for s in students:
            await session.refresh(s)
            
        # Batch Membership (Odd to A, Even to B)
        memberships = []
        for i, s in enumerate(students):
            # i=0 (S001) -> Batch A, i=1 (S002) -> Batch B
            b_id = batch1.id if i % 2 == 0 else batch2.id
            memberships.append(BatchMembership(tenant_id=tenant.id, student_profile_id=s.id, batch_id=b_id))
        session.add_all(memberships)
        
        # Elective Section
        elective_section = ElectiveSection(tenant_id=tenant.id, course_id=elective_course.id, term_id=term.id, capacity=5)
        session.add(elective_section)
        await session.commit()
        await session.refresh(elective_section)

        # Enroll some students in Elective (first 4 students)
        enrollments = []
        for s in students[:4]:
            enrollments.append(EnrollmentRecord(tenant_id=tenant.id, student_profile_id=s.id, elective_section_id=elective_section.id))
        session.add_all(enrollments)

        # Eligibility
        elig_core = Eligibility(tenant_id=tenant.id, staff_profile_id=teacher1.id, course_id=core_course.id, cohort_id=cohort.id)
        elig_lab1 = Eligibility(tenant_id=tenant.id, staff_profile_id=teacher2.id, course_id=lab_course.id, cohort_id=cohort.id, batch_id=batch1.id)
        elig_lab2 = Eligibility(tenant_id=tenant.id, staff_profile_id=teacher2.id, course_id=lab_course.id, cohort_id=cohort.id, batch_id=batch2.id)
        elig_elec = Eligibility(tenant_id=tenant.id, staff_profile_id=teacher1.id, course_id=elective_course.id, cohort_id=cohort.id)  # Wait, elective uses a derived cohort?

        session.add_all([elig_core, elig_lab1, elig_lab2])
        await session.commit()

        print(f"Seed complete. Tenant ID: {tenant.id}")

if __name__ == "__main__":
    asyncio.run(seed_demo_dataset())
