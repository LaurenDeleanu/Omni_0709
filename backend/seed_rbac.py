import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text
from app.core.config import settings
from app.models.rbac import Permission, Role, RolePermission
import uuid

PERMISSIONS = [
    {"module": "users", "action": "read", "description": "Ver directorio de empleados"},
    {"module": "users", "action": "write", "description": "Modificar empleados"},
    {"module": "admin", "action": "manage", "description": "Administrar módulos y configuración global"},
    {"module": "it", "action": "read", "description": "Ver incidencias de IT"},
    {"module": "it", "action": "write", "description": "Gestionar tickets e inventario IT"},
    {"module": "finance", "action": "read", "description": "Ver resumen financiero"},
    {"module": "finance", "action": "write", "description": "Aprobar gastos y nóminas"},
    {"module": "training", "action": "manage", "description": "Asignar cursos y ver progreso"}
]

async def seed_permissions():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    engine = create_async_engine(dsn, echo=False)
    
    # In this system, tenant DB tables are in a schema named tenant_acme_corp for the default tenant.
    # We will insert standard permissions into tenant_acme_corp.permissions if they don't exist.
    
    async with AsyncSession(engine) as session:
        # Switch schema to the default tenant
        await session.execute(text("SET search_path TO tenant_acme_corp"))
        
    async with AsyncSession(engine) as session:
        # Switch schema to the default tenant
        await session.execute(text("SET search_path TO tenant_acme_corp"))
        
        print("Recreating RBAC tables...")
        await session.execute(text("DROP TABLE IF EXISTS role_permissions CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS permissions CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS roles CASCADE"))
        
        await session.commit()
        
    async with engine.begin() as conn:
        await conn.execute(text("SET search_path TO tenant_acme_corp"))
        await conn.run_sync(Permission.metadata.create_all)
        
    async with AsyncSession(engine) as session:
        await session.execute(text("SET search_path TO tenant_acme_corp"))
        print("Seeding Permissions...")
        for p_data in PERMISSIONS:
            result = await session.execute(
                select(Permission).where(
                    Permission.module == p_data["module"], 
                    Permission.action == p_data["action"]
                )
            )
            existing = result.scalar_one_or_none()
            if not existing:
                new_perm = Permission(
                    id=uuid.uuid4().hex,
                    module=p_data["module"],
                    action=p_data["action"],
                    description=p_data["description"]
                )
                session.add(new_perm)
        
        await session.commit()
        
        # 2. Ensure default roles exist ("employee", "hr_admin", "it_manager", "finance_manager")
        print("Ensuring Default Roles exist...")
        
        default_roles = [
            {"id": "employee", "name": "Empleado (Estándar)", "is_system": True},
            {"id": "hr_admin", "name": "Administrador HR", "is_system": True},
            {"id": "it_manager", "name": "IT Manager (Soporte)", "is_system": True},
            {"id": "finance_manager", "name": "Finance Manager (Gastos)", "is_system": True}
        ]
        
        for role_data in default_roles:
            res = await session.execute(select(Role).where(Role.id == role_data["id"]))
            existing_role = res.scalar_one_or_none()
            if not existing_role:
                new_role = Role(
                    id=role_data["id"],
                    name=role_data["name"],
                    description=f"Rol de sistema: {role_data['name']}",
                    is_system_default=role_data["is_system"]
                )
                session.add(new_role)
                
        await session.commit()
        
        # 3. Grant basic permissions to HR admin as an example
        print("Granting HR admin all permissions...")
        res_hr = await session.execute(select(Role).where(Role.id == "hr_admin"))
        hr_role = res_hr.scalar_one()
        
        all_perms_res = await session.execute(select(Permission))
        all_perms = all_perms_res.scalars().all()
        
        for perm in all_perms:
            check_rp = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == hr_role.id,
                    RolePermission.permission_id == perm.id
                )
            )
            if not check_rp.scalar_one_or_none():
                rp = RolePermission(id=uuid.uuid4().hex, role_id=hr_role.id, permission_id=perm.id)
                session.add(rp)
                
        await session.commit()
        print("Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(seed_permissions())
