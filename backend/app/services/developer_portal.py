"""
developer_portal.py — Developer Portal: API key management, usage analytics.
"""
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

logger = logging.getLogger("successcore.developer")

API_KEY_PREFIX = "sc_"


async def generate_api_key() -> tuple[str, str]:
    """Generate API key + hash pair. Returns (plaintext, hash)."""
    plain = API_KEY_PREFIX + secrets.token_urlsafe(32)
    h = hashlib.sha256(plain.encode()).hexdigest()
    return plain, h


async def create_api_key(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    scopes: list[str],
    user_id: str,
) -> dict:
    """Create a new API key for a tenant."""
    from app.models.oauth import OAuthClient
    import uuid

    plain, hashed = await generate_api_key()
    key_id = uuid.uuid4().hex

    client = OAuthClient(
        id=key_id,
        client_id=key_id,
        client_secret_hash=hashed,
        client_name=name,
        tenant_id=tenant_id,
        allowed_scopes=scopes,
        redirect_uris=[],
        is_active=True,
    )
    db.add(client)
    await db.commit()

    return {
        "id": key_id,
        "name": name,
        "api_key": plain,
        "scopes": scopes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message": "Store this key securely. It will not be shown again.",
    }


async def list_api_keys(db: AsyncSession, tenant_id: str) -> list[dict]:
    """List all API keys for a tenant (masked)."""
    from app.models.oauth import OAuthClient
    result = await db.execute(
        select(OAuthClient).where(
            OAuthClient.tenant_id == tenant_id,
        )
    )
    clients = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.client_name,
            "scopes": c.allowed_scopes,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in clients
    ]


async def revoke_api_key(db: AsyncSession, key_id: str, tenant_id: str):
    """Revoke an API key."""
    from app.models.oauth import OAuthClient
    result = await db.execute(
        select(OAuthClient).where(
            OAuthClient.id == key_id,
            OAuthClient.tenant_id == tenant_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        return None
    client.is_active = False
    await db.commit()
    return {"status": "revoked", "key_id": key_id}


async def get_api_usage_stats(db: AsyncSession, tenant_id: str, days: int = 30) -> dict:
    """Get API usage statistics for a tenant."""
    from app.models.agent import AgentExecutionRun
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(AgentExecutionRun).where(AgentExecutionRun.created_at >= cutoff)
    )
    runs = result.scalars().all()

    total = len(runs)
    success = sum(1 for r in runs if getattr(r, "status", "") == "success")
    failed = total - success

    endpoints = {}
    for r in runs:
        ep = getattr(r, "endpoint", "unknown")
        endpoints[ep] = endpoints.get(ep, 0) + 1

    return {
        "period_days": days,
        "total_calls": total,
        "success_rate": round(success / total * 100, 1) if total else 0,
        "failed": failed,
        "top_endpoints": sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:10],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
