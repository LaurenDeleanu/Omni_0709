import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

logger = logging.getLogger("successcore.webhooks")

MAX_RETRIES = 5
BASE_DELAY = 1.0
MAX_DELAY = 300.0

EVENT_TYPES = {
    "employee.created": "New employee added to directory",
    "employee.hired": "Employee marked as hired",
    "employee.updated": "Employee profile modified",
    "employee.deleted": "Employee removed",
    "payslip.generated": "Payslip created in payroll cycle",
    "payroll.finalized": "Payroll cycle finalized and paid",
    "expense.approved": "Expense claim approved",
    "expense.rejected": "Expense claim rejected",
    "course.completed": "Employee completed training course",
    "candidate.applied": "New candidate application received",
    "interview.scheduled": "Interview booked for candidate",
    "kudos.received": "Employee received peer recognition",
    "vacation.approved": "Vacation request approved",
    "vacation.rejected": "Vacation request rejected",
    "agent.run.completed": "AI agent execution finished",
    "ticket.created": "IT support ticket created",
    "ticket.resolved": "IT support ticket resolved",
    "workflow.started": "Onboarding/offboarding workflow started",
    "workflow.completed": "Onboarding/offboarding workflow completed",
    "contract.signed": "Legal contract signed",
    "tenant.provisioned": "New tenant provisioned",
    "tenant.deprovisioned": "Tenant deprovisioned",
}


@dataclass
class WebhookSubscription:
    id: str
    tenant_id: str
    event_types: List[str]
    endpoint_url: str
    secret: str
    is_active: bool = True
    retry_count: int = 0
    last_delivery_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WebhookDelivery:
    id: str
    subscription_id: str
    event_type: str
    payload: dict
    status: str
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    duration_ms: int = 0
    attempt: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookEngine:
    def __init__(self):
        self._subscriptions: Dict[str, WebhookSubscription] = {}
        self._deliveries: List[WebhookDelivery] = []
        self._delivery_lock = asyncio.Lock()

    def register_subscription(self, sub: WebhookSubscription):
        self._subscriptions[sub.id] = sub

    def remove_subscription(self, sub_id: str):
        self._subscriptions.pop(sub_id, None)

    def get_subscriptions(self, tenant_id: str) -> List[WebhookSubscription]:
        return [s for s in self._subscriptions.values() if s.tenant_id == tenant_id]

    async def dispatch_event(self, event_type: str, payload: dict, tenant_id: str) -> int:
        if event_type not in EVENT_TYPES:
            logger.warning(f"Unknown event type: {event_type}")
            return 0

        import asyncio
        asyncio.create_task(self._try_slack_dispatch(event_type, payload, tenant_id))

        from app.services.event_bus import get_event_bus
        get_event_bus().publish_async(event_type, tenant_id=tenant_id, payload=payload)

        matching = [s for s in self.get_subscriptions(tenant_id) if s.is_active and event_type in s.event_types]
        if not matching:
            return 0

        tasks = [self._deliver(s, event_type, payload) for s in matching]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if not isinstance(r, Exception))

    async def _try_slack_dispatch(self, event_type: str, payload: dict, tenant_id: str):
        try:
            from app.services.slack_connector import dispatch_slack_event
            await dispatch_slack_event(tenant_id, event_type, payload)
        except Exception as e:
            logger.debug(f"Slack dispatch skipped: {e}")

    async def _deliver(self, sub: WebhookSubscription, event_type: str, payload: dict):
        import httpx
        import hmac
        import hashlib

        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        signature = hmac.new(
            sub.secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Delivery-Id": uuid.uuid4().hex,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            start = time.monotonic()
            delivery = WebhookDelivery(
                id=uuid.uuid4().hex,
                subscription_id=sub.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempt=attempt,
            )

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(sub.endpoint_url, content=body, headers=headers)
                    delivery.response_code = resp.status_code
                    delivery.response_body = resp.text[:500]
                    delivery.duration_ms = int((time.monotonic() - start) * 1000)

                    if 200 <= resp.status_code < 300:
                        delivery.status = "success"
                        sub.last_delivery_at = datetime.now(timezone.utc)
                        sub.retry_count = 0
                        async with self._delivery_lock:
                            self._deliveries.append(delivery)
                        return delivery
                    else:
                        delivery.status = "failed"
            except Exception as e:
                delivery.status = "error"
                delivery.response_body = str(e)[:500]
                delivery.duration_ms = int((time.monotonic() - start) * 1000)

            async with self._delivery_lock:
                self._deliveries.append(delivery)

            if attempt < MAX_RETRIES:
                delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
                await asyncio.sleep(delay)

        sub.retry_count += 1
        if sub.retry_count > 10:
            sub.is_active = False
            logger.warning(f"Webhook {sub.id} disabled after 10+ consecutive failures")

        raise RuntimeError(f"Webhook delivery to {sub.endpoint_url} failed after {MAX_RETRIES} attempts")

    async def get_delivery_logs(self, subscription_id: str = None, limit: int = 50) -> List[dict]:
        async with self._delivery_lock:
            logs = self._deliveries
            if subscription_id:
                logs = [d for d in logs if d.subscription_id == subscription_id]
            return [
                {
                    "id": d.id,
                    "subscription_id": d.subscription_id,
                    "event_type": d.event_type,
                    "status": d.status,
                    "response_code": d.response_code,
                    "duration_ms": d.duration_ms,
                    "attempt": d.attempt,
                    "created_at": d.created_at.isoformat(),
                }
                for d in logs[-limit:]
            ]


_webhook_engine = WebhookEngine()


def get_webhook_engine() -> WebhookEngine:
    return _webhook_engine
