"""Courses router — CRUD under /api/v1/tenants/{tenantId}/courses."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.course import Course
from app.schemas.common import PaginatedResponse
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate

from app.rbac.dependencies import require_role
router = APIRouter(
    dependencies=[Depends(require_role(["institution_admin", "department_head"]))],
    prefix="/api/v1/tenants/{tenantId}/courses", tags=["courses"])


@router.post("", response_model=CourseRead, status_code=201)
async def create_course(
    tenantId: UUID,
    body: CourseCreate,
    db: AsyncSession = Depends(set_tenant_context),
):
    course = Course(
        tenant_id=tenantId,
        department_id=body.department_id,
        name=body.name,
        type=body.type,
        credit_value=body.credit_value,
        hours_per_week=body.hours_per_week,
        block_size=body.block_size,
        required_equipment_tags=body.required_equipment_tags,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("", response_model=PaginatedResponse[CourseRead])
async def list_courses(
    tenantId: UUID,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(set_tenant_context),
):
    q = select(Course).order_by(Course.name).limit(limit + 1)
    if cursor:
        q = q.where(Course.name > cursor)
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = items[-1].name if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.get("/{courseId}", response_model=CourseRead)
async def get_course(tenantId: UUID, courseId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Course).where(Course.id == courseId))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Course not found"}})
    return course


@router.patch("/{courseId}", response_model=CourseRead)
async def update_course(tenantId: UUID, courseId: UUID, body: CourseUpdate, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Course).where(Course.id == courseId))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Course not found"}})
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/{courseId}", status_code=204)
async def delete_course(tenantId: UUID, courseId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Course).where(Course.id == courseId))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Course not found"}})
    await db.delete(course)
    await db.commit()
