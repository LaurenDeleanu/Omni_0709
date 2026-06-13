import logging
from typing import List, Optional

logger = logging.getLogger("successcore.push")

WEB_PUSH_SUBSCRIPTIONS: list = []


def add_subscription(sub: dict):
    existing = [s for s in WEB_PUSH_SUBSCRIPTIONS if s.get("endpoint") == sub.get("endpoint")]
    if not existing:
        WEB_PUSH_SUBSCRIPTIONS.append(sub)


def remove_subscription(endpoint: str):
    global WEB_PUSH_SUBSCRIPTIONS
    WEB_PUSH_SUBSCRIPTIONS = [s for s in WEB_PUSH_SUBSCRIPTIONS if s.get("endpoint") != endpoint]


def get_subscription_count() -> int:
    return len(WEB_PUSH_SUBSCRIPTIONS)


async def send_push_notification(
    message: str,
    title: str = "SuccessCore",
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> int:
    subscriptions = WEB_PUSH_SUBSCRIPTIONS
    if tenant_id:
        subscriptions = [s for s in subscriptions if s.get("tenant_id") == tenant_id]
    if user_id:
        subscriptions = [s for s in subscriptions if s.get("user_id") == user_id]

    if not subscriptions:
        return 0

    import json
    payload = json.dumps({"title": title, "body": message, "icon": "/icon-192x192.png"})

    sent = 0
    for sub in subscriptions:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    sub["endpoint"],
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Content-Encoding": "aes128gcm",
                        "TTL": "86400",
                    }
                )
                if resp.status_code < 300:
                    sent += 1
                else:
                    logger.warning(f"Push delivery failed ({resp.status_code}): {resp.text[:200]}")
                    if resp.status_code in (404, 410):
                        remove_subscription(sub["endpoint"])
        except Exception as e:
            logger.error(f"Push notification error: {e}")

    return sent
