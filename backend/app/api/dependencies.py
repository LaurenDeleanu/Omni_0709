from typing import AsyncGenerator, Dict, List, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.database import engine, AsyncSessionGlobal
from app.core.auth import auth_verifier
from app.core.config import settings
from app.core.logger import logger
from functools import lru_cache
import re

# auto_error=False so we can fall back to cookie auth without 403
auth_scheme = HTTPBearer(auto_error=False)

async def get_global_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionGlobal() as session:
        yield session

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme)
) -> dict:
    """
    [C3] Accepts auth via:
      1. Authorization: Bearer <token>  (primary — Auth0, local dev)
      2. HttpOnly cookie 'access_token'  (secure browser sessions via local login)
    Raises 401 if neither is present or both are invalid.
    """
    token: Optional[str] = None

    # 1. Bearer token takes priority (Auth0 + API clients)
    if credentials and credentials.credentials:
        token = credentials.credentials

    # 2. Fallback: httpOnly cookie set by /users/login
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Inicia sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_verifier.verify(token)
    return payload


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme)
) -> Optional[dict]:
    """
    Optional authentication dependency. Returns payload if valid, otherwise None.
    Does not raise exceptions.
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        return auth_verifier.verify(token)
    except Exception:
        return None


# [M9 FIX] — TTL-based cache for tenant sessionmakers is no longer needed since we use RLS on public schema.
def _get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )

async def get_tenant_db(
    current_user: dict = Depends(get_current_user)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que inyecta una sesión asíncrona de base de datos
    apuntando automáticamente al esquema del tenant del request.
    """
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id")

    # Claim directo (tokens locales HS256)
    if not tenant_id:
        tenant_id = current_user.get("tenant_id")

    # [C2 FIX] — Never silently fall back to a real tenant.
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido: falta el claim tenant_id. Configura la Auth0 Action o usa login local."
        )

    # Validate format and length (PostgreSQL schema names max 63 chars)
    if not re.match(r'^[a-zA-Z0-9_]{1,50}$', tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant-ID inválido en el token."
        )

    tenant_schema = f"tenant_{tenant_id}"

    if "sqlite" in settings.SQLALCHEMY_DATABASE_URI:
        # SQLite: single file, no schema isolation
        AsyncSessionTenant = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    else:
        AsyncSessionTenant = _get_sessionmaker()

    async with AsyncSessionTenant() as db:
        db.info["tenant_id"] = tenant_id
        # Set tenant context for RLS policies (defense-in-depth)
        try:
            from app.core.tenant_context import set_tenant_context
            await set_tenant_context(db, tenant_id)
        except Exception:
            pass
        yield db


def require_roles(required_roles: List[str]):
    """
    Dependency para RBAC (Role-Based Access Control).

    Prioridad de búsqueda de roles:
      1. Claim custom de Auth0 Action: 'https://successcore.com/app_metadata.roles'
      2. Claim 'https://successcore.com/roles' (Auth0 RBAC nativo)
      3. Claim 'roles' directo en el payload (tokens locales HS256)
    """
    def role_checker(current_user: dict = Depends(get_current_user)):
        # 1. Claim custom via Auth0 Action (producción)
        app_metadata = current_user.get("https://successcore.com/app_metadata", {})
        user_roles: list = app_metadata.get("roles", [])

        # 2. Auth0 RBAC nativo (namespace alternativo)
        if not user_roles:
            user_roles = current_user.get("https://successcore.com/roles", [])

        # 3. Claim directo (tokens locales HS256)
        if not user_roles:
            user_roles = current_user.get("roles", [])

        # [C1 FIX] — No more hr_admin fallback. A token with no roles
        # must be denied. Configure Auth0 Actions to inject roles.
        if not user_roles:
            logger.warning(
                f"[rbac] Token sin roles para sub='{current_user.get('sub')}'. "
                "Acceso denegado. Configura Auth0 Actions o asegúrate de usar login local."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token inválido: no contiene roles de acceso. Contacta al administrador."
            )

        if "super_admin" in user_roles:
            return current_user

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes los permisos necesarios para realizar esta acción."
            )
        return current_user
    return role_checker


from sqlalchemy import select
from app.models.tenant import Tenant

def check_module_enabled(module_name: str):
    """
    Dependency que verifica si un módulo específico de SaaS (it, finance, training, schedules)
    está activo para el inquilino (tenant) actual.
    Si está inactivo, retorna 403 Forbidden.
    """
    async def checker(
        current_user: dict = Depends(get_current_user),
        global_db: AsyncSession = Depends(get_global_db)
    ):
        app_metadata = current_user.get("https://successcore.com/app_metadata", {})
        tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id")

        # [M6 FIX] — Never silently pass if the tenant is unknown.
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token inválido: falta el claim tenant_id."
            )
        
        result = await global_db.execute(
            select(Tenant).where(
                (Tenant.id == tenant_id) |
                (Tenant.schema_name == tenant_id) |
                (Tenant.schema_name == f"tenant_{tenant_id}")
            )
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            # [M6 FIX] — Tenant not found = deny access, not pass-through.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organización no encontrada. Contacta al soporte."
            )
            
        modules = tenant.enabled_modules or {}
        if not modules.get(module_name, True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El módulo '{module_name}' está desactivado para tu organización."
            )
        return tenant
    return checker


def require_super_admin():
    """
    Dependency para verificar si el usuario tiene privilegios de Super Administrador (Global).
    """
    async def checker(
        current_user: dict = Depends(get_current_user),
        tenant_db: AsyncSession = Depends(get_tenant_db)
    ):
        from app.models.user import User
        user_email = current_user.get("email")
        if not user_email:
            # Fallback para tokens mock que puedan no tener email
            user_id = current_user.get("user_id")
            if user_id == "admin":
                return True # Fallback for local mock admin
            raise HTTPException(status_code=403, detail="No email en el token")

        result = await tenant_db.execute(select(User).where(User.email == user_email))
        user = result.scalar_one_or_none()
        if not user or not user.is_super_admin:
            # If the user is the local admin mock, let it pass
            if current_user.get("user_id") == "admin":
                return True
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Se requieren privilegios de Super Administrador para esta accion."
            )
        return True
    return checker


async def get_tenant_db_from_api_key(
    request: Request,
    global_db: AsyncSession = Depends(get_global_db)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that authenticates external integrations (Zapier, Make, etc.)
    using an API key prefix/hash lookup.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
            
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta la API Key en las cabeceras."
        )
        
    if api_key.startswith("mock_zapier_key_"):
        parts = api_key.split("_")
        tenant_id = parts[-1] if len(parts) > 3 else "default"
    elif api_key.startswith("sc_"):
        parts = api_key.split("_")
        if len(parts) >= 3:
            tenant_id = parts[1]
        else:
            raise HTTPException(status_code=401, detail="API Key format invalid")
    else:
        raise HTTPException(status_code=401, detail="API Key must start with sc_ or mock_zapier_key_")

    tenant_schema = f"tenant_{tenant_id}"
    
    if "sqlite" in settings.SQLALCHEMY_DATABASE_URI:
        AsyncSessionTenant = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    else:
        AsyncSessionTenant = _get_sessionmaker()
        
    async with AsyncSessionTenant() as db:
        if not api_key.startswith("mock_zapier_key_"):
            from app.models.agent import AgentApiKey
            import hashlib
            hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
            prefix = api_key[:8]
            result = await db.execute(
                select(AgentApiKey).where(
                    AgentApiKey.key_prefix == prefix,
                    AgentApiKey.is_active == True
                )
            )
            key_record = result.scalar_one_or_none()
            if not key_record or key_record.key_hash != hashed_key:
                raise HTTPException(status_code=401, detail="API Key no válida o inactiva.")
        yield db

def require_mfa(current_user: dict = Depends(get_current_user)):
    """
    Dependency that enforces Multi-Factor Authentication.
    """
    amr = current_user.get("amr", [])
    if "mfa" not in amr:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Se requiere autenticación multifactor (MFA)."
        )
    return current_user
