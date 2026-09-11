"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    users,
    substitutions,
    rules,
    terms,
)

ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(
    title="Smart Timetable Generator API",
    version="0.1.0",
    description="Phase 1: Master data CRUD + single-cohort CP-SAT solver (H1–H9)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict:
    """Return CORS headers appropriate for the incoming origin."""
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure CORS headers are present on all HTTP error responses.

    FastAPI's CORSMiddleware only fires on normal responses; exceptions
    bypass it. This handler re-adds the headers so the browser doesn't
    see a CORS error on 401/403/404/etc.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=_cors_headers(request),
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
app.include_router(users.router)
app.include_router(substitutions.router)
app.include_router(rules.router)
app.include_router(terms.router)



@app.get("/health")
async def health():
    return {"status": "ok"}
