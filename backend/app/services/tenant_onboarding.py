"""
Onboarding automatizado para nuevos tenants (Phase 1 — P0)
===========================================================
Proporciona flujos de onboarding automáticos cuando se crea un nuevo tenant:
- Creación de roles y permisos por defecto
- Configuración inicial de agentes
- Datos semilla (departamentos, políticas)
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrador del tenant con acceso completo a todos los módulos",
        "permissions": ["*"],
    },
    {
        "name": "hr_manager",
        "description": "Gestor de RRHH con acceso a empleados, nóminas y reportes",
        "permissions": [
            "users:read", "users:write",
            "employees:read", "employees:write",
            "pay:read", "pay:write",
            "reports:read", "reports:write",
            "calendar:read", "calendar:write",
            "grow:read", "grow:write",
            "training:read", "training:write",
            "hire:read", "hire:write",
            "chat:read", "chat:write",
            "notifications:read",
        ],
    },
    {
        "name": "manager",
        "description": "Manager de equipo con acceso a su equipo directo",
        "permissions": [
            "users:read",
            "employees:read",
            "pay:read",
            "calendar:read", "calendar:write",
            "grow:read",
            "chat:read", "chat:write",
            "notifications:read",
        ],
    },
    {
        "name": "employee",
        "description": "Empleado estándar con acceso de autoservicio",
        "permissions": [
            "users:read:self",
            "pay:read:self",
            "calendar:read:self", "calendar:write:self",
            "training:read:self",
            "chat:read", "chat:write",
            "notifications:read",
        ],
    },
]

DEFAULT_DEPARTMENTS = [
    {"name": "Dirección", "code": "DIR"},
    {"name": "Recursos Humanos", "code": "RRHH"},
    {"name": "Finanzas", "code": "FIN"},
    {"name": "IT", "code": "IT"},
    {"name": "Ventas", "code": "SALES"},
    {"name": "Marketing", "code": "MKT"},
    {"name": "Operaciones", "code": "OPS"},
    {"name": "Legal", "code": "LEGAL"},
    {"name": "Ingeniería", "code": "ENG"},
    {"name": "Soporte", "code": "SUP"},
]

DEFAULT_AGENTS = [
    {
        "name": "Copiloto de Plataforma",
        "avatar": "🤖",
        "agent_type": "COPILOT",
        "ai_model": "gpt-4o-mini",
        "ai_temperature": 0.2,
        "ai_tone": "Profesional y resolutivo",
        "ai_system_prompt": (
            "Eres el Copiloto de Plataforma de SuccessCore. Tu objetivo es ayudar al usuario "
            "a interactuar con la plataforma utilizando las herramientas disponibles. "
            "Responde en español, sé conciso y profesional."
        ),
    },
    {
        "name": "HR Assistant Pro",
        "avatar": "👥",
        "agent_type": "CONVERSATIONAL",
        "ai_model": "gpt-4o",
        "ai_temperature": 0.3,
        "ai_tone": "Profesional y empático",
        "ai_system_prompt": (
            "Eres un asistente de RRHH para SuccessCore. Ayudas a managers y empleados "
            "con consultas sobre personas: perfiles de empleados, organigramas, estadísticas "
            "de departamento, saldos de vacaciones y anuncios de empresa."
        ),
    },
    {
        "name": "Payroll Specialist",
        "avatar": "💰",
        "agent_type": "CONVERSATIONAL",
        "ai_model": "gpt-4o",
        "ai_temperature": 0.1,
        "ai_tone": "Preciso y meticuloso",
        "ai_system_prompt": (
            "Eres un especialista en nóminas para SuccessCore. Procesas nóminas, "
            "gestionas reglas fiscales, creas bonificaciones y ayudas con preguntas "
            "de compensación. Operas con precisión extrema — los cálculos financieros "
            "deben ser exactos. Siempre muestra los cálculos paso a paso."
        ),
    },
    {
        "name": "IT Helpdesk",
        "avatar": "🔧",
        "agent_type": "CONVERSATIONAL",
        "ai_model": "gpt-4o-mini",
        "ai_temperature": 0.2,
        "ai_tone": "Técnico pero accesible",
        "ai_system_prompt": (
            "Eres un agente de helpdesk IT para SuccessCore. Creas y gestionas tickets "
            "de IT, buscas en la base de conocimiento, sugieres soluciones y ayudas "
            "a empleados con problemas técnicos. Escala problemas complejos al equipo IT humano."
        ),
    },
    {
        "name": "Recruiter Pro",
        "avatar": "🎯",
        "agent_type": "CONVERSATIONAL",
        "ai_model": "gpt-4o",
        "ai_temperature": 0.4,
        "ai_tone": "Profesional y objetivo",
        "ai_system_prompt": (
            "Eres un especialista en reclutamiento para SuccessCore. Gestionas el pipeline "
            "completo de contratación: ofertas de trabajo, cribado de candidatos (con IA), "
            "programación de entrevistas y promoción de candidatos a empleados."
        ),
    },
]


async def provision_tenant_onboarding(
    tenant_id: str,
    db: AsyncSession,
    admin_email: str = "",
    company_name: str = "",
) -> Dict[str, Any]:
    """
    Provision automatic onboarding resources for a new tenant.
    Creates default roles, departments, and agents.
    """
    results = {
        "tenant_id": tenant_id,
        "roles_created": 0,
        "departments_created": 0,
        "agents_created": 0,
        "errors": [],
    }

    try:
        # Create default roles
        from sqlalchemy import select
        from app.models.rbac import Role, Permission, RolePermission

        for role_data in DEFAULT_ROLES:
            try:
                existing = await db.execute(
                    select(Role).where(Role.name == role_data["name"], Role.tenant_id == tenant_id)
                )
                if existing.scalar_one_or_none():
                    continue

                role = Role(
                    tenant_id=tenant_id,
                    name=role_data["name"],
                    description=role_data["description"],
                )
                db.add(role)
                await db.flush()

                # Role.permissions es una relación a RolePermission, no una lista de
                # strings: cada "modulo:accion" se materializa como fila Permission
                # (find-or-create) + su enlace RolePermission, igual que en admin.py.
                for perm_str in role_data["permissions"]:
                    module, _, action = perm_str.partition(":")
                    action = action or "*"
                    result = await db.execute(
                        select(Permission).where(
                            Permission.module == module,
                            Permission.action == action,
                            Permission.tenant_id == tenant_id,
                        )
                    )
                    perm = result.scalar_one_or_none()
                    if not perm:
                        perm = Permission(tenant_id=tenant_id, module=module, action=action)
                        db.add(perm)
                        await db.flush()
                    db.add(RolePermission(tenant_id=tenant_id, role_id=role.id, permission_id=perm.id))

                results["roles_created"] += 1
            except Exception as e:
                results["errors"].append(f"Role '{role_data['name']}': {str(e)}")

        await db.flush()

        # Create default departments
        # Los departamentos se guardan como entradas de PageMetadata (BD por tenant)
        from app.models.metadata import PageMetadata

        for dept_data in DEFAULT_DEPARTMENTS:
            try:
                # (module_name, page_name) es UNIQUE: reejecutar el onboarding
                # no debe duplicar ni abortar.
                existing = await db.execute(
                    select(PageMetadata).where(
                        PageMetadata.module_name == "departments",
                        PageMetadata.page_name == dept_data["code"],
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                dept = PageMetadata(
                    tenant_id=tenant_id,
                    module_name="departments",
                    page_name=dept_data["code"],
                    description=dept_data["name"],
                    schema_data={"code": dept_data["code"], "name": dept_data["name"], "category": "department"},
                )
                db.add(dept)
                results["departments_created"] += 1
            except Exception as e:
                results["errors"].append(f"Department '{dept_data['name']}': {str(e)}")

        await db.flush()

        # Create default agents
        from app.models.agent import Agent, AgentConfig

        for agent_data in DEFAULT_AGENTS:
            try:
                agent_name = f"{agent_data['name']} ({company_name or tenant_id})"
                existing = await db.execute(
                    select(Agent).where(Agent.name == agent_name, Agent.tenant_id == tenant_id)
                )
                if existing.scalar_one_or_none():
                    continue

                agent = Agent(
                    tenant_id=tenant_id,
                    name=agent_name,
                    avatar=agent_data["avatar"],
                    agent_type=agent_data["agent_type"],
                    ai_model=agent_data["ai_model"],
                    ai_system_prompt=agent_data["ai_system_prompt"],
                    ai_temperature=agent_data["ai_temperature"],
                    ai_tone=agent_data["ai_tone"],
                    is_active=True,
                )
                db.add(agent)
                await db.flush()

                config = AgentConfig(
                    tenant_id=tenant_id,
                    agent_id=agent.id,
                    max_loops=10,
                    max_tokens_per_run=50000,
                )
                db.add(config)
                results["agents_created"] += 1
            except Exception as e:
                results["errors"].append(f"Agent '{agent_data['name']}': {str(e)}")

        await db.commit()

        logger.info(
            f"Tenant '{tenant_id}' onboarded: {results['roles_created']} roles, "
            f"{results['departments_created']} departments, {results['agents_created']} agents"
        )

    except Exception as e:
        await db.rollback()
        results["errors"].append(f"Onboarding failed: {str(e)}")
        logger.error(f"Onboarding failed for tenant '{tenant_id}': {e}")

    return results


async def get_onboarding_status(
    tenant_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Check the onboarding status for a given tenant."""
    from app.models.rbac import Role
    from app.models.agent import Agent
    from sqlalchemy import select, func

    role_count = await db.scalar(
        select(func.count()).select_from(Role).where(Role.tenant_id == tenant_id)
    )
    agent_count = await db.scalar(
        select(func.count()).select_from(Agent).where(Agent.tenant_id == tenant_id)
    )

    return {
        "tenant_id": tenant_id,
        "roles": role_count or 0,
        "agents": agent_count or 0,
        "is_onboarded": (role_count or 0) >= 2 and (agent_count or 0) >= 1,
    }
