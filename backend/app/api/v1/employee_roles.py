from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from app.api.dependencies import get_tenant_db, require_roles
from app.models.user import User

router = APIRouter()

VALID_ROLES = ["employee", "hr_admin", "sys_admin", "super_admin", "manager"]


class AssignRoleRequest(BaseModel):
    role: str


@router.get("/{user_id}/roles")
async def get_employee_roles(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee"])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return {"user_id": user_id, "roles": user.roles or ["employee"]}


@router.post("/{user_id}/roles")
async def assign_employee_role(
    user_id: str,
    body: AssignRoleRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"])),
):
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol no valido. Roles validos: {', '.join(VALID_ROLES)}"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    current_roles: list = user.roles or ["employee"]
    if body.role in current_roles:
        return {"user_id": user_id, "roles": current_roles, "message": "El rol ya estaba asignado"}

    current_roles.append(body.role)
    user.roles = current_roles
    await db.commit()

    return {"user_id": user_id, "roles": current_roles, "message": f"Rol '{body.role}' asignado"}


@router.delete("/{user_id}/roles/{role}")
async def remove_employee_role(
    user_id: str,
    role: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    current_roles: list = user.roles or ["employee"]
    if role not in current_roles:
        raise HTTPException(status_code=404, detail="El empleado no tiene ese rol")

    if role == "employee" and len(current_roles) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el unico rol del empleado"
        )

    current_roles.remove(role)
    if not current_roles:
        current_roles = ["employee"]
    user.roles = current_roles
    await db.commit()

    return {"user_id": user_id, "roles": current_roles, "message": f"Rol '{role}' eliminado"}
