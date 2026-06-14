"""
dev_portal_api.py — Developer Portal API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_tenant_db, get_current_user, require_roles

router = APIRouter(prefix="/dev", tags=["Developer Portal"])


class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] = ["read"]


@router.post("/api-keys")
async def create_api_key_endpoint(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.developer_portal import create_api_key
    tenant_id = current_user.get("tenant_id", "default")
    user_id = current_user.get("sub", "")
    return await create_api_key(db, tenant_id, body.name, body.scopes, user_id)


@router.get("/api-keys")
async def list_api_keys_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.developer_portal import list_api_keys
    return {"keys": await list_api_keys(db, current_user.get("tenant_id", "default"))}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key_endpoint(
    key_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.developer_portal import revoke_api_key
    result = await revoke_api_key(db, key_id, current_user.get("tenant_id", "default"))
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
    return result


@router.get("/usage")
async def api_usage_stats(
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.developer_portal import get_api_usage_stats
    return await get_api_usage_stats(db, current_user.get("tenant_id", "default"), days)
