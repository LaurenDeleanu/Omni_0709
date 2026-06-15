from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.api.v1._pagination import paginate_query
from app.schemas.pagination import PaginatedResponse
from app.api.middleware.csrf import CSRFTokenManager
from app.services.data_masking import mask_data, mask_list
from app.services.session_manager import register_session, list_sessions, revoke_session
from app.services.password_policy import validate_password
from app.services.event_sourcing import publish_event
from app.models.user import User, ProfileChangeRequest
from app.schemas.user import UserCreate, UserResponse, UserUpdate, ProfileUpdateInput, ProfileChangeRequestResponse, ProfileChangeRequestReview
from app.models.push import PushSubscription
import uuid
import re
from pydantic import BaseModel, EmailStr, field_validator
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.auth import verify_password, hash_password
from app.core.logger import logger

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
csrf_manager = CSRFTokenManager()


@router.get("/csrf-token")
async def get_csrf_token(request: Request):
    token = csrf_manager.get_or_create_token(request)
    return {"csrf_token": token}


@router.get("/sessions")
async def get_my_sessions(
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub", "").split("|")[-1]
    user_email = current_user.get("email", "")
    sessions = list_sessions(user_id=user_id, user_email=user_email)
    return {"sessions": sessions, "count": len(sessions)}


@router.delete("/sessions/{session_jti}")
async def revoke_my_session(
    session_jti: str,
    current_user: dict = Depends(get_current_user),
):
    revoked = revoke_session(session_jti)
    if not revoked:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "revoked", "jti": session_jti}


def _validate_password_strength(password: str) -> str:
    if not password:
        raise ValueError("Password is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 72:
        raise ValueError("Password must not exceed 72 characters")

    valid, errors = validate_password(password)
    if not valid:
        raise ValueError("Password policy: " + "; ".join(errors))

    return password


@router.get("", dependencies=[Depends(require_roles(["hr_admin", "employee"]))])
async def get_users(
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(User.full_name.asc())

    if page is not None:
        result = await paginate_query(db, stmt, page=page, page_size=page_size)
        user_roles = current_user.get("https://successcore.com/roles", []) or current_user.get("roles", [])
        user_email = current_user.get("email", "")
        items = [mask_data(_user_to_dict(item), user_roles, user_email) for item in result["items"]]
        return PaginatedResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"], total_pages=result["total_pages"])

    exec_result = await db.execute(stmt)
    users = exec_result.scalars().all()
    user_roles = current_user.get("https://successcore.com/roles", []) or current_user.get("roles", [])
    user_email = current_user.get("email", "")
    return [mask_data(_user_to_dict(u), user_roles, user_email) for u in users]


def _user_to_dict(u: User) -> dict:
    return {c.name: getattr(u, c.name) for c in u.__table__.columns}


# ── Profile Self-Service & Approval requests ───────────────────────────────────

@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    profile_in: ProfileUpdateInput,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualiza el perfil del usuario actual.
    - Teléfono y Contacto de Emergencia se actualizan directamente.
    - Dirección e IBAN crean solicitudes de cambio pendientes de aprobación por RRHH.
    """
    sub = current_user.get("sub", "unknown")
    user_id = sub.split("|")[-1] if "|" in sub else sub
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # Campos no sensibles (Edición Directa)
    if profile_in.phone_number is not None:
        user.phone_number = profile_in.phone_number
    if profile_in.emergency_contact is not None:
        user.emergency_contact = profile_in.emergency_contact
        
    # Campos sensibles (Crean solicitudes de aprobación)
    if profile_in.address is not None and profile_in.address != user.address:
        # Validar si ya hay una solicitud pendiente idéntica para evitar spam
        existing_req = await db.execute(
            select(ProfileChangeRequest).where(
                ProfileChangeRequest.user_id == user.id,
                ProfileChangeRequest.field_name == "address",
                ProfileChangeRequest.status == "pending"
            )
        )
        old_req = existing_req.scalar_one_or_none()
        if old_req:
            old_req.new_value = profile_in.address
        else:
            req = ProfileChangeRequest(
                id=uuid.uuid4().hex,
                user_id=user.id,
                field_name="address",
                old_value=user.address,
                new_value=profile_in.address,
                status="pending"
            )
            db.add(req)
            
    if profile_in.iban is not None and profile_in.iban != user.iban:
        existing_req = await db.execute(
            select(ProfileChangeRequest).where(
                ProfileChangeRequest.user_id == user.id,
                ProfileChangeRequest.field_name == "iban",
                ProfileChangeRequest.status == "pending"
            )
        )
        old_req = existing_req.scalar_one_or_none()
        if old_req:
            old_req.new_value = profile_in.iban
        else:
            req = ProfileChangeRequest(
                id=uuid.uuid4().hex,
                user_id=user.id,
                field_name="iban",
                old_value=user.iban,
                new_value=profile_in.iban,
                status="pending"
            )
            db.add(req)
            
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/profile-requests", response_model=List[ProfileChangeRequestResponse], dependencies=[Depends(require_roles(["hr_admin", "super_admin"]))])
async def list_profile_requests(
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Lista las solicitudes de cambios en perfiles pendientes de aprobación (Solo HR/Super Admin).
    """
    result = await db.execute(
        select(ProfileChangeRequest).order_by(ProfileChangeRequest.requested_at.desc())
    )
    return result.scalars().all()


@router.post("/profile-requests/{request_id}/review", dependencies=[Depends(require_roles(["hr_admin", "super_admin"]))])
async def review_profile_request(
    request_id: str,
    review: ProfileChangeRequestReview,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Aprueba o rechaza una solicitud de cambio de perfil.
    Si se aprueba, actualiza el campo del usuario en base de datos.
    """
    sub = current_user.get("sub", "unknown")
    admin_id = sub.split("|")[-1] if "|" in sub else sub

    result = await db.execute(
        select(ProfileChangeRequest).where(ProfileChangeRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud de cambio no encontrada")
        
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Esta solicitud ya ha sido procesada")
        
    req.status = "approved" if review.approved else "rejected"
    req.reviewed_at = datetime.now(timezone.utc)
    req.reviewed_by = admin_id
    
    if review.approved:
        # Buscar usuario y aplicar el cambio en base de datos
        user_result = await db.execute(select(User).where(User.id == req.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            setattr(user, req.field_name, req.new_value)
            
    await db.commit()
    return {"message": f"Solicitud procesada con estado: {req.status}"}


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtiene el perfil del usuario autenticado actual."""
    sub = current_user.get("sub", "unknown")
    user_id = sub.split("|")[-1] if "|" in sub else sub
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.get("/me/hub")
async def get_my_hub(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    sub = current_user.get("sub", "unknown")
    user_id = sub.split("|")[-1] if "|" in sub else sub

    from app.services.self_service import get_employee_hub
    hub = await get_employee_hub(user_id, db)
    return hub


@router.post("/logout")
async def logout():
    """[C3] Clears the httpOnly access_token cookie, terminating the browser session."""
    response = Response(content='{"message": "Sesión cerrada exitosamente."}', media_type="application/json")
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"),
        samesite="none"
    )
    return response


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_roles(["hr_admin", "employee"]))])
async def get_user(user_id: str, db: AsyncSession = Depends(get_tenant_db)):
    """Obtener un empleado por su ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["hr_admin", "super_admin"]))])
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_tenant_db)):
    """Crear un nuevo empleado con contraseña (HR Admin y Super Admin)."""
    # [C6] Validate password strength if provided
    if getattr(user_in, 'password', None):
        try:
            _validate_password_strength(user_in.password)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    create_data = user_in.model_dump(exclude={"password"})
    new_user = User(
        id=uuid.uuid4().hex,
        hashed_password=hash_password(user_in.password) if getattr(user_in, 'password', None) else None,
        **create_data
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"[create_user] IntegrityError: {e.orig}")
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")
    except Exception as e:
        await db.rollback()
        logger.error(f"[create_user] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al crear el empleado.")

    try:
        publish_event("employee.created", {
            "user_id": new_user.id, "email": new_user.email,
            "full_name": new_user.full_name or "", "department": new_user.department or "",
            "role": new_user.role, "hire_date": new_user.hire_date.isoformat() if new_user.hire_date else None
        }, tenant_id="acme_corp")
    except Exception:
        pass

    try:
        from app.core.task_queue import enqueue
        await enqueue(
            "onboarding_setup",
            args={"employee_id": new_user.id, "user_id": new_user.id},
            tenant_id="acme_corp",
        )
    except Exception:
        pass

    return new_user


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_roles(["hr_admin"]))])
async def update_user(user_id: str, user_in: UserUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    old_salary = getattr(user, 'base_salary', 0)
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    if "base_salary" in update_data:
        try:
            publish_event("salary.changed", {
                "user_id": user.id, "old_salary": old_salary, "new_salary": update_data["base_salary"]
            }, tenant_id="acme_corp")
        except Exception:
            pass
    try:
        publish_event("employee.updated", {
            "user_id": user.id, "changed_fields": list(update_data.keys())
        }, tenant_id="acme_corp")
    except Exception:
        pass
    return user


@router.patch("/{user_id}/archive", response_model=UserResponse, dependencies=[Depends(require_roles(["hr_admin"]))])
async def archive_user(user_id: str, db: AsyncSession = Depends(get_tenant_db)):
    """Archivar un empleado (soft-delete: is_active=False). Preserva historial."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    try:
        from app.services.event_publisher import publish_employee_archived
        publish_employee_archived(user.id, user.email or "")
    except Exception:
        pass

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["hr_admin"]))])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_tenant_db)):
    """Eliminar permanentemente un empleado (solo HR Admin)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await db.delete(user)
    await db.commit()
    try:
        publish_event("employee.deleted", {
            "user_id": str(user_id), "email": user.email or ""
        }, tenant_id="acme_corp")
    except Exception:
        pass
    return None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None

    @field_validator("tenant_id")
    @classmethod
    def tenant_id_required(cls, v: Optional[str]) -> str:
        """[C2] tenant_id is required at login to route to the correct schema."""
        if not v or not v.strip():
            raise ValueError("El campo tenant_id es obligatorio para el inicio de sesión.")
        if not re.match(r'^[a-zA-Z0-9_]{1,50}$', v):
            raise ValueError("tenant_id inválido: solo letras, números y guiones bajos.")
        return v


@router.post("/login", response_model=dict)
@limiter.limit("5/minute")  # [M12] IP-based rate limit
async def login_local(req: LoginRequest, request: Request):
    from app.services.login_guard import check_login_allowed, record_login_attempt, clear_login_attempts

    client_ip = request.client.host if request.client else "unknown"
    allowed, block_msg = await check_login_allowed(req.email, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=block_msg,
        )

    is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI
    
    tenant_id = req.tenant_id
    tenant_schema = f"tenant_{tenant_id}"
    
    from app.core.database import engine
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    if is_sqlite:
        tenant_engine = engine
    else:
        tenant_engine = engine.execution_options(schema_translate_map={None: tenant_schema})
    
    AsyncSessionTenant = async_sessionmaker(
        bind=tenant_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    
    async with AsyncSessionTenant() as db:
        result = await db.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()
        
        if not user:
            await record_login_attempt(req.email, client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos."
            )
            
        if not user.is_active:
            await record_login_attempt(req.email, client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta de usuario está desactivada."
            )

        if not user.hashed_password:
            await record_login_attempt(req.email, client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Esta cuenta no tiene una contraseña configurada. Solicita un enlace de acceso al administrador."
            )
            
        if not verify_password(req.password, user.hashed_password):
            await record_login_attempt(req.email, client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos."
            )
        
        await clear_login_attempts(req.email, client_ip)
            
        token_payload = {
            "sub": f"local|{user.id}",
            "email": user.email,
            "name": user.full_name or user.email,
            "tenant_id": tenant_id,
            "jti": str(uuid.uuid4()),
            "roles": [user.role],
            "https://successcore.com/app_metadata": {
                "tenant_id": tenant_id,
                "roles": [user.role]
            },
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "iat": datetime.now(timezone.utc)
        }
        
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        register_session(token_payload["jti"], user.email, user.id, request.client.host if request.client else "")
        
        is_production = not is_sqlite
        
        from fastapi.responses import JSONResponse
        
        response = JSONResponse(content={
            "accessToken": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": tenant_id
            }
        })
        
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=is_production,
            samesite="none" if is_production else "lax",
            max_age=7 * 24 * 3600,
            path="/",
        )
        
        return response


class ResetPasswordRequest(BaseModel):
    password: str

@router.post("/{user_id}/reset-password", dependencies=[Depends(require_roles(["hr_admin", "super_admin"]))])
async def reset_user_password(
    user_id: str,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Permite a HR Admin o Super Admin establecer/resetear la contraseña de cualquier empleado."""
    # [C6] Enforce password policy on resets too
    try:
        _validate_password_strength(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.hashed_password = hash_password(payload.password)
    await db.commit()
    return {"message": f"Contraseña actualizada para {user.email}"}


class PushSubscriptionPayload(BaseModel):
    endpoint: str
    keys: dict


@router.post("/push-subscription")
async def store_push_subscription(
    payload: PushSubscriptionPayload,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    user_id = current_user.get("sub", "").split("|")[-1]

    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == payload.endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.keys = payload.keys
    else:
        sub = PushSubscription(
            user_id=user_id,
            endpoint=payload.endpoint,
            keys=payload.keys,
        )
        db.add(sub)

    await db.commit()
    return {"status": "stored"}


@router.get("/debug-login")
async def debug_login(email: str = "admin@successcore.com", tenant_id: str = "acme_corp"):
    import traceback
    try:
        from app.core.database import engine
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.user import User
        from sqlalchemy import select

        tenant_schema = f"tenant_{tenant_id}"
        is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI
        tenant_engine = engine if is_sqlite else engine.execution_options(schema_translate_map={None: tenant_schema})

        AsyncSessionTenant = async_sessionmaker(bind=tenant_engine, class_=AsyncSession, autocommit=False, autoflush=False, expire_on_commit=False)

        async with AsyncSessionTenant() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                return {"found": True, "email": user.email, "id": user.id, "role": user.role, "is_active": user.is_active, "has_password": bool(user.hashed_password)}
            return {"found": False}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}
