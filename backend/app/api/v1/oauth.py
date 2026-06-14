from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.services.oauth_service import (
    register_oauth_client, validate_client, exchange_code_for_tokens,
    introspect_token, revoke_token, generate_authorization_code
)
from app.services.oauth_rate_limiter import check_oauth_rate_limit, get_oauth_rate_limit_status
from app.services.integrations.google import GoogleWorkspaceIntegration
from app.services.integrations.microsoft import Microsoft365Integration

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class OAuthClientCreate(BaseModel):
    name: str
    redirect_uris: str
    scopes: str = "read:all"
    description: str = ""


class OAuthClientOut(BaseModel):
    id: str
    client_id: str
    client_secret: str
    name: str
    redirect_uris: str
    scopes: str


class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None
    refresh_token: Optional[str] = None


class IntrospectRequest(BaseModel):
    token: str


class RevokeRequest(BaseModel):
    token: str


@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def create_oauth_client(
    body: OAuthClientCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "")
    result = await register_oauth_client(
        db, tenant_id, body.name, body.redirect_uris,
        body.scopes, body.description, current_user.get("email", "")
    )
    return result


@router.post("/authorize")
async def authorize(
    client_id: str = None,
    redirect_uri: str = None,
    scope: str = "read:all",
    state: str = "",
    response_type: str = "code",
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code is supported")

    code = await generate_authorization_code(
        db, client_id,
        current_user.get("sub", "").split("|")[-1],
        scope, redirect_uri or ""
    )
    redirect = f"{redirect_uri}?code={code}"
    if state:
        redirect += f"&state={state}"
    return {"redirect": redirect, "code": code}


@router.post("/token")
@limiter.limit("20/minute")
async def token(body: TokenRequest, db: AsyncSession = Depends(get_tenant_db)):
    if body.grant_type == "authorization_code":
        if not body.code:
            raise HTTPException(status_code=400, detail="code is required")
        result = await exchange_code_for_tokens(db, body.code, body.client_id, body.client_secret)
        if not result:
            raise HTTPException(status_code=400, detail="Invalid code or client credentials")
        return result

    elif body.grant_type == "refresh_token":
        if not body.refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required")
        result = await exchange_refresh_token(db, body.refresh_token, body.client_id, body.client_secret)
        if not result:
            raise HTTPException(status_code=400, detail="Invalid refresh_token or client credentials")
        return result

    raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {body.grant_type}")


@router.post("/introspect")
@limiter.limit("20/minute")
async def introspect(body: IntrospectRequest, db: AsyncSession = Depends(get_tenant_db)):
    result = await introspect_token(db, body.token)
    if not result:
        return {"active": False}
    return result


@router.post("/revoke")
async def revoke(body: RevokeRequest, db: AsyncSession = Depends(get_tenant_db)):
    ok = await revoke_token(db, body.token)
    return {"status": "revoked" if ok else "not_found"}


@router.get("/clients")
async def list_oauth_clients(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.models.oauth import OAuthClient
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "")
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.tenant_id == tenant_id).order_by(OAuthClient.created_at.desc())
    )
    clients = result.scalars().all()
    return [{
        "id": c.id, "client_id": c.client_id, "name": c.name,
        "description": c.description, "redirect_uris": c.redirect_uris,
        "scopes": c.allowed_scopes, "is_active": c.is_active,
        "created_at": c.created_at.isoformat()
    } for c in clients]


@router.post("/clients/{client_id}/rotate-secret")
async def rotate_client_secret(
    client_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.models.oauth import OAuthClient
    result = await db.execute(select(OAuthClient).where(OAuthClient.client_id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    import secrets, hashlib
    new_secret = secrets.token_urlsafe(32)
    client.client_secret_hash = hashlib.sha256(new_secret.encode()).hexdigest()
    await db.commit()
    return {"client_id": client_id, "client_secret": new_secret}


@router.delete("/clients/{client_id}")
async def delete_oauth_client(
    client_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.models.oauth import OAuthClient
    result = await db.execute(select(OAuthClient).where(OAuthClient.client_id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.is_active = False
    await db.commit()
    return {"status": "deactivated", "client_id": client_id}


@router.get("/rate-limit/{client_id}")
async def get_oauth_rate_limit(
    client_id: str,
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return get_oauth_rate_limit_status(client_id)


@router.get("/analytics")
async def get_oauth_analytics(
    client_id: str = Query(""),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.oauth_analytics import get_oauth_stats
    return get_oauth_stats(client_id)


class DeprecationMiddleware:
    @staticmethod
    def add_headers(path: str) -> dict:
        deprecated = {}
        if path.startswith("/api/v1/legacy"):
            deprecated = {"Deprecation": "true", "Sunset": "Sat, 01 Jan 2027 00:00:00 GMT"}
        return deprecated

@router.get("/google/login")
async def google_sso_login():
    url = await GoogleWorkspaceIntegration.get_auth_url()
    return {"auth_url": url}

@router.get("/google/callback")
async def google_sso_callback(code: str, db: AsyncSession = Depends(get_tenant_db)):
    # Exchange code
    user_info = await GoogleWorkspaceIntegration.exchange_code(code)
    
    # In a real scenario, we'd lookup/create the user in DB and generate a session token
    # For now, return the mock user info
    return {"message": "Google SSO successful", "user": user_info}

@router.get("/microsoft/login")
async def microsoft_sso_login():
    url = await Microsoft365Integration.get_auth_url()
    return {"auth_url": url}

@router.get("/microsoft/callback")
async def microsoft_sso_callback(code: str, db: AsyncSession = Depends(get_tenant_db)):
    # Exchange code
    user_info = await Microsoft365Integration.exchange_code(code)
    
    # In a real scenario, we'd lookup/create the user in DB and generate a session token
    # For now, return the mock user info
    return {"message": "Microsoft SSO successful", "user": user_info}
