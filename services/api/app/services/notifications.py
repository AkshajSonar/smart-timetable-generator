"""Notification stub service — FR-11.1.

Hackathon implementation: writes a Notification row with status='sent'
immediately (no real delivery integration). Replace send_notification with
a real email/SMS gateway call post-hackathon without changing call sites.

Tie-break / design choice (§31 latitude):
  Channel defaults to 'email'. Status written as 'sent' (stub — no actual
  delivery occurs). sent_at is set to now(). This means the notification
  table accurately records who was notified and when; the delivery proof
  is the status field, not an external system receipt.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


async def send_notification(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    identity_id: UUID,
    subject: str,
    body: str,
    channel: str = "email",
) -> None:
    """Persist a Notification row with status='sent' (stub delivery)."""
    from app.models.stubs import Notification

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    notif = Notification(
        tenant_id=tenant_id,
        identity_id=identity_id,
        channel=channel,
        subject=subject,
        body=body,
        status="sent",   # stub: mark as sent immediately
        created_at=now,
        sent_at=now,
    )
    db.add(notif)
    # Caller is responsible for committing the outer transaction.
