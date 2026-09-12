from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_jwt
from app.core.tenant_context import set_tenant_context
from app.models.stubs import Notification
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/notifications", tags=["notifications"])


class NotificationRead(BaseModel):
    id: UUID
    identity_id: UUID
    channel: str
    subject: str | None
    body: str | None
    status: str
    created_at: datetime
    sent_at: datetime | None

class NotificationPreferencesRequest(BaseModel):
    email: bool = True
    push: bool = True
    sms: bool = False

class NotificationPreferencesResponse(BaseModel):
    email: bool
    push: bool
    sms: bool

_user_preferences: dict[UUID, dict[str, bool]] = {}


@router.get("", response_model=PaginatedResponse[NotificationRead])
async def list_notifications(
    tenantId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
):
    """List notifications for current tenant (FR-11.1)."""
    result = await db.execute(
        select(Notification)
        .where(Notification.tenant_id == tenantId)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    items = result.scalars().all()
    
    return PaginatedResponse(
        items=[
            NotificationRead(
                id=n.id,
                identity_id=n.identity_id,
                channel=n.channel,
                subject=n.subject,
                body=n.body,
                status=n.status,
                created_at=n.created_at,
                sent_at=n.sent_at
            ) for n in items
        ],
        next_cursor=None
    )


@router.put("/{notificationId}/read")
async def mark_notification_read(
    tenantId: UUID,
    notificationId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
):
    """Mark a notification as read (FR-11.1)."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notificationId,
            Notification.tenant_id == tenantId
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Notification not found"}})
    
    notif.status = "read"
    await db.commit()
    return {"status": "success"}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    tenantId: UUID,
    identity_id: UUID = Depends(verify_jwt),
):
    """Get notification channel preferences for identity (FR-11.1)."""
    prefs = _user_preferences.get(identity_id, {"email": True, "push": True, "sms": False})
    return NotificationPreferencesResponse(**prefs)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    tenantId: UUID,
    body: NotificationPreferencesRequest,
    identity_id: UUID = Depends(verify_jwt),
):
    """Update notification channel preferences for identity (FR-11.1)."""
    _user_preferences[identity_id] = body.dict()
    return NotificationPreferencesResponse(**body.dict())
