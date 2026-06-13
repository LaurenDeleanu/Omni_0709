from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.api.dependencies import get_tenant_db, require_roles
from app.models.rbac import Role, Permission, RolePermission
from app.models.user import User
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, PermissionResponse
import uuid

router = APIRouter()

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["super_admin"]))
):
    """List all available system permissions."""
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.action))
    return result.scalars().all()


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["super_admin", "hr_admin"]))
):
    """List all roles with their assigned permissions."""
    query = select(Role).options(
        selectinload(Role.permissions).selectinload(RolePermission.permission)
    ).order_by(Role.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["super_admin"]))
):
    """Create a new custom role with permissions."""
    # Create the role
    role = Role(
        id=uuid.uuid4().hex,
        name=role_in.name,
        description=role_in.description,
        is_system_default=False
    )
    db.add(role)

    # Add permissions if any
    for perm_id in role_in.permission_ids:
        # Verify permission exists
        perm_res = await db.execute(select(Permission).where(Permission.id == perm_id))
        if perm_res.scalar_one_or_none():
            rp = RolePermission(
                id=uuid.uuid4().hex,
                role_id=role.id,
                permission_id=perm_id
            )
            db.add(rp)

    await db.commit()
    
    # Reload with relationships
    query = select(Role).options(
        selectinload(Role.permissions).selectinload(RolePermission.permission)
    ).where(Role.id == role.id)
    result = await db.execute(query)
    return result.scalar_one()


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["super_admin"]))
):
    """Update an existing role and its permissions."""
    query = select(Role).options(
        selectinload(Role.permissions)
    ).where(Role.id == role_id)
    result = await db.execute(query)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    # Update basic fields if provided
    if role_in.name is not None:
        role.name = role_in.name
    if role_in.description is not None:
        role.description = role_in.description

    # Update permissions if provided
    if role_in.permission_ids is not None:
        # Delete existing permissions
        for rp in role.permissions:
            await db.delete(rp)
        
        # Add new permissions
        for perm_id in role_in.permission_ids:
            perm_res = await db.execute(select(Permission).where(Permission.id == perm_id))
            if perm_res.scalar_one_or_none():
                new_rp = RolePermission(
                    id=uuid.uuid4().hex,
                    role_id=role.id,
                    permission_id=perm_id
                )
                db.add(new_rp)

    await db.commit()
    
    # Reload with relationships
    query = select(Role).options(
        selectinload(Role.permissions).selectinload(RolePermission.permission)
    ).where(Role.id == role.id)
    result = await db.execute(query)
    return result.scalar_one()


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["super_admin"]))
):
    """Delete a custom role."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    if role.is_system_default:
        raise HTTPException(status_code=400, detail="No se pueden eliminar los roles por defecto del sistema")

    # Check if users are assigned to this role
    user_res = await db.execute(select(User).where(User.role_id == role_id))
    if user_res.first():
        raise HTTPException(status_code=400, detail="No se puede eliminar el rol porque tiene usuarios asignados. Reasígnelos primero.")

    await db.delete(role)
    await db.commit()
    return None
