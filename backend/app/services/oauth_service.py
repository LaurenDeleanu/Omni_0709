import secrets
import hashlib
import base64
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("successcore.oauth")

TOKEN_EXPIRY_MINUTES = 60
REFRESH_EXPIRY_DAYS = 30


def generate_client_credentials() -> tuple:
    client_id = f"sc_{secrets.token_hex(16)}"
    client_secret = secrets.token_urlsafe(32)
    secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
    return client_id, client_secret, secret_hash


async def register_oauth_client(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    redirect_uris: str,
    scopes: str = "read:all",
    description: str = "",
    created_by: str = "",
) -> dict:
    from app.models.oauth import OAuthClient
    import uuid

    client_id, client_secret, secret_hash = generate_client_credentials()

    client = OAuthClient(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret_hash=secret_hash,
        name=name,
        description=description,
        redirect_uris=redirect_uris,
        allowed_scopes=scopes,
        created_by=created_by,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)

    return {
        "id": client.id,
        "client_id": client_id,
        "client_secret": client_secret,
        "name": name,
        "redirect_uris": redirect_uris,
        "scopes": scopes,
    }


async def validate_client(db: AsyncSession, client_id: str, client_secret: str) -> Optional[dict]:
    from app.models.oauth import OAuthClient
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id, OAuthClient.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        return None
    secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
    if secret_hash != client.client_secret_hash:
        return None
    return {
        "id": client.id,
        "client_id": client.client_id,
        "tenant_id": client.tenant_id,
        "scopes": client.allowed_scopes,
        "redirect_uris": client.redirect_uris.split(",") if client.redirect_uris else [],
    }


async def generate_authorization_code(db: AsyncSession, client_id: str, user_id: str, scopes: str, redirect_uri: str) -> str:
    code = secrets.token_urlsafe(32)
    from app.models.oauth import OAuthToken
    import uuid

    token = OAuthToken(
        id=uuid.uuid4().hex,
        client_id=client_id,
        user_id=user_id,
        access_token_hash=hashlib.sha256(code.encode()).hexdigest(),
        scopes=scopes,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(token)
    await db.commit()
    return code


async def exchange_code_for_tokens(db: AsyncSession, code: str, client_id: str, client_secret: str) -> Optional[dict]:
    client = await validate_client(db, client_id, client_secret)
    if not client:
        return None

    code_hash = hashlib.sha256(code.encode()).hexdigest()
    from app.models.oauth import OAuthToken
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.access_token_hash == code_hash,
            OAuthToken.client_id == client_id,
            OAuthToken.revoked == False,
            OAuthToken.expires_at > datetime.now(timezone.utc),
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return None

    token.revoked = True
    token.access_token_hash = "USED"

    import uuid
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    at_hash = hashlib.sha256(access_token.encode()).hexdigest()
    rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    at = OAuthToken(
        id=uuid.uuid4().hex,
        client_id=client_id,
        user_id=token.user_id,
        access_token_hash=at_hash,
        refresh_token_hash=rt_hash,
        scopes=client["scopes"],
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
    )
    db.add(at)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_EXPIRY_MINUTES * 60,
        "scopes": client["scopes"],
    }


async def introspect_token(db: AsyncSession, access_token: str) -> Optional[dict]:
    at_hash = hashlib.sha256(access_token.encode()).hexdigest()
    from app.models.oauth import OAuthToken
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.access_token_hash == at_hash,
            OAuthToken.revoked == False,
            OAuthToken.expires_at > datetime.now(timezone.utc),
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return None
    return {
        "active": True,
        "client_id": token.client_id,
        "user_id": token.user_id,
        "scopes": token.scopes,
        "exp": int(token.expires_at.timestamp()),
    }


async def revoke_token(db: AsyncSession, access_token: str) -> bool:
    at_hash = hashlib.sha256(access_token.encode()).hexdigest()
    from app.models.oauth import OAuthToken
    result = await db.execute(select(OAuthToken).where(OAuthToken.access_token_hash == at_hash))
    token = result.scalar_one_or_none()
    if not token:
        return False
    token.revoked = True
    await db.commit()
    return True
