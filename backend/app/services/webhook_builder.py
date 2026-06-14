"""
webhook_builder.py — User-configurable webhook endpoints for system events.
"""
import logging
import json
import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import httpx

logger = logging.getLogger("successcore.webhooks")

RETRY_BACKOFF = [30, 120, 600, 3600]  # 30s, 2min, 10min, 1h


class WebhookSubscription(BaseModel):
    id: str
    tenant_id: str
    event_type: str
    endpoint_url: str
    secret: str
    is_active: bool = True
    description: str = ""
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = ""
    last_triggered: Optional[str] = None


async def create_subscription(
    db: AsyncSession,
    tenant_id: str,
    event_type: str,
    endpoint_url: str,
    description: str = "",
    secret: Optional[str] = None,
) -> dict:
    """Create a new webhook subscription."""
    import secrets
    sub_id = uuid.uuid4().hex
    webhook_secret = secret or secrets.token_urlsafe(24)

    sub = {
        "id": sub_id,
        "tenant_id": tenant_id,
        "event_type": event_type,
        "endpoint_url": endpoint_url,
        "secret": webhook_secret,
        "is_active": True,
        "description": description,
        "retry_count": 0,
        "max_retries": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_triggered": None,
    }

    # Store in Redis for persistence
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        await r.hset(f"webhook:subs:{tenant_id}", sub_id, json.dumps(sub))
    except Exception as e:
        logger.warning(f"Webhook subscription not persisted to Redis: {e}")

    return sub


async def list_subscriptions(db: AsyncSession, tenant_id: str) -> list[dict]:
    """List all webhook subscriptions for a tenant."""
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        raw = await r.hgetall(f"webhook:subs:{tenant_id}")
        return [json.loads(v) for v in raw.values()]
    except Exception:
        return []


async def delete_subscription(db: AsyncSession, tenant_id: str, sub_id: str):
    """Delete a webhook subscription."""
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        await r.hdel(f"webhook:subs:{tenant_id}", sub_id)
        return {"status": "deleted", "id": sub_id}
    except Exception:
        return {"status": "error", "id": sub_id}


async def dispatch_webhook(tenant_id: str, event_type: str, payload: dict):
    """Dispatch a webhook event to all matching subscriptions."""
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        raw = await r.hgetall(f"webhook:subs:{tenant_id}")
        subs = [json.loads(v) for v in raw.values()]
    except Exception:
        return

    matching = [s for s in subs if s["event_type"] == event_type and s["is_active"]]
    if not matching:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        for sub in matching:
            try:
                body = json.dumps(payload)
                sig = hmac.new(
                    sub["secret"].encode(), body.encode(), hashlib.sha256
                ).hexdigest()

                resp = await client.post(
                    sub["endpoint_url"],
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": sig,
                        "X-Webhook-Event": event_type,
                        "X-Webhook-ID": sub["id"],
                    },
                )
                if resp.status_code < 200 or resp.status_code >= 300:
                    logger.warning(f"Webhook failed: {sub['id']} -> {resp.status_code}")
                    await _schedule_retry(tenant_id, sub, payload)
                else:
                    sub["last_triggered"] = datetime.now(timezone.utc).isoformat()
                    sub["retry_count"] = 0
            except Exception as e:
                logger.error(f"Webhook delivery error: {e}")
                await _schedule_retry(tenant_id, sub, payload)


async def _schedule_retry(tenant_id: str, sub: dict, payload: dict):
    """Schedule a webhook retry with exponential backoff."""
    retry_count = sub.get("retry_count", 0) + 1
    if retry_count > sub.get("max_retries", 3):
        sub["is_active"] = False
        logger.error(f"Webhook disabled after {retry_count} failures: {sub['id']}")
        return

    sub["retry_count"] = retry_count
    delay = RETRY_BACKOFF[min(retry_count - 1, len(RETRY_BACKOFF) - 1)]

    try:
        from app.core.task_queue import enqueue
        await enqueue(
            "webhook_retry",
            {"tenant_id": tenant_id, "sub": sub, "payload": payload},
            tenant_id=tenant_id,
        )
    except Exception:
        pass
