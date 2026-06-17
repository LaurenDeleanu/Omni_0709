from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
import os
import sys
import uuid
from contextlib import asynccontextmanager

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1 import users, imports, reports, employees, schedules, tenant, calendar, metadata, ai, it, finance, training, admin, hire, sales, work, pay, legal, rbac, grow, ops, intelligence, notifications, announcements, kudos, workflows, integrations, agents, harness, crm, git, monitoring, omni, billing, chat, search, bulk, comments, oauth, workflow_exec, visual_workflows, email_templates, notification_prefs, plugins, slack, docusign, onboarding, approvals, public_agents, demo_recorder, benchmarks, surveys, reviews_360, interviews, time_tracking, checklists, manager, talent_grid, job_board, it_kb_enhanced, auto_onboard, interview_scheduler, it_auto_routing, tool_registry, signup, documents, marketplace, self_service, interview_kits, performance, dev_portal_api, webhooks_api, agent_budgets, agent_schedules, agent_triggers, employee_roles, hr_panel, tax_admin, health, power_automate
from app.api.middleware.csrf import CSRFMiddleware
from app.api.middleware.rate_limiter import PerClientRateLimiter
from app.api.middleware.correlation import CorrelationMiddleware
from app.api.middleware.api_key_rate_limiter import ApiKeyRateLimiter
from app.api.middleware.compression import CompressionMiddleware
from app.api.middleware.body_size_limit import BodySizeLimitMiddleware
from app.services.api_analytics import record_request
from app.services.usage_quotas import record_api_call
from app.core.config import settings
import time as _time


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)
    
    from app.core.database import engine, wait_for_db
    from app.models.base import GlobalBase
    from sqlalchemy import text
    import logging as _logging

    logger = _logging.getLogger("successcore.main")

    db_ready = await wait_for_db(max_retries=10, delay=2.0)
    if not db_ready:
        logger.error("Database unavailable — starting in degraded mode")
    else:
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scripts.seed import seed_tenant_and_users
            await seed_tenant_and_users()
        except Exception as e:
            logger.warning(f"Auto-seed skipped: {e}")

        async with engine.begin() as conn:
            # Migrations are handled by Alembic

            if "sqlite" not in settings.SQLALCHEMY_DATABASE_URI:
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    logger.info("pgvector extension enabled")
                except Exception:
                    logger.warning("pgvector extension not available — vector features disabled")
                await conn.commit()

            for key in ["custom_openai_key", "custom_gemini_key", "custom_openrouter_key", "custom_anthropic_key", "custom_grok_key", "custom_groq_key"]:
                try:
                    async with engine.connect() as alter_conn:
                        await alter_conn.execute(text(f"ALTER TABLE tenants ADD COLUMN IF NOT EXISTS {key} VARCHAR(500) NULL;"))
                        await alter_conn.commit()
                except Exception as e:
                    logger.info(f"Column {key}: {e}")
            try:
                async with engine.connect() as alter_conn:
                    await alter_conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS tier VARCHAR(50) DEFAULT 'FREE' NOT NULL;"))
                    await alter_conn.commit()
            except Exception as e:
                logger.info(f"Column tier: {e}")

        # Tenant schema migrations are now handled externally by migrate_all_tenants.py 
        # before uvicorn boots, preventing event-loop blocks here.

    from app.services.backup_scheduler import start_backup_scheduler
    start_backup_scheduler()

    from app.services.event_notification_bridge import bind_event_notifications
    bind_event_notifications()
    from app.services.event_bus import get_event_bus
    await get_event_bus().start_redis_listener()
    from app.services.synthetic_monitor import start_synthetic_monitor
    await start_synthetic_monitor(interval_seconds=120)
    logger.info("Event notification bridge bound")

    from app.services.org_chart import bind_org_chart_cache_invalidation
    bind_org_chart_cache_invalidation()
    logger.info("Org chart cache invalidation bound")

    from app.services.cron_scheduler import start_cron_scheduler
    from app.core.database import AsyncSessionGlobal
    import asyncio as _asyncio
    _asyncio.ensure_future(start_cron_scheduler(lambda: AsyncSessionGlobal()))
    logger.info("Cron scheduler started")

    from app.services.key_rotation_scheduler import start_key_rotation_scheduler
    _asyncio.ensure_future(start_key_rotation_scheduler(lambda: AsyncSessionGlobal()))
    logger.info("Key rotation scheduler started")

    from app.services.digest_scheduler import start_digest_scheduler
    start_digest_scheduler()
    logger.info("Digest scheduler started")

    from app.services.agent_scheduler import start_scheduler
    await start_scheduler(lambda: AsyncSessionGlobal())
    logger.info("Agent scheduler started")

    from app.core.task_queue import start_worker
    await start_worker()
    logger.info("Redis task queue worker started")

    from app.services.agent_health import monitor_all_agents
    import asyncio as _asyncio
    _health_task = _asyncio.create_task(monitor_all_agents(lambda: AsyncSessionGlobal()))
    logger.info("Agent health monitor started")

    from app.services.pool_monitor import monitor_agent_pools
    _pool_monitor_task = _asyncio.create_task(monitor_agent_pools())
    logger.info("Agent pool monitor started")

    yield

    _pool_monitor_task.cancel()
    _health_task.cancel()
    try:
        await _pool_monitor_task
        await _health_task
    except _asyncio.CancelledError:
        pass

    from app.core.task_queue import stop_worker
    await stop_worker()
    from app.services.backup_scheduler import stop_backup_scheduler
    stop_backup_scheduler()
    from app.services.cron_scheduler import stop_cron_scheduler
    stop_cron_scheduler()
    from app.services.key_rotation_scheduler import stop_key_rotation
    stop_key_rotation()
    from app.services.digest_scheduler import stop_digest_scheduler
    stop_digest_scheduler()
    from app.services.event_bus import get_event_bus
    await get_event_bus().stop_redis_listener()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="SaaS HR System API based on FastAPI",
    version=settings.VERSION,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")


@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    start = _time.monotonic()
    response = await call_next(request)
    latency = int((_time.monotonic() - start) * 1000)
    record_request(method=request.method, path=request.url.path, status_code=response.status_code, latency_ms=latency, client_ip=request.client.host if request.client else "unknown")
    tenant_id = request.headers.get("X-Tenant-ID", "unknown")
    record_api_call(tenant_id)
    return response

# ── Static files ──────────────────────────────────────────────────────────────
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# ── Rate Limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Correlation middleware — injects request_id / tenant_id into logger context
from app.core.logger import request_id_var, tenant_id_var

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    t_id = request.headers.get("X-Tenant-ID") or "-"
    request_id_var.set(req_id)
    tenant_id_var.set(t_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

# FRONTEND_URL and ALLOWED_ORIGINS are configurable in .env
_allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
if settings.FRONTEND_URL not in _allowed_origins:
    _allowed_origins.append(settings.FRONTEND_URL)

app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(PerClientRateLimiter)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(ApiKeyRateLimiter)
app.add_middleware(CompressionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-CSRF-Token"],
    expose_headers=["Content-Disposition"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(users.router,     prefix=f"{settings.API_V1_STR}/users",     tags=["Users"])
app.include_router(employees.router, prefix=f"{settings.API_V1_STR}/employees", tags=["Employee History"])
app.include_router(employee_roles.router, prefix=f"{settings.API_V1_STR}/employees", tags=["Employee Roles"])
app.include_router(imports.router,   prefix=f"{settings.API_V1_STR}/imports",   tags=["Mass Upload"])
app.include_router(reports.router,   prefix=f"{settings.API_V1_STR}/reports",   tags=["Reports PDF/Excel"])
app.include_router(schedules.router, prefix=f"{settings.API_V1_STR}/schedules", tags=["Scheduled Reports"])
app.include_router(tenant.router,    prefix=f"{settings.API_V1_STR}/tenant",    tags=["Tenant Settings"])
app.include_router(calendar.router,  prefix=f"{settings.API_V1_STR}/calendar",  tags=["Calendar"])
app.include_router(metadata.router,  prefix=f"{settings.API_V1_STR}/metadata",  tags=["Dynamic UI Metadata"])
app.include_router(ai.router,        prefix=f"{settings.API_V1_STR}/ai",        tags=["AI Orchestrator"])
app.include_router(it.router,        prefix=f"{settings.API_V1_STR}/it",        tags=["IT Management"])
app.include_router(finance.router,   prefix=f"{settings.API_V1_STR}/finance",   tags=["Finance & Accounting"])
app.include_router(grow.router,      prefix=f"{settings.API_V1_STR}/grow",      tags=["Performance & Culture"])
app.include_router(training.router,  prefix=f"{settings.API_V1_STR}/training",  tags=["Training & LMS"])
app.include_router(admin.router,     prefix=f"{settings.API_V1_STR}/admin",     tags=["Administration"])
app.include_router(hire.router,      prefix=f"{settings.API_V1_STR}/hire",      tags=["Recruitment ATS"])
app.include_router(hire.public_router, prefix=f"{settings.API_V1_STR}/hire", tags=["Recruitment Public"])
app.include_router(sales.router,     prefix=f"{settings.API_V1_STR}/sales",     tags=["CRM & Sales"])
app.include_router(work.router,      prefix=f"{settings.API_V1_STR}/work",      tags=["Project Management"])
app.include_router(ops.router,       prefix=f"{settings.API_V1_STR}/ops",       tags=["Operations & Facilities"])
app.include_router(intelligence.router, prefix=f"{settings.API_V1_STR}/intel",  tags=["Intelligence & Analytics"])
app.include_router(pay.router,       prefix=f"{settings.API_V1_STR}/pay",       tags=["Payroll & Benefits"])
app.include_router(legal.router,     prefix=f"{settings.API_V1_STR}/legal",     tags=["Legal & Compliance"])
app.include_router(rbac.router,      prefix=f"{settings.API_V1_STR}/rbac",      tags=["Role-Based Access Control"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["Notifications"])
app.include_router(integrations.router, prefix=f"{settings.API_V1_STR}/integrations", tags=["Integrations"])
app.include_router(power_automate.router, prefix=f"{settings.API_V1_STR}/power-automate", tags=["Power Automate"])
app.include_router(announcements.router, prefix=f"{settings.API_V1_STR}/announcements", tags=["Announcements"])
app.include_router(kudos.router,      prefix=f"{settings.API_V1_STR}/kudos",      tags=["Kudos Peer Recognition"])
app.include_router(workflows.router,  prefix=f"{settings.API_V1_STR}/workflows",  tags=["Onboarding/Offboarding Workflows"])
app.include_router(agents.router,     prefix=f"{settings.API_V1_STR}/agents",     tags=["AI Agents"])
app.include_router(harness.router,   prefix=f"{settings.API_V1_STR}/harness",   tags=["Harness Test Suite"])
app.include_router(crm.router,        prefix=f"{settings.API_V1_STR}/crm",        tags=["CRM & Contacts"])
app.include_router(git.router,        prefix=f"{settings.API_V1_STR}/git",        tags=["Git & Code Lab"])
app.include_router(monitoring.router, prefix=f"{settings.API_V1_STR}/monitoring", tags=["AI Observability"])
app.include_router(omni.router,       prefix=f"{settings.API_V1_STR}/omni",       tags=["Omni Codebase Controller"])
app.include_router(billing.router,    prefix=f"{settings.API_V1_STR}/billing",    tags=["Billing & API Keys"])
app.include_router(chat.router,       prefix=f"{settings.API_V1_STR}/chat",       tags=["Chat"])
app.include_router(chat.collab_router, prefix=f"{settings.API_V1_STR}/collaborative", tags=["Collaborative Sessions"])
app.include_router(search.router,     prefix=f"{settings.API_V1_STR}/search",     tags=["Search"])
app.include_router(bulk.router,       prefix=f"{settings.API_V1_STR}/bulk",       tags=["Bulk Operations"])
app.include_router(comments.router,   prefix=f"{settings.API_V1_STR}/comments",    tags=["Comments"])
app.include_router(oauth.router,      prefix=f"{settings.API_V1_STR}/oauth",       tags=["OAuth2"])
app.include_router(workflow_exec.router, prefix=f"{settings.API_V1_STR}/workflow-exec", tags=["Workflow Exec"])
app.include_router(visual_workflows.router,  prefix=f"{settings.API_V1_STR}/visual-workflows", tags=["Visual Workflows"])
app.include_router(email_templates.router, prefix=f"{settings.API_V1_STR}/email-templates", tags=["Email Templates"])
app.include_router(notification_prefs.router, prefix=f"{settings.API_V1_STR}/notification-prefs", tags=["Notification Prefs"])
app.include_router(plugins.router, prefix=f"{settings.API_V1_STR}/plugins", tags=["Plugin Marketplace"])
app.include_router(slack.router, prefix=f"{settings.API_V1_STR}/slack", tags=["Slack Integration"])
app.include_router(docusign.router, prefix=f"{settings.API_V1_STR}/docusign", tags=["DocuSign Integration"])
app.include_router(onboarding.router, prefix=f"{settings.API_V1_STR}/onboarding", tags=["AI Onboarding Journeys"])
app.include_router(approvals.router, prefix=f"{settings.API_V1_STR}/approvals", tags=["Human Approvals"])
app.include_router(public_agents.router, prefix=f"{settings.API_V1_STR}/public", tags=["Public Agent API"])
app.include_router(demo_recorder.router, prefix=f"{settings.API_V1_STR}/demo", tags=["Demo Recorder & Skill Discovery"])
app.include_router(benchmarks.router, prefix=f"{settings.API_V1_STR}/benchmarks", tags=["Compensation Benchmarks"])
app.include_router(surveys.router, prefix=f"{settings.API_V1_STR}/surveys", tags=["Pulse Surveys"])
app.include_router(reviews_360.router, prefix=f"{settings.API_V1_STR}/reviews-360", tags=["360 Reviews"])
app.include_router(interviews.router, prefix=f"{settings.API_V1_STR}", tags=["Interview Engine"])
app.include_router(time_tracking.router, prefix=f"{settings.API_V1_STR}/time-tracking", tags=["Time Tracking"])
app.include_router(checklists.router, prefix=f"{settings.API_V1_STR}/checklists", tags=["Checklists & Employee Hub"])
app.include_router(manager.router, prefix=f"{settings.API_V1_STR}/manager", tags=["Manager Command Center"])
app.include_router(talent_grid.router, prefix=f"{settings.API_V1_STR}", tags=["Talent Grid"])
app.include_router(job_board.router, prefix=f"{settings.API_V1_STR}", tags=["Job Board"])
app.include_router(it_kb_enhanced.router, prefix=f"{settings.API_V1_STR}/it/kb", tags=["IT KB Enhanced"])
app.include_router(auto_onboard.router, prefix=f"{settings.API_V1_STR}", tags=["Auto-Onboard"])
app.include_router(interview_scheduler.router, prefix=f"{settings.API_V1_STR}", tags=["Interview Scheduler"])
app.include_router(it_auto_routing.router, prefix=f"{settings.API_V1_STR}", tags=["IT Auto-Routing"])
app.include_router(tool_registry.router, prefix=f"{settings.API_V1_STR}", tags=["Tool Registry"])
app.include_router(signup.router, prefix=f"{settings.API_V1_STR}", tags=["Public Signup"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}", tags=["Documents"])
app.include_router(marketplace.router, prefix=f"{settings.API_V1_STR}", tags=["Agent Marketplace"])
app.include_router(self_service.router, prefix=f"{settings.API_V1_STR}", tags=["Employee Self-Service"])
app.include_router(interview_kits.router, prefix=f"{settings.API_V1_STR}", tags=["Interview Kits"])
app.include_router(performance.router, prefix=f"{settings.API_V1_STR}", tags=["Performance Calibration"])
app.include_router(dev_portal_api.router, prefix=f"{settings.API_V1_STR}", tags=["Developer Portal"])
app.include_router(webhooks_api.router, prefix=f"{settings.API_V1_STR}", tags=["Webhooks"])
app.include_router(agent_budgets.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Agent Budgets"])
app.include_router(agent_schedules.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Agent Schedules"])
app.include_router(agent_triggers.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Agent Triggers"])
app.include_router(hr_panel.router, prefix=f"{settings.API_V1_STR}/hr-panel", tags=["HR Panel"])
app.include_router(tax_admin.router, prefix=f"{settings.API_V1_STR}", tags=["Tax Administration"])
app.include_router(health.router, tags=["System"])
@app.get("/metrics", tags=["System"])
async def prometheus_metrics_endpoint():
    from app.services.prometheus_metrics import generate_prometheus_metrics
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=generate_prometheus_metrics(), media_type="text/plain")


@app.get("/synthetic-check", tags=["System"])
async def synthetic_check():
    from app.services.synthetic_monitor import run_synthetic_check
    return await run_synthetic_check()


@app.get("/synthetic-history", tags=["System"])
async def synthetic_history(limit: int = 20):
    from app.services.synthetic_monitor import get_synthetic_history
    return {"history": get_synthetic_history(limit)}



@app.get("/openapi.json", tags=["System"], include_in_schema=False)
async def get_openapi_spec():
    from fastapi.openapi.utils import get_openapi
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get("/postman.json", tags=["System"], include_in_schema=False)
async def get_postman_collection():
    from fastapi.openapi.utils import get_openapi
    from app.services.postman_export import generate_postman_collection
    spec = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    return generate_postman_collection(spec)


@app.get("/sdk.tgz", tags=["System"], include_in_schema=False)
async def download_typescript_sdk():
    import io, tarfile, time
    from fastapi.responses import Response
    from fastapi.openapi.utils import get_openapi
    
    spec = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    
    sdk_code = [
        "// SuccessCore TypeScript SDK v1.0.0",
        "// Auto-generated — npm install ./successcore-sdk.tgz",
        "",
        'const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";',
        "",
        "async function api(path, opts = {}) {",
        "  const res = await fetch(BASE_URL + path, {",
        '    ...opts, credentials: "include",',
        '    headers: { "Content-Type": "application/json", ...opts.headers }',
        "  });",
        "  if (!res.ok) {",
        '    const e = await res.json().catch(() => ({}));',
        '    throw new Error(e.detail || "API Error " + res.status);',
        "  }",
        "  return res.json();",
        "}",
        "",
        "export class SuccessCoreClient {",
        "  async login(email, password, tenant) {",
        "    return api('/users/login', { method: 'POST', body: JSON.stringify({ email, password, tenant_id: tenant }) });",
        "  }",
        "  async getEmployees(page = 1, size = 20) { return api('/users?page=' + page + '&page_size=' + size); }",
        "  async getAgents() { return api('/agents'); }",
        "  async getNotifications() { return api('/notifications'); }",
        "  async search(q) { return api('/search?q=' + encodeURIComponent(q)); }",
        "  async getDashboardSummary() { return api('/admin/dashboard-summary'); }",
        "  async getOrgChart() { return api('/employees/org-chart'); }",
        "  async getDigest() { return api('/intel/digest'); }",
        "  async createClient(data) { return api('/agents/copilot/run', { method: 'POST', body: JSON.stringify({ message: 'Create client: ' + JSON.stringify(data) }) }); }",
        "}",
        'export default new SuccessCoreClient();',
    ]
    
    package_json = {
        "name": "successcore-sdk", "version": "1.0.0",
        "main": "index.ts", "types": "index.ts",
        "description": "SuccessCore HR Platform TypeScript SDK",
        "license": "MIT"
    }
    
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="package/index.ts")
        info.size = len("\n".join(sdk_code).encode())
        info.mtime = int(time.time())
        tar.addfile(info, io.BytesIO("\n".join(sdk_code).encode()))
        pkg_info = tarfile.TarInfo(name="package/package.json")
        pkg_bytes = __import__('json').dumps(package_json, indent=2).encode()
        pkg_info.size = len(pkg_bytes)
        pkg_info.mtime = int(time.time())
        tar.addfile(pkg_info, io.BytesIO(pkg_bytes))
    
    buf.seek(0)
    return Response(content=buf.read(), media_type="application/gzip",
                    headers={"Content-Disposition": "attachment; filename=successcore-sdk-v1.0.0.tgz"})
