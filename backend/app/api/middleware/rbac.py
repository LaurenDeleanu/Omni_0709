"""
RBAC Permission Enforcement Middleware
──────────────────────────────────────
Provides a reusable FastAPI dependency that checks if the current user
has the required module-level permission for an endpoint.

Usage in a router:
    from app.api.middleware.rbac import require_permission

    @router.post("/pay/cycles", dependencies=[Depends(require_permission("payroll", "write"))])
    async def create_cycle(...): ...
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_user, get_tenant_db
from app.core.config import settings
from app.core.logger import logger
from app.models.user import User
from app.models.rbac import Role, RolePermission, Permission


def require_permission(module: str, action: str):
    async def checker(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_tenant_db),
    ):
        user_roles = current_user.get("https://successcore.com/roles", [])
        if not user_roles:
            user_roles = current_user.get("roles", [])
        if not user_roles and settings.DEBUG_MODE:
            logger.warning("[rbac] DEBUG_MODE: granting hr_admin role to token with no roles")
            user_roles = ["hr_admin"]
        if not user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token invalido: no contiene roles de acceso. Contacta al administrador."
            )

        if "hr_admin" in user_roles or "super_admin" in user_roles:
            return current_user

        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No se pudo verificar la identidad del usuario."
            )

        result = await db.execute(select(User).where(User.email == user_email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no encontrado en el directorio."
            )

        # Super admin flag on user model
        if user.is_super_admin:
            return current_user

        # ── 3. Check role permissions ─────────────────────────────────────────
        if not user.role_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes un rol asignado. Se requiere permiso '{module}:{action}'."
            )

        # Query: user.role_id → RolePermission → Permission
        result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id == user.role_id,
                Permission.module == module,
                Permission.action == action,
            )
        )
        permission = result.scalar_one_or_none()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso '{module}:{action}' para realizar esta acción."
            )

        return current_user

    return checker
