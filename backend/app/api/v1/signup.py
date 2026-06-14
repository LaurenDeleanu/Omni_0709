"""
signup.py — Self-service tenant signup (public endpoint).
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator

from app.api.dependencies import get_global_db
from app.core.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.core.auth import hash_password

logger = logging.getLogger("successcore.signup")

router = APIRouter(prefix="/signup", tags=["signup"])


class SignupRequest(BaseModel):
    company_name: str
    admin_email: EmailStr
    admin_password: str
    admin_name: str
    tier: str = "FREE"

    @field_validator("company_name")
    @classmethod
    def company_name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Company name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Company name must be under 100 characters")
        return v

    @field_validator("admin_password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("tier")
    @classmethod
    def tier_valid(cls, v: str) -> str:
        v = v.upper()
        if v not in ("FREE", "PRO", "ENTERPRISE"):
            raise ValueError("Tier must be FREE, PRO, or ENTERPRISE")
        return v


class ValidateRequest(BaseModel):
    company_name: str
    email: str


def _schema_name(company: str) -> str:
    import re
    base = re.sub(r"[^a-z0-9]", "", company.lower().strip())[:30]
    if not base:
        base = "tenant"
    return f"tenant_{base}"


async def _company_exists(db: AsyncSession, company_name: str) -> bool:
    result = await db.execute(
        select(Tenant.id).where(Tenant.name.ilike(company_name.strip()))
    )
    return result.scalar_one_or_none() is not None


async def _email_exists(db: AsyncSession, email: str) -> bool:
    result = await db.execute(
        select(User.id).where(User.email == email.strip().lower())
    )
    return result.scalar_one_or_none() is not None


@router.post("/validate")
async def validate_signup(body: ValidateRequest, db: AsyncSession = Depends(get_global_db)):
    if not settings.ALLOW_PUBLIC_SIGNUP:
        raise HTTPException(status_code=403, detail="Public signup is disabled")

    company_taken = await _company_exists(db, body.company_name)
    email_taken = await _email_exists(db, body.email)

    suggestions = []
    if company_taken:
        for suffix in ["HQ", "Corp", "Inc", "Ltd", "Group"]:
            alt = f"{body.company_name} {suffix}"
            if not await _company_exists(db, alt):
                suggestions.append(alt)
                if len(suggestions) >= 3:
                    break

    return {
        "available": not company_taken and not email_taken,
        "company_taken": company_taken,
        "email_taken": email_taken,
        "suggestions": suggestions,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, request: Request, db: AsyncSession = Depends(get_global_db)):
    if not settings.ALLOW_PUBLIC_SIGNUP:
        raise HTTPException(status_code=403, detail="Public signup is disabled")

    if await _company_exists(db, body.company_name):
        raise HTTPException(status_code=409, detail="Company name already registered")

    if await _email_exists(db, body.admin_email):
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant_id = uuid.uuid4().hex
    schema = _schema_name(body.company_name)

    # Ensure unique schema name
    existing = await db.execute(select(Tenant.id).where(Tenant.schema_name == schema))
    attempt = 0
    while existing.scalar_one_or_none() and attempt < 10:
        attempt += 1
        schema = f"{_schema_name(body.company_name)}{attempt}"
        existing = await db.execute(select(Tenant.id).where(Tenant.schema_name == schema))

    # Create tenant record
    tenant = Tenant(
        id=tenant_id,
        name=body.company_name.strip(),
        schema_name=schema,
        tier=body.tier,
        subscription_status="active" if body.tier == "FREE" else "pending",
        subscription_tier=None if body.tier == "FREE" else body.tier,
    )
    db.add(tenant)
    await db.flush()

    # Provision tenant schema + roles + agents
    try:
        from app.services.tenant_provisioning import provision_tenant
        await provision_tenant(db, tenant)
    except Exception as e:
        logger.warning(f"Tenant schema provisioning skipped: {e}")

    # Create admin user in the tenant schema
    user_id = uuid.uuid4().hex
    pwd_hash = hash_password(body.admin_password)
    admin_user = User(
        id=user_id,
        email=body.admin_email.strip().lower(),
        full_name=body.admin_name.strip(),
        hashed_password=pwd_hash,
        role="hr_admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(admin_user)
    await db.flush()

    # Try to auto-onboard (create defaults)
    try:
        from app.api.v1.auto_onboard import onboard_tenant
        await onboard_tenant(db, tenant)
    except Exception as e:
        logger.warning(f"Auto-onboard skipped: {e}")

    # Stripe checkout for paid tiers
    checkout_url = None
    if body.tier != "FREE" and settings.STRIPE_SECRET_KEY:
        try:
            from app.services.integrations.stripe import StripeIntegration
            checkout_url = await StripeIntegration.create_checkout_session(
                tenant_id=tenant_id,
                customer_email=body.admin_email,
                tier=body.tier,
                success_url=f"{settings.FRONTEND_URL}/dashboard",
                cancel_url=f"{settings.FRONTEND_URL}/signup",
            )
        except Exception as e:
            logger.error(f"Stripe checkout failed: {e}")

    # Send welcome email
    try:
        from app.services.email_service import send_email
        await send_email(
            to=body.admin_email,
            subject=f"Welcome to SuccessCore — {body.company_name} is ready!",
            body=f"""Hi {body.admin_name},

Your SuccessCore workspace for {body.company_name} is ready!

Login: {body.admin_email}
Tenant ID: {schema}
Tier: {body.tier}

Get started: {settings.FRONTEND_URL}/login

— The SuccessCore Team
""",
        )
    except Exception as e:
        logger.warning(f"Welcome email skipped: {e}")

    await db.commit()

    return {
        "tenant_id": tenant_id,
        "schema_name": schema,
        "admin_user_id": user_id,
        "tier": body.tier,
        "checkout_url": checkout_url,
        "message": "Tenant created successfully",
    }
