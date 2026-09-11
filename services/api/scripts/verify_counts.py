"""Verify §22.4 dataset requirements numerically against the seeded database."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.database import SuperuserAsyncSessionLocal
from sqlalchemy import text


async def run_counts():
    async with SuperuserAsyncSessionLocal() as session:
        # Auto-detect the tenant
        # Find the real seeded tenant (the one with actual departments, not test stubs)
        res = await session.execute(text("""
            SELECT t.id, t.name FROM tenant t
            JOIN department d ON d.tenant_id = t.id
            GROUP BY t.id, t.name
            ORDER BY COUNT(d.id) DESC
            LIMIT 1
        """))
        row = res.fetchone()
        if not row:
            print("No tenant with departments found — run seed_demo.py first")
            return
        tenant_id = row[0]
        print(f"=== §22.4 Verification for Tenant '{row[1]}' ({tenant_id}) ===\n")

        # --- 1. Elective sections ---
        res = await session.execute(
            text("SELECT COUNT(*) FROM elective_section WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        es_count = res.scalar()
        print(f"Elective sections: {es_count}")

        # --- 2. Enrollment records ---
        res = await session.execute(
            text("SELECT COUNT(*) FROM enrollment_record WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        er_count = res.scalar()
        print(f"Enrollment records: {er_count}")

        # --- 3. Cross-department elective enrollment ---
        # cohort table has no department_id; use the name prefix (e.g. 'CS' from 'CS-Y1')
        res = await session.execute(text("""
            SELECT es.id, COUNT(DISTINCT split_part(co.name, '-', 1)) AS dept_count
            FROM enrollment_record er
            JOIN student_profile sp ON er.student_profile_id = sp.id
            JOIN cohort co ON sp.cohort_id = co.id
            JOIN elective_section es ON er.elective_section_id = es.id
            WHERE er.tenant_id = :tid
            GROUP BY es.id
            HAVING COUNT(DISTINCT split_part(co.name, '-', 1)) > 1
        """), {"tid": tenant_id})
        cross_dept_rows = res.fetchall()
        print(f"Elective sections with cross-department enrollment: {len(cross_dept_rows)}")
        for r in cross_dept_rows:
            print(f"  → Section {r[0]}: students from {r[1]} different departments")

        # --- 4. Room counts by type ---
        res = await session.execute(text("""
            SELECT type, COUNT(*)
            FROM room
            WHERE tenant_id = :tid
            GROUP BY type ORDER BY type
        """), {"tid": tenant_id})
        print(f"\nRooms by type:")
        for r in res.fetchall():
            print(f"  {r[0]}: {r[1]} rooms")

        # --- 5. Courses with block_size > 1 ---
        res = await session.execute(
            text("SELECT COUNT(*) FROM course WHERE tenant_id = :tid AND block_size > 1"),
            {"tid": tenant_id}
        )
        block_count = res.scalar()
        print(f"\nCourses with block_size > 1: {block_count}")

        res = await session.execute(
            text("SELECT name, block_size, hours_per_week FROM course WHERE tenant_id = :tid AND block_size > 1"),
            {"tid": tenant_id}
        )
        for r in res.fetchall():
            print(f"  → '{r[0]}': block_size={r[1]}, hours_per_week={r[2]}")

        # --- 6. Exam entities ---
        res = await session.execute(
            text("SELECT COUNT(*) FROM exam_timetable_version WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        print(f"\nExam timetable versions: {res.scalar()}")

        res = await session.execute(
            text("SELECT COUNT(*) FROM exam_session WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        exam_count = res.scalar()
        print(f"Exam sessions: {exam_count}")

        # Multi-room split check
        res = await session.execute(text("""
            SELECT es.course_id, c.name, COUNT(DISTINCT es.room_id) AS room_count
            FROM exam_session es
            JOIN course c ON es.course_id = c.id
            WHERE es.tenant_id = :tid
            GROUP BY es.course_id, c.name
            HAVING COUNT(DISTINCT es.room_id) > 1
        """), {"tid": tenant_id})
        split_rows = res.fetchall()
        print(f"Exam sessions requiring multi-room split: {len(split_rows)}")
        for r in split_rows:
            print(f"  → '{r[1]}': split across {r[2]} rooms")

        # Invigilator pool
        res = await session.execute(
            text("SELECT COUNT(DISTINCT invigilator_staff_profile_id) FROM exam_session WHERE tenant_id = :tid AND invigilator_staff_profile_id IS NOT NULL"),
            {"tid": tenant_id}
        )
        print(f"Unique invigilators in pool: {res.scalar()}")

        # --- 7. Eligibility ---
        res = await session.execute(
            text("SELECT COUNT(*) FROM eligibility WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        elig_count = res.scalar()
        print(f"\nEligibility records: {elig_count}")

        # Coverage: how many faculty per scheduling unit
        res = await session.execute(text("""
            SELECT e.course_id, e.cohort_id, c.name, COUNT(DISTINCT e.staff_profile_id) AS fac_count
            FROM eligibility e
            JOIN course c ON e.course_id = c.id
            WHERE e.tenant_id = :tid
            GROUP BY e.course_id, e.cohort_id, c.name
            ORDER BY fac_count ASC
            LIMIT 10
        """), {"tid": tenant_id})
        rows = res.fetchall()
        min_fac = rows[0][3] if rows else 0
        print(f"Min faculty per scheduling unit: {min_fac}")
        print(f"Bottom 10 scheduling units by faculty coverage:")
        for r in rows:
            print(f"  → '{r[2]}' (cohort {str(r[1])[:8]}...): {r[3]} eligible faculty")

        # --- 8. Summary ---
        res = await session.execute(
            text("SELECT COUNT(*) FROM staff_profile WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        fac_total = res.scalar()

        res = await session.execute(
            text("SELECT COUNT(*) FROM course WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        course_total = res.scalar()

        res = await session.execute(
            text("SELECT COUNT(*) FROM cohort WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        cohort_total = res.scalar()

        res = await session.execute(
            text("SELECT COUNT(*) FROM student_profile WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        student_total = res.scalar()

        res = await session.execute(
            text("SELECT COUNT(*) FROM department WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        dept_total = res.scalar()

        print(f"\n=== Summary ===")
        print(f"Departments: {dept_total}")
        print(f"Cohorts: {cohort_total}")
        print(f"Faculty: {fac_total}")
        print(f"Students: {student_total}")
        print(f"Courses: {course_total}")
        print(f"Eligibility: {elig_count}")
        print(f"Elective sections: {es_count}")
        print(f"Enrollment records: {er_count}")
        print(f"Block courses: {block_count}")
        print(f"Exam sessions: {exam_count}")


if __name__ == "__main__":
    asyncio.run(run_counts())
