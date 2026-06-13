import logging
import hmac
import hashlib
import json
import httpx
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger("successcore.webhook_replay")


async def replay_delivery(subscription_id: str, delivery_id: str, webhook_engine) -> dict:
    sub = webhook_engine._subscriptions.get(subscription_id)
    if not sub:
        raise ValueError("Subscription not found")

    delivery = None
    for d in webhook_engine._deliveries:
        if d.id == delivery_id:
            delivery = d
            break
    if not delivery:
        raise ValueError("Delivery not found")

    body = json.dumps(delivery.payload, ensure_ascii=False, default=str).encode("utf-8")
    signature = hmac.new(sub.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": delivery.event_type,
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Delivery-Id": f"replay-{delivery_id[:8]}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(sub.endpoint_url, content=body, headers=headers)
            return {
                "status": "delivered" if 200 <= resp.status_code < 300 else "failed",
                "response_code": resp.status_code,
                "response_body": resp.text[:500],
                "replayed_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
