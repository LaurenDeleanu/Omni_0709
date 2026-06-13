from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.employee_history import EmployeeHistory
from app.models.user import User
from app.schemas.employee_history import HistoryCreate, HistoryResponse, HistoryUpdate
from app.services.org_chart import get_cached_org_chart
from app.services.span_control import get_span_of_control
from app.services.social_profiles import get_employee_social_profile
from app.services.coffee_roulette import generate_coffee_pairings
from app.services.activity_feed import get_activity_feed
from app.services.custom_fields import set_custom_field, delete_custom_field
from app.services.department_analytics import get_department_analytics
import uuid

router = APIRouter()


@router.get("/org-chart")
async def get_org_chart(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id", "acme_corp")
    return await get_cached_org_chart(db, tenant_id)


@router.get("/span-of-control")
async def get_span_of_control_route(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_span_of_control(db)


@router.get("/profile/{user_id}")
async def get_employee_profile(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin"]))
):
    try:
        return await get_employee_social_profile(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/activity-feed")
async def get_activity_feed_endpoint(
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin"]))
):
    return {"events": await get_activity_feed(db, limit)}


@router.post("/coffee-roulette")
async def trigger_coffee_roulette(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    return await generate_coffee_pairings(db)


@router.get("/filter")
async def advanced_filter_employees(
    department: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    contract_type: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    min_salary: Optional[float] = Query(None),
    max_salary: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    stmt = select(User)
    if department:
        stmt = stmt.where(User.department == department)
    if role:
        stmt = stmt.where(User.role == role)
    if contract_type:
        stmt = stmt.where(User.contract_type == contract_type)
    if country:
        stmt = stmt.where(User.country == country)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if min_salary is not None:
        stmt = stmt.where(User.base_salary >= min_salary)
    if max_salary is not None:
        stmt = stmt.where(User.base_salary <= max_salary)
    if search:
        stmt = stmt.where(User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    stmt = stmt.order_by(User.full_name.asc()).limit(200)

    result = await db.execute(stmt)
    users = result.scalars().all()

    from app.services.data_masking import mask_data
    user_roles = _.get("https://successcore.com/roles", []) or _.get("roles", [])
    user_email = _.get("email", "")

    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "department": u.department,
             "role": u.role, "contract_type": u.contract_type, "country": u.country,
             "is_active": u.is_active, "hire_date": u.hire_date.isoformat() if u.hire_date else None}
            for u in users]


@router.put("/{user_id}/custom-fields/{field_name}")
async def set_custom_field_endpoint(
    user_id: str,
    field_name: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    try:
        return await set_custom_field(db, user_id, field_name, body.get("value"))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{user_id}/custom-fields/{field_name}")
async def delete_custom_field_endpoint(
    user_id: str,
    field_name: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    try:
        return await delete_custom_field(db, user_id, field_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/history", response_model=List[HistoryResponse])
async def get_employee_history(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Obtener el historial laboral completo de un empleado (US 6.1)."""
    # Verificar que el empleado existe
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    result = await db.execute(
        select(EmployeeHistory)
        .where(EmployeeHistory.user_id == user_id)
        .order_by(EmployeeHistory.start_date.desc())
    )
    return result.scalars().all()


@router.post("/{user_id}/history", response_model=HistoryResponse, status_code=status.HTTP_201_CREATED)
async def add_history_entry(
    user_id: str,
    entry_in: HistoryCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Añadir una nueva entrada al historial laboral de un empleado (US 6.1)."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    entry = EmployeeHistory(
        id=uuid.uuid4().hex,
        user_id=user_id,
        **entry_in.model_dump()
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.put("/{user_id}/history/{entry_id}", response_model=HistoryResponse)
async def update_history_entry(
    user_id: str,
    entry_id: str,
    entry_in: HistoryUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Actualizar una entrada del historial (ej: añadir fecha de fin al salir de un puesto)."""
    result = await db.execute(
        select(EmployeeHistory).where(
            EmployeeHistory.id == entry_id,
            EmployeeHistory.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")

    for field, value in entry_in.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{user_id}/history/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history_entry(
    user_id: str,
    entry_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar una entrada del historial."""
    result = await db.execute(
        select(EmployeeHistory).where(
            EmployeeHistory.id == entry_id,
            EmployeeHistory.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")

    await db.delete(entry)
    await db.commit()
    return None
