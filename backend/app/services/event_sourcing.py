import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("successcore.events")

EVENT_SCHEMAS = {
    "employee.created": {"version": "1.0", "fields": ["user_id", "email", "full_name", "department", "role", "hire_date"]},
    "employee.updated": {"version": "1.0", "fields": ["user_id", "changed_fields"]},
    "employee.deleted": {"version": "1.0", "fields": ["user_id", "email"]},
    "salary.changed": {"version": "1.0", "fields": ["user_id", "old_salary", "new_salary", "changed_by"]},
    "vacation.approved": {"version": "1.0", "fields": ["request_id", "user_id", "start_date", "end_date", "days"]},
    "expense.approved": {"version": "1.0", "fields": ["claim_id", "user_id", "amount", "category"]},
    "course.completed": {"version": "1.0", "fields": ["enrollment_id", "user_id", "course_id", "course_title"]},
    "kudos.received": {"version": "1.0", "fields": ["kudos_id", "sender_id", "receiver_id", "badge", "message"]},
    "agent.run.completed": {"version": "1.0", "fields": ["run_id", "agent_id", "status", "cost_usd", "latency_ms"]},
}


def publish_event(event_type: str, payload: Dict[str, Any], tenant_id: str = "") -> dict:
    schema = EVENT_SCHEMAS.get(event_type)
    if not schema:
        logger.warning(f"Unknown event type: {event_type}")
        return {"error": "unknown_event_type"}

    event = {
        "event_id": str(__import__('uuid').uuid4().hex),
        "event_type": event_type,
        "schema_version": schema["version"],
        "tenant_id": tenant_id,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        from app.services.webhook_engine import get_webhook_engine
        get_webhook_engine().dispatch_event(event_type, payload, tenant_id)
    except Exception as e:
        logger.debug(f"Webhook dispatch skipped: {e}")

    try:
        from app.services.event_bus import get_event_bus
        get_event_bus().publish_async(event_type, tenant_id=tenant_id, payload=payload)
    except Exception as e:
        logger.debug(f"Event bus publish skipped: {e}")

    logger.debug(f"Event published: {event_type} ({event['event_id']})")
    return event


async def publish_event_async(event_type: str, payload: Dict[str, Any], tenant_id: str = "") -> dict:
    event = publish_event(event_type, payload, tenant_id)
    try:
        from app.services.event_trigger_service import handle_event
        from app.core.database import AsyncSessionGlobal
        async with AsyncSessionGlobal() as db:
            await handle_event(event_type, payload, db)
    except Exception as e:
        logger.debug(f"Event trigger handler skipped: {e}")
    return event
