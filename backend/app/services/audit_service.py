import logging
import json
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("successcore.audit")


def audit_log(
    action: str,
    resource: str,
    resource_id: str = "",
    user_id: str = "",
    tenant_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    ip_address: str = "",
):
    record = {
        "timestamp": time.time(),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "status": status,
        "ip_address": ip_address,
        "details": details or {},
    }
    logger.info(f"AUDIT | {action} | {resource}/{resource_id} | user={user_id} | tenant={tenant_id} | status={status}")


async def audit_log_persist(
    action: str,
    resource: str,
    resource_id: str = "",
    user_id: str = "",
    tenant_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    ip_address: str = "",
):
    audit_log(action, resource, resource_id, user_id, tenant_id, details, status, ip_address)

    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if r:
            entry = {
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "status": status,
                "details": details or {},
                "ip": ip_address,
            }
            await r.lpush("audit_log", json.dumps(entry, default=str))
            await r.ltrim("audit_log", 0, 9999)
    except Exception as e:
        logger.debug(f"Audit persist failed: {e}")

    try:
        from app.services.pii_sanitizer import sanitize_output
        from app.services.usage_quotas import record_api_call
        record_api_call(tenant_id)
    except Exception:
        pass
