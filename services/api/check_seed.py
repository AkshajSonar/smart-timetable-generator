import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        for table, label in [
            ("identity", "Identities"),
            ("tenant", "Tenants"),
            ("academic_term", "Terms"),
            ("department", "Departments"),
            ("course", "Courses"),
            ("cohort", "Cohorts"),
            ("staff_profile", "Staff profiles"),
            ("student_profile", "Student profiles"),
            ("room", "Rooms"),
            ("period_template", "Period templates"),
            ("eligibility", "Eligibility rows"),
            ("timetable_version", "Timetable versions"),
        ]:
            r = await s.execute(text(f"SELECT count(*) FROM {table}"))
            print(f"  {label}: {r.scalar()}")
        
        # Get tenant ID
        r = await s.execute(text("SELECT id, name FROM tenant LIMIT 1"))
        row = r.fetchone()
        if row:
            print(f"\nTenant ID: {row[0]}  Name: {row[1]}")
        
        # Get term ID
        r = await s.execute(text("SELECT id, name FROM academic_term LIMIT 1"))
        row = r.fetchone()
        if row:
            print(f"Term ID:   {row[0]}  Name: {row[1]}")

asyncio.run(check())
