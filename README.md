<p align="center">
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-teal?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-blue?logo=postgresql" alt="PostgreSQL pgvector" />
  <img src="https://img.shields.io/badge/Redis-7-red?logo=redis" alt="Redis" />
  <img src="https://img.shields.io/badge/Cloudflare-Workers-orange?logo=cloudflare" alt="Cloudflare Workers" />
  <img src="https://img.shields.io/badge/license-proprietary-red" alt="License" />
</p>

# Omni HR

**Plataforma SaaS empresarial de gestión de recursos humanos con agentes de inteligencia artificial nativos.**

SuccessCore HR unifica 28 módulos de RRHH en una sola plataforma y los potencia con 10 agentes de IA especializados que automatizan tareas complejas: desde la gestión de empleados y nóminas hasta el reclutamiento, compliance y analítica avanzada.

---

## ✨ Características principales

### 🤖 AI Agents nativos
- **10 agentes especializados**: HR Assistant, Payroll Specialist, IT Helpdesk, Recruiter Pro, Sales Coach, Performance Coach, Onboarding Buddy, Compliance Officer, Data Analyst, Finance Manager
- **Omni Master**: Orquestador multi-agente que descompone tareas complejas y coordina agentes especializados
- **Copilot universal**: Asistente AI con delegación inteligente y RAG contextual
- **6 proveedores LLM**: OpenAI, Anthropic, Gemini, OpenRouter, Grok, Groq con cascade fallback
- **Memoria semántica**: pgvector + Redis para contexto persistente entre sesiones

### 📦 Módulos integrados

| Categoría | Módulos |
|-----------|---------|
| **Core HR** | Empleados, Organigrama, Historial laboral, Importación masiva CSV/Excel |
| **Tiempo** | Calendario, Vacaciones/PTO, Control horario, Turnos |
| **Finanzas** | Nóminas, Compensación, Gastos, Ledger contable |
| **Talento** | Reclutamiento ATS, Onboarding, Formación LMS, Evaluaciones, OKRs |
| **Operaciones** | IT Helpdesk, Proyectos, Operaciones, Legal/Compliance |
| **Comercial** | CRM, Pipeline de ventas, Leads |
| **Analytics** | People Analytics, Reportes PDF/Excel, Dashboards |
| **Colaboración** | Chat, Reconocimientos (Kudos), Anuncios, Workflows |
| **Plataforma** | RBAC, Notificaciones, Integraciones (Slack, DocuSign), Plugins, API pública |

### 🌍 Enterprise-ready
- **Multi-tenant**: Aislamiento completo de datos por organización
- **6 idiomas**: Español, English, Français, Deutsch, Português, العربية (RTL)
- **Auth0 SSO**: Google, Microsoft, SAML corporativo + login local
- **GDPR compliant**: Encriptación de datos, data residency, PII masking, derecho al olvido
- **FUNDAE**: Validación de compliance para formación bonificada (España)
- **Registro horario digital**: Cumplimiento RDL 8/2019 y reforma 2026

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND                               │
│  Next.js 16 · React 19 · Tailwind CSS v4 · shadcn/ui     │
│  next-intl (6 idiomas) · Auth0 · PWA · Monaco Editor     │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                    BACKEND                                │
│  FastAPI · SQLAlchemy async · pgvector · Redis           │
│  58 API routers · 152 servicios · 40 modelos             │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              AI AGENT SYSTEM                        │  │
│  │  Copilot Orchestrator → 10 Specialist Agents        │  │
│  │  Agent Runtime (ReAct) · Multi-Model Router         │  │
│  │  RAG (pgvector) · Semantic Memory · Tool Registry   │  │
│  │  Guardrails · Hallucination Detection · PII Masking │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                  INFRASTRUCTURE                           │
│  PostgreSQL + pgvector · Redis · Docker Compose           │
│  Cloudflare Workers (Edge AI) · GitHub Actions CI/CD      │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Inicio rápido

### Prerrequisitos
- Docker & Docker Compose
- Node.js 20+ (para desarrollo local)
- Python 3.11+ (para desarrollo local)

### Con Docker (recomendado)

```bash
# Clonar el repositorio
git clone <repo-url> && cd SAS

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves (Auth0, OpenAI, etc.)

# Iniciar todos los servicios
docker compose up -d

# La aplicación estará disponible en:
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8080
# API Docs:  http://localhost:8080/docs
```

### Desarrollo local

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend
cd frontend
npm install
npm run dev
```

### Variables de entorno requeridas

| Variable | Descripción |
|----------|-------------|
| `AUTH0_DOMAIN` | Dominio de Auth0 (ej: `your-tenant.auth0.com`) |
| `AUTH0_CLIENT_ID` | Client ID de Auth0 |
| `AUTH0_CLIENT_SECRET` | Client Secret de Auth0 |
| `OPENAI_API_KEY` | API key de OpenAI (opcional si se usa BYOK) |
| `SECRET_KEY` | Clave secreta para JWT local |
| `DATABASE_URL` | URL de PostgreSQL (por defecto usa Docker) |
| `REDIS_HOST` | Host de Redis (por defecto `redis` en Docker) |

---

## 📊 Estructura del proyecto

```
SAS/
├── frontend/                    # Next.js 16 App Router
│   ├── src/
│   │   ├── app/[locale]/       # Rutas internacionalizadas
│   │   │   ├── dashboard/      # 28 vistas de dashboard
│   │   │   ├── login/          # Página de login
│   │   │   └── pricing/        # Página de precios
│   │   ├── components/
│   │   │   ├── ai/             # Chat Widget, Copilot, Markdown
│   │   │   ├── admin/views/    # Agent Studio, CRM, Workflows, etc.
│   │   │   ├── layout/         # Sidebar, Búsqueda, Notificaciones
│   │   │   └── ui/             # shadcn/ui components
│   │   └── lib/api/            # 31 API clients tipados
│   └── messages/               # i18n (es, en, fr, de, pt, ar)
│
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── api/v1/             # 58 routers API REST
│   │   ├── core/               # Config, DB, Auth, Redis
│   │   ├── models/             # 40 modelos SQLAlchemy
│   │   ├── schemas/            # 16 schemas Pydantic
│   │   ├── services/           # 152 servicios de negocio
│   │   └── tasks/              # Tareas programadas
│   ├── alembic/                # Migraciones de BD
│   └── requirements.txt
│
├── workers/                     # Cloudflare Workers
│   └── agent_edge.js           # Edge AI router
│
├── e2e/                         # Playwright E2E tests
├── .github/workflows/          # CI/CD
├── docker-compose.yml
└── AUDITORIA_COMPLETA_SUCCESSCORE.md  # Auditoría y plan de negocio
```

---

## 🧪 Tests

```bash
# Backend unit tests
cd backend && python -m pytest app/

# E2E tests
npx playwright test

# Frontend lint + typecheck
cd frontend && npm run lint && npx tsc --noEmit
```

---

## 📈 Roadmap

Ver [AI_STUDIO_ROADMAP.md](AI_STUDIO_ROADMAP.md) para el plan detallado de mejora del sistema AI.

| Fase | Alcance | Estado |
|------|---------|--------|
| Phase 1 | Context Manager, Multi-Model Router, ReAct, Dynamic Prompts | 🔄 En progreso |
| Phase 2 | 60 nuevas tools, Tool ACL, 10-agent fleet, Platform Knowledge | 📋 Planificado |
| Phase 3 | Omni Master v2, Deployment Channels, Budget Caps | 📋 Planificado |
| Phase 4 | Visual Agent Builder, Persistent Sessions, Semantic Memory | 📋 Planificado |
| Phase 5 | External API, Health Monitoring, Skill Certification | 📋 Planificado |
| Phase 6 | A/B Deployments, Edge AI, Voice Interface | 📋 Planificado |

---

## 🔒 Seguridad

- **Auth0 SSO**: Google, Microsoft, SAML corporativo
- **RBAC**: Roles y permisos granulares por tenant
- **CSRF Protection**: Tokens anti-CSRF en todas las peticiones
- **Rate Limiting**: Por IP, por API key, por tenant
- **Field Encryption**: Encriptación a nivel de campo para datos sensibles
- **PII Masking**: Enmascaramiento automático en respuestas AI
- **Prompt Injection Detection**: Guardrails en sistema AI
- **Audit Trail**: Registro completo de acciones y ejecuciones AI

---

## 📄 Licencia

Software propietario. Todos los derechos reservados.  
SuccessCore HR © 2026

---

