"""
tax_admin.py — Admin CRUD for configurable tax brackets + sync with government APIs.
"""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_global_db, get_current_user, require_roles
from app.models.tax_bracket import TaxBracket

logger = logging.getLogger("successcore.tax_admin")
router = APIRouter(prefix="/tax/admin", tags=["Tax Administration"])


class TaxBracketCreate(BaseModel):
    country_code: str
    name: str
    description: str = ""
    currency: str = "EUR"
    tax_year: int = 2026
    brackets: list = []
    social_security_employee: float = 0
    social_security_employer: float = 0
    standard_deduction: float = 0
    personal_allowance: float = 0
    vat_rate: float = 0
    vat_reduced_rate: float = 0
    vat_food_rate: float = 0


class TaxBracketUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    brackets: Optional[list] = None
    social_security_employee: Optional[float] = None
    social_security_employer: Optional[float] = None
    standard_deduction: Optional[float] = None
    personal_allowance: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_reduced_rate: Optional[float] = None
    vat_food_rate: Optional[float] = None
    is_active: Optional[bool] = None
    tax_year: Optional[int] = None


@router.get("")
async def list_tax_brackets(
    country_code: Optional[str] = Query(default=None),
    tax_year: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(TaxBracket).order_by(TaxBracket.country_code)
    if country_code:
        query = query.where(TaxBracket.country_code == country_code.upper())
    if tax_year:
        query = query.where(TaxBracket.tax_year == tax_year)

    result = await db.execute(query)
    brackets = result.scalars().all()
    return {
        "brackets": [
            {
                "id": b.id, "country_code": b.country_code, "name": b.name,
                "description": b.description, "currency": b.currency,
                "tax_year": b.tax_year, "brackets": b.brackets,
                "social_security_employee": b.social_security_employee,
                "social_security_employer": b.social_security_employer,
                "standard_deduction": b.standard_deduction,
                "personal_allowance": b.personal_allowance,
                "vat_rate": b.vat_rate, "vat_reduced_rate": b.vat_reduced_rate,
                "vat_food_rate": b.vat_food_rate,
                "is_active": b.is_active, "is_custom": b.is_custom,
                "source": b.source, "last_synced_at": b.last_synced_at.isoformat() if b.last_synced_at else None,
            }
            for b in brackets
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tax_bracket(
    body: TaxBracketCreate,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "sys_admin"])),
):
    bracket_id = uuid.uuid4().hex
    bracket = TaxBracket(
        id=bracket_id,
        country_code=body.country_code.upper(),
        name=body.name,
        description=body.description,
        currency=body.currency,
        tax_year=body.tax_year,
        brackets=body.brackets,
        social_security_employee=body.social_security_employee,
        social_security_employer=body.social_security_employer,
        standard_deduction=body.standard_deduction,
        personal_allowance=body.personal_allowance,
        vat_rate=body.vat_rate,
        vat_reduced_rate=body.vat_reduced_rate,
        vat_food_rate=body.vat_food_rate,
        is_custom=True,
        source="manual",
    )
    db.add(bracket)
    await db.commit()
    return {"id": bracket_id, "status": "created"}


@router.put("/{bracket_id}")
async def update_tax_bracket(
    bracket_id: str,
    body: TaxBracketUpdate,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "sys_admin"])),
):
    result = await db.execute(select(TaxBracket).where(TaxBracket.id == bracket_id))
    bracket = result.scalar_one_or_none()
    if not bracket:
        raise HTTPException(status_code=404, detail="Tax bracket not found")

    for field in body.model_dump(exclude_unset=True):
        if field == "brackets" and body.brackets is not None:
            bracket.brackets = body.brackets
        elif hasattr(bracket, field):
            setattr(bracket, field, getattr(body, field))

    bracket.is_custom = True
    bracket.updated_at = datetime.now(timezone.utc)
    await db.commit()
    from app.services.tax_calculator import clear_cache
    clear_cache()
    return {"id": bracket_id, "status": "updated"}


@router.delete("/{bracket_id}")
async def delete_tax_bracket(
    bracket_id: str,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "sys_admin"])),
):
    result = await db.execute(select(TaxBracket).where(TaxBracket.id == bracket_id))
    bracket = result.scalar_one_or_none()
    if not bracket:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    await db.delete(bracket)
    await db.commit()
    from app.services.tax_calculator import clear_cache
    clear_cache()
    return {"id": bracket_id, "status": "deleted"}


@router.post("/sync")
async def sync_from_providers(
    country_code: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "sys_admin"])),
):
    """Sync tax brackets from government APIs and save to DB."""
    from app.services.tax_api_client import sync_tax_brackets_from_providers

    synced = await sync_tax_brackets_from_providers(country_code)
    count = 0
    for item in synced:
        existing = await db.execute(
            select(TaxBracket).where(
                TaxBracket.country_code == item["country_code"],
                TaxBracket.tax_year == item.get("tax_year", 2026),
            )
        )
        if existing.scalar_one_or_none():
            continue

        bracket = TaxBracket(
            id=uuid.uuid4().hex,
            country_code=item["country_code"],
            name=item.get("name", f"Tax {item['country_code']}"),
            brackets=item.get("brackets", []),
            social_security_employee=item.get("social_security_employee", 0),
            social_security_employer=item.get("social_security_employer", 0),
            personal_allowance=item.get("personal_allowance", 0),
            standard_deduction=item.get("standard_deduction", 0),
            vat_rate=item.get("vat_rate", 0),
            vat_reduced_rate=item.get("vat_reduced_rate", 0),
            vat_food_rate=item.get("vat_food_rate", 0),
            currency=item.get("currency", "EUR"),
            tax_year=item.get("tax_year", 2026),
            source=item.get("source", "api"),
            last_synced_at=datetime.now(timezone.utc),
            is_custom=False,
        )
        db.add(bracket)
        count += 1

    await db.commit()
    return {"synced": count, "countries": list(set(i["country_code"] for i in synced))}
