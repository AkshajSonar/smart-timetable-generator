"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    departments,
    courses,
    rooms,
    staff_profiles,
    eligibility,
    cohorts,
    period_templates,
    timetables,
    tenants,
    reports,
    import_data,
    students,
    exams,
)

app = FastAPI(
    title="Smart Timetable Generator API",
    version="0.1.0",
    description="Phase 1: Master data CRUD + single-cohort CP-SAT solver (H1–H9)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants.router)
app.include_router(departments.router)
app.include_router(courses.router)
app.include_router(rooms.router)
app.include_router(staff_profiles.router)
app.include_router(eligibility.router)
app.include_router(cohorts.router)
app.include_router(period_templates.router)
app.include_router(timetables.router)
app.include_router(reports.router)
app.include_router(import_data.router)
app.include_router(students.router)
app.include_router(exams.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
