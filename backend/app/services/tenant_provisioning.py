import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import create_engine, text, select
from app.core.config import settings
from app.core.database import engine, AsyncSessionGlobal
from app.core.encryption import encrypt_key
from app.core.auth import hash_password
from app.models.base import Base
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

DEFAULT_MODULES = {
    "it": True, "finance": True, "training": True, "schedules": True,
    "hire": True, "work": True, "sales": True, "grow": True,
    "ops": True, "intelligence": True, "people": True,
}

DEFAULT_TABLES = [
    "users", "employee_history", "vacation_requests", "meetings", "tasks",
    "expense_claims", "time_logs", "break_logs", "work_schedules", "general_shifts",
    "journal_entries", "journal_lines", "courses", "course_enrollments", "fundae_validations",
    "hire_jobs", "hire_candidates", "hire_interviews", "pay_cycles", "pay_payslips",
    "pay_payslip_lines", "pay_tax_rules", "pay_bonuses", "legal_contracts",
    "legal_whistleblower_reports", "legal_dsar_tickets", "grow_objectives",
    "grow_key_results", "grow_reviews", "intel_dashboards", "intel_widgets",
    "intel_kpi_alerts", "projects", "work_tasks", "kanban_boards", "board_columns",
    "sprints", "wiki_pages", "clients", "leads", "ops_assets", "ops_bookings",
    "ops_visitors", "it_assets", "it_tickets", "saas_licenses", "it_requisitions",
    "notifications", "announcements", "kudos", "workflow_templates", "user_workflows",
    "agents", "agent_configs", "agent_execution_runs", "agent_triggers",
    "test_suites", "test_cases", "test_runs", "knowledge_documents", "knowledge_chunks",
    "git_repositories", "code_modules", "teams", "team_members", "chat_rooms",
    "chat_room_members", "chat_messages", "user_integrations", "push_subscriptions",
    "profile_change_requests", "audit_logs", "roles", "permissions", "role_permissions",
    "page_metadata", "scheduled_reports",
]

DEFAULT_ROLES = [
    {"id": "role_hr_admin", "name": "HR Admin", "description": "Full HR platform access", "is_system_default": True},
    {"id": "role_employee", "name": "Employee", "description": "Standard employee access", "is_system_default": True},
    {"id": "role_manager", "name": "Manager", "description": "Team management access", "is_system_default": True},
    {"id": "role_viewer", "name": "Viewer", "description": "Read-only access", "is_system_default": True},
]

DEFAULT_PERMISSIONS = [
    {"id": "perm_admin_read", "module": "admin", "action": "read", "description": "View admin panel"},
    {"id": "perm_admin_write", "module": "admin", "action": "write", "description": "Modify admin settings"},
    {"id": "perm_payroll_read", "module": "payroll", "action": "read", "description": "View payroll data"},
    {"id": "perm_payroll_write", "module": "payroll", "action": "write", "description": "Create/edit payroll"},
    {"id": "perm_legal_read", "module": "legal", "action": "read", "description": "View legal documents"},
    {"id": "perm_legal_write", "module": "legal", "action": "write", "description": "Create/edit legal documents"},
    {"id": "perm_employees_read", "module": "employees", "action": "read", "description": "View employee data"},
    {"id": "perm_employees_write", "module": "employees", "action": "write", "description": "Edit employee data"},
    {"id": "perm_finance_read", "module": "finance", "action": "read", "description": "View finance data"},
    {"id": "perm_finance_write", "module": "finance", "action": "write", "description": "Edit finance data"},
    {"id": "perm_training_read", "module": "training", "action": "read", "description": "View training data"},
    {"id": "perm_training_write", "module": "training", "action": "write", "description": "Edit training data"},
    {"id": "perm_hire_read", "module": "hire", "action": "read", "description": "View hiring data"},
    {"id": "perm_hire_write", "module": "hire", "action": "write", "description": "Edit hiring data"},
    {"id": "perm_agents_read", "module": "agents", "action": "read", "description": "View AI agents"},
    {"id": "perm_agents_write", "module": "agents", "action": "write", "description": "Create/edit AI agents"},
]

ROLE_PERMISSIONS_MAP = {
    "role_hr_admin": [p["id"] for p in DEFAULT_PERMISSIONS],
    "role_manager": ["perm_employees_read", "perm_finance_read", "perm_training_read", "perm_hire_read", "perm_agents_read"],
    "role_employee": ["perm_employees_read", "perm_agents_read"],
    "role_viewer": ["perm_employees_read"],
}


async def create_tenant_schema(schema_name: str) -> None:
    is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI
    if is_sqlite:
        logger.info(f"SQLite mode: skipping schema creation for {schema_name}")
        return

    sync_uri = settings.SYNC_DATABASE_URI
    sync_engine = create_engine(sync_uri)
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("COMMIT"))
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.execute(text("COMMIT"))
            tenant_engine = conn.engine.execution_options(schema_translate_map={None: schema_name})
            with tenant_engine.connect() as tenant_conn:
                Base.metadata.create_all(tenant_conn)
                tenant_conn.execute(text("COMMIT"))
            try:
                import subprocess
                result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info(f"Alembic migration applied to {schema_name}")
                else:
                    logger.warning(f"Alembic migration skipped for {schema_name}: {result.stderr[:200]}")
            except Exception as e:
                logger.warning(f"Alembic migration not available: {e}")
    finally:
        sync_engine.dispose()


async def seed_tenant_data(db: AsyncSession, admin_email: str, admin_password: str, admin_name: str) -> dict:
    for role in DEFAULT_ROLES:
        await db.execute(
            text("INSERT INTO roles (id, name, description, is_system_default) VALUES (:id, :name, :description, :is_default) ON CONFLICT (id) DO NOTHING"),
            role
        )

    for perm in DEFAULT_PERMISSIONS:
        await db.execute(
            text("INSERT INTO permissions (id, module, action, description) VALUES (:id, :module, :action, :description) ON CONFLICT (id) DO NOTHING"),
            perm
        )

    for role_id, perm_ids in ROLE_PERMISSIONS_MAP.items():
        for perm_id in perm_ids:
            rp_id = uuid.uuid4().hex
            await db.execute(
                text("INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :role_id, :perm_id) ON CONFLICT DO NOTHING"),
                {"id": rp_id, "role_id": role_id, "perm_id": perm_id}
            )

    admin_id = uuid.uuid4().hex
    hashed_pw = hash_password(admin_password)
    now = datetime.now(timezone.utc)
    await db.execute(
        text("""
            INSERT INTO users (id, email, full_name, department, role, role_id, is_active, is_super_admin, created_at, updated_at, password_hash)
            VALUES (:id, :email, :name, 'Administration', 'hr_admin', :role_id, true, true, :now, :now, :pw)
            ON CONFLICT (email) DO NOTHING
        """),
        {"id": admin_id, "email": admin_email, "name": admin_name, "role_id": "role_hr_admin", "now": now, "pw": hashed_pw}
    )

    await db.commit()
    return {"admin_id": admin_id, "admin_email": admin_email}


async def drop_tenant_schema(schema_name: str) -> None:
    is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI
    if is_sqlite:
        logger.info(f"SQLite mode: skipping schema drop for {schema_name}")
        return

    sync_uri = settings.SYNC_DATABASE_URI
    sync_engine = create_engine(sync_uri)
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("COMMIT"))
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
            conn.execute(text("COMMIT"))
    finally:
        sync_engine.dispose()


async def provision_tenant(
    name: str,
    schema_name: str,
    admin_email: str,
    admin_password: str,
    admin_name: str,
    tier: str = "FREE",
) -> dict:
    async with AsyncSessionGlobal() as global_db:
        existing = await global_db.execute(
            select(Tenant).where(Tenant.schema_name == schema_name)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Tenant with schema_name '{schema_name}' already exists")

        tenant = Tenant(
            id=uuid.uuid4().hex,
            name=name,
            schema_name=schema_name,
            tier=tier,
            is_active=True,
            enabled_modules=DEFAULT_MODULES,
        )
        global_db.add(tenant)
        await global_db.commit()

    await create_tenant_schema(schema_name)

    tenant_schema = f"tenant_{schema_name}" if not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else None
    if tenant_schema:
        tenant_engine = engine.execution_options(schema_translate_map={None: tenant_schema})
        AsyncSessionTenant = async_sessionmaker(
            bind=tenant_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        async with AsyncSessionTenant() as tenant_db:
            tenant_db.info["tenant_id"] = schema_name
            admin_info = await seed_tenant_data(tenant_db, admin_email, admin_password, admin_name)
    else:
        async with AsyncSessionGlobal() as tenant_db:
            tenant_db.info["tenant_id"] = schema_name
            admin_info = await seed_tenant_data(tenant_db, admin_email, admin_password, admin_name)

    await _fire_tenant_event("tenant.provisioned", {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "schema_name": tenant.schema_name,
        "tier": tier,
    })

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "schema_name": tenant.schema_name,
        "tier": tenant.tier,
        "admin_id": admin_info["admin_id"],
        "admin_email": admin_info["admin_email"],
    }


async def _fire_tenant_event(event_type: str, tenant_data: dict):
    try:
        from app.services.webhook_engine import get_webhook_engine
        engine = get_webhook_engine()
        await engine.dispatch_event(event_type, tenant_data, tenant_data.get("schema_name", ""))
    except Exception as e:
        logger.warning(f"Webhook dispatch failed for {event_type}: {e}")


async def deprovision_tenant(tenant_id: str, hard: bool = False) -> dict:
    async with AsyncSessionGlobal() as global_db:
        result = await global_db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        schema_name = tenant.schema_name
        tenant_name = tenant.name

        if hard:
            await global_db.delete(tenant)
            await global_db.commit()
            await drop_tenant_schema(schema_name)
            await _fire_tenant_event("tenant.deprovisioned", {"tenant_id": tenant_id, "tenant_name": tenant_name, "schema_name": schema_name, "mode": "hard"})
            logger.info(f"Hard-deleted tenant {tenant_name} ({tenant_id}), schema {schema_name}")
            return {"status": "hard_deleted", "tenant_id": tenant_id, "tenant_name": tenant_name}
        else:
            tenant.is_active = False
            await global_db.commit()
            await _fire_tenant_event("tenant.deprovisioned", {"tenant_id": tenant_id, "tenant_name": tenant_name, "schema_name": schema_name, "mode": "soft"})
            logger.info(f"Soft-deactivated tenant {tenant_name} ({tenant_id})")
            return {"status": "deactivated", "tenant_id": tenant_id, "tenant_name": tenant_name}
