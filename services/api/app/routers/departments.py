"""Departments router — CRUD under /api/v1/tenants/{tenantId}/departments."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.department import Department
from app.schemas.common import PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/departments", tags=["departments"])


@router.post("", response_model=DepartmentRead, status_code=201)
async def create_department(
    tenantId: UUID,
    body: DepartmentCreate,
    db: AsyncSession = Depends(set_tenant_context),
):
    dept = Department(tenant_id=tenantId, name=body.name)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.get("", response_model=PaginatedResponse[DepartmentRead])
async def list_departments(
    tenantId: UUID,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(set_tenant_context),
):
    q = select(Department).order_by(Department.name).limit(limit + 1)
    if cursor:
        q = q.where(Department.name > cursor)
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = items[-1].name if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.get("/{deptId}", response_model=DepartmentRead)
async def get_department(
    tenantId: UUID,
    deptId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
):
    result = await db.execute(select(Department).where(Department.id == deptId))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Department not found", "details": {}}})
    return dept


@router.patch("/{deptId}", response_model=DepartmentRead)
async def update_department(
    tenantId: UUID,
    deptId: UUID,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(set_tenant_context),
):
    result = await db.execute(select(Department).where(Department.id == deptId))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Department not found", "details": {}}})
    if body.name is not None:
        dept.name = body.name
    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/{deptId}", status_code=204)
async def delete_department(
    tenantId: UUID,
    deptId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
):
    result = await db.execute(select(Department).where(Department.id == deptId))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Department not found", "details": {}}})
    await db.delete(dept)
    await db.commit()
