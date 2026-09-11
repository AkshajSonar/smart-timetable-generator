"""Rooms router — CRUD under /api/v1/tenants/{tenantId}/rooms."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.room import Room
from app.schemas.common import PaginatedResponse
from app.schemas.room import RoomCreate, RoomRead, RoomUpdate

from app.rbac.dependencies import require_role
router = APIRouter(
    dependencies=[Depends(require_role(["institution_admin", "department_head"]))],
    prefix="/api/v1/tenants/{tenantId}/rooms", tags=["rooms"])


@router.post("", response_model=RoomRead, status_code=201)
async def create_room(tenantId: UUID, body: RoomCreate, db: AsyncSession = Depends(set_tenant_context)):
    room = Room(tenant_id=tenantId, **body.model_dump())
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.get("", response_model=PaginatedResponse[RoomRead])
async def list_rooms(tenantId: UUID, cursor: str | None = None, limit: int = 50, db: AsyncSession = Depends(set_tenant_context)):
    q = select(Room).order_by(Room.name).limit(limit + 1)
    if cursor:
        q = q.where(Room.name > cursor)
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = items[-1].name if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.get("/{roomId}", response_model=RoomRead)
async def get_room(tenantId: UUID, roomId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Room).where(Room.id == roomId))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Room not found"}})
    return room


@router.patch("/{roomId}", response_model=RoomRead)
async def update_room(tenantId: UUID, roomId: UUID, body: RoomUpdate, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Room).where(Room.id == roomId))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Room not found"}})
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    await db.commit()
    await db.refresh(room)
    return room


@router.delete("/{roomId}", status_code=204)
async def delete_room(tenantId: UUID, roomId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Room).where(Room.id == roomId))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Room not found"}})
    await db.delete(room)
    await db.commit()
