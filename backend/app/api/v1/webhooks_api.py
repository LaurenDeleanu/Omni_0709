"""
webhooks_api.py — Webhook Builder API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, get_current_user, require_roles

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class CreateWebhookRequest(BaseModel):
    event_type: str
    endpoint_url: str
    description: str = ""
    secret: str = ""


@router.post("")
async def create_webhook(
    body: CreateWebhookRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "manager"])),
):
    from app.services.webhook_builder import create_subscription
    tenant_id = current_user.get("tenant_id", "default")
    return await create_subscription(db, tenant_id, body.event_type, body.endpoint_url, body.description, body.secret or None)


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.webhook_builder import list_subscriptions
    return {"webhooks": await list_subscriptions(db, current_user.get("tenant_id", "default"))}


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.webhook_builder import delete_subscription
    return await delete_subscription(db, current_user.get("tenant_id", "default"), webhook_id)


@router.post("/test")
async def test_webhook(
    body: CreateWebhookRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a test event to verify webhook endpoint."""
    from app.services.webhook_builder import dispatch_webhook
    import hashlib

    test_payload = {
        "event": "test",
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "message": f"Test webhook from {current_user.get('email', 'unknown')}",
    }
    await dispatch_webhook(current_user.get("tenant_id", "default"), "test", test_payload)
    return {"status": "sent", "event": "test"}
