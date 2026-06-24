# AGENTS.md — SuccessCore HR Coding Agent Instructions

This file contains everything a coding agent needs to understand and contribute to this repository correctly. Read it fully before writing any code.

---

## Project Overview

**SuccessCore HR** is a multi-tenant, enterprise SaaS HR platform with native AI agents. It is a monorepo containing:

| Directory | Stack | Purpose |
|-----------|-------|---------|
| `backend/` | Python 3.11, FastAPI, SQLAlchemy async, PostgreSQL + pgvector, Redis | REST API + AI agent runtime |
| `frontend/` | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui | Web application |
| `workers/` | Cloudflare Workers (JS) | Edge AI routing |
| `e2e/` | Playwright | End-to-end tests |
| `scripts/` | Python | Ops scripts (seed, migrate, rollback) |

**Production URLs:**
- Frontend: `NEXT_PUBLIC_SITE_URL` (deployed on Vercel)
- Backend: `https://omnius-sas.onrender.com` (deployed on Render)
- API Docs: `{backend_url}/docs`

---

## Local Development

### Prerequisites
- Docker & Docker Compose, OR:
- Python 3.11+, Node.js 20+, PostgreSQL 15+, Redis 7+

### Running with Docker (recommended)
```bash
cp .env.example .env          # Fill in required secrets
docker compose up -d
# Frontend: http://localhost:3000
# Backend:  http://localhost:8080
# API Docs: http://localhost:8080/docs
```

### Running locally
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

### Required environment variables
Set these in `.env` (copy from `.env.example`). **Never hardcode them.**

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key — **must be 32+ chars, will crash if missing** |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` or `REDIS_HOST` | Redis connection |
| `AUTH0_DOMAIN` | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | Auth0 client ID |
| `NEXT_PUBLIC_API_URL` | Full backend API URL including `/api/v1` |
| `OPENAI_API_KEY` | OpenAI key (optional if tenants use BYOK) |

---

## Architecture

### Multi-tenancy
- Every tenant has its own **PostgreSQL schema**: `tenant_{tenant_id}` (e.g. `tenant_acme_corp`).
- The global schema holds `tenants`, `users`, and billing tables.
- The dependency `get_tenant_db` (in `backend/app/api/dependencies.py`) automatically routes to the correct tenant schema based on the authenticated user's `tenant_id`.
- **Never query cross-tenant data** without using `get_tenant_db`. Do not use `AsyncSessionGlobal` for tenant data.

### Backend structure
```
backend/app/
├── main.py              # FastAPI app, all routers registered here, lifespan hooks
├── core/
│   ├── config.py        # Settings via pydantic-settings (reads .env)
│   ├── database.py      # Async SQLAlchemy engine, session factories, read replica
│   ├── logger.py        # JSON structured logger (request_id + tenant_id context vars)
│   ├── auth.py          # JWT + Auth0 verification
│   ├── cache.py         # Redis helpers
│   └── task_queue.py    # Redis-backed async task queue
├── api/v1/              # 82 routers — one file per domain
│   ├── _pagination.py   # paginate_query() and paginate_cursor() helpers
│   └── *.py             # Domain routers (agents.py, finance.py, hire.py, etc.)
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic v2 request/response schemas
├── services/            # 234 business logic services (agent_fleet.py, llm_router.py, etc.)
└── tasks/               # Scheduled background tasks
```

### Frontend structure
```
frontend/src/
├── app/[locale]/        # Next.js App Router — all routes are locale-prefixed
│   └── dashboard/       # 28 dashboard views
├── components/
│   ├── admin/views/     # Feature views (AgentStudio, CRM, Hire, etc.)
│   ├── ai/              # AiChatWidget, Copilot, MessageBubble
│   ├── layout/          # Sidebar, NotificationCenter, UniversalSearch
│   └── ui/              # shadcn/ui primitives
├── lib/api/             # 31 typed API clients
│   ├── client.ts        # Core HTTP client — use fetchClient() for all API calls
│   └── *.ts             # Domain clients (finance.ts, hire.ts, users.ts, etc.)
└── hooks/               # use-user.ts, use-sse.ts, use-websocket.ts
```

---

## Coding Rules

### Backend

#### Routers (FastAPI)
- **One router file per domain**. Add new routers to `backend/app/api/v1/`.
- Register new routers in `backend/app/main.py` — add both the import and `app.include_router(...)`.
- Always use `Depends(get_tenant_db)` for tenant data, `Depends(get_current_user)` for auth.
- Use `Depends(require_roles([...]))` for RBAC enforcement.
- Protect all write endpoints with RBAC — do not leave routes open.

#### Logging — CRITICAL RULE
- **Never use `print()`**. Use `logging.getLogger(__name__)`.
- The logger is structured JSON with automatic `request_id` and `tenant_id` correlation.
- Pattern:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.info("Message %s", variable)   # use %s formatting, NOT f-strings
  logger.warning("...")
  logger.error("...", exc_info=True)    # always pass exc_info for exceptions
  ```

#### Pagination
- Use `paginate_query()` from `app.api.v1._pagination` for offset-based pagination.
- Use `paginate_cursor()` for large tables where offset is expensive.
- Never return unbounded lists — always apply `.limit()` or `paginate_query()`.

#### Database migrations
- **All schema changes go through Alembic**. Never run raw `ALTER TABLE` in application code or ad-hoc scripts.
- Generate migrations: `cd backend && alembic revision --autogenerate -m "description"`
- Apply migrations: `alembic upgrade head`
- Tenant-schema migrations use `backend/scripts/migrate_all_tenants.py`.

#### Models
- All models live in `backend/app/models/`.
- Use `uuid4().hex` for primary keys (string IDs), not integer sequences.
- Encrypted fields use `app.core.encryption` — do not store PII in plaintext.

#### Configuration
- All settings come from `app.core.config.settings` (pydantic-settings).
- **Never hardcode** URLs, secrets, API keys, or credentials in source code.
- `SECRET_KEY` missing or weak → app crashes on startup. This is intentional.

#### AI / Agent system
- Agent execution flows through `app.services.agent_executor` and `app.services.agent_fleet`.
- The LLM router (`app.services.llm_router`) handles multi-model fallback (OpenAI → Anthropic → Gemini → OpenRouter → Grok → Groq).
- Tenants can provide BYOK (Bring Your Own Key) via `custom_openai_key` etc. on the `Tenant` model.
- Tool execution lives in `app.services.tool_executor` (130 KB — the largest file in the codebase).
- Guardrails, PII masking, and hallucination detection are in `app.services.guard_service`, `pii_sanitizer`, `hallucination_detector`.

### Frontend

#### API calls
- **Always use `fetchClient()`** from `@/lib/api/client` for all API requests.
- `fetchClient()` automatically adds CSRF tokens, handles 401 redirects, sets `credentials: "include"`, and applies a 60-second timeout.
- **Never** use `fetch()` with a hardcoded `http://localhost:8080` or `http://127.0.0.1` URL in production paths.
- When a raw `fetch()` is necessary (e.g. blob downloads where you need the Response object), use:
  ```ts
  `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1"}/your/path`
  ```

#### Authentication
- Auth is cookie-based (`httpOnly`). No tokens in `localStorage` (XSS risk).
- CSRF is handled automatically by `fetchClient()` via double-submit cookie pattern.
- The `auth-guard.tsx` component protects all dashboard routes.

#### Internationalisation
- All UI text must use `next-intl`. Import `useTranslations` and look up keys from `frontend/messages/`.
- Routes are locale-prefixed: `/en/dashboard`, `/es/dashboard`, etc. Use `Link` from `next-intl/navigation`.
- Supported locales: `es`, `en`, `fr`, `de`, `pt`, `ar` (RTL).

#### Components
- Use shadcn/ui primitives from `@/components/ui/` for all base UI elements.
- Use `sonner` (`toast.success()`, `toast.error()`) for notifications — not `alert()`.
- Framer Motion is available for animations. Use it for meaningful transitions, not decoration.

#### Environment variables
- Only `NEXT_PUBLIC_*` vars are available in the browser.
- Server-side vars (Auth0 secrets, etc.) must never be referenced in `"use client"` files.

---

## Adding New Features — Checklist

### New backend endpoint
1. Create or add to the relevant router in `backend/app/api/v1/`.
2. Add Pydantic schemas in `backend/app/schemas/` if needed.
3. Implement business logic in `backend/app/services/`.
4. Register the router in `backend/app/main.py`.
5. If a new DB table: create a model in `backend/app/models/`, then run `alembic revision --autogenerate`.
6. Add an API client function in `frontend/src/lib/api/<domain>.ts`.
7. Never skip RBAC — add `Depends(require_roles([...]))`.

### New frontend page/view
1. Create the route under `frontend/src/app/[locale]/dashboard/`.
2. Add a nav entry in `frontend/src/components/layout/Sidebar.tsx`.
3. All text must use `next-intl` translations.
4. All data fetching must go through `fetchClient()` or the typed API clients.

---

## Testing

```bash
# Backend unit tests
cd backend
python -m pytest tests/ -v

# Frontend type check
cd frontend
npx tsc --noEmit

# Frontend lint
cd frontend
npm run lint

# E2E tests (requires running stack)
npx playwright test
```

---

## What NOT to do

| ❌ Don't | ✅ Do instead |
|----------|--------------|
| Use `print()` | Use `logger = logging.getLogger(__name__)` |
| Hardcode `localhost:8080` in frontend | Use `process.env.NEXT_PUBLIC_API_URL` |
| Use `fetch()` directly in components | Use `fetchClient()` from `@/lib/api/client` |
| Run raw `ALTER TABLE` in code | Use Alembic migrations |
| Query tenant data with `AsyncSessionGlobal` | Use `Depends(get_tenant_db)` |
| Store secrets in source code | Use `.env` / environment variables |
| Commit `*.db` files, `login.json`, or `scratch/` dirs | They are gitignored for a reason |
| Add a migration script at the repo root | Add it to `backend/scripts/` instead |
| Leave a route without RBAC | Add `Depends(require_roles([...]))` |
| Use `localStorage` for auth tokens | Auth is cookie-based — no token storage |

---

## File Size Warning

Several service files are very large (50–130 KB). Before editing:
- `backend/app/services/tool_executor.py` (130 KB) — defines all AI agent tools
- `backend/app/services/agent_fleet.py` (72 KB) — full agent fleet management
- `backend/app/services/platform_knowledge.py` (55 KB) — RAG knowledge base
- `backend/app/services/omni_orchestrator.py` (53 KB) — Omni Master orchestrator
- `backend/app/api/v1/agents.py` (59 KB) — agent CRUD + runtime API

Read the existing patterns in these files before adding new code. They have their own internal conventions.

---

## Deployment

- **Backend**: deployed to Render. Config in `render.yaml`. Migrations run automatically via `scripts/migrate_all_tenants.py` at boot.
- **Frontend**: deployed to Vercel. Config in `frontend/vercel.json`.
- **Edge worker**: deployed to Cloudflare Workers via `workers/wrangler.toml`.
- **CI/CD**: GitHub Actions in `.github/workflows/`.
- **Docker**: `docker-compose.yml` at the repo root for local development.
