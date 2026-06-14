# SuccessCore HR — Deep Codebase Re-Audit & Per-Module Enhancement Plan

**Date:** June 14, 2026  
**Scope:** 76 API modules, 54 frontend pages, 40+ services, 110+ models  
**Status:** 11 critical runtime crashes fixed. 27 frontend violations identified.

---

## 1. Audit Results — Critical Fixes Applied

| # | File | Issue | Fix |
|---|---|---|---|
| 1 | `signup.py` | Missing `Depends` import | Added to fastapi import |
| 2 | `signup.py` | `provision_tenant_schema` doesn't exist | → `provision_tenant` |
| 3 | `signup.py` | `auto_onboard` module path wrong | → `app.api.v1.auto_onboard` |
| 4 | `signup.py` | `create_checkout_session` is class method | → `StripeIntegration.create_checkout_session(...)` |
| 5 | `marketplace.py` | Missing `func` from sqlalchemy | Added `func, distinct` |
| 6 | `webhook_builder.py` | Missing `hashlib` import | Added at top, removed inline `import hmac` |
| 7 | `expense_ocr.py` | `_call_llm_cascade` doesn't exist | Replaced with standalone `_call_llm()` using direct OpenAI client |
| 8 | `finance_forecasting.py` | `JournalEntry.amount` → no such field | → `JournalLine.debit` |
| 9 | `finance_forecasting.py` | `Invoice.total` → no such field | → `Invoice.total_amount` |
| 10 | `performance_calibration.py` | 6 fields don't exist on `PerformanceReview` | Rewritten to use `manager_evaluation` JSON |
| 11 | `developer_portal.py` | `client_secret`, `scopes`, `grant_types` wrong | → `client_secret_hash`, `allowed_scopes`, removed `grant_types` |
| 12 | `usage_billing.py` | `tokens_used` → no such field | → `token_usage` |
| 13 | `main.py` | `harness` imported but unregistered | Added `include_router(harness.router)` |
| 14 | `main.py` | `/it` prefix collision (it + it_kb_enhanced) | → `/{API_V1}/it/kb` |
| 15 | `main.py` | Hardcoded prefixes (bot_steps, signup) | → `{settings.API_V1_STR}/bots` and `{settings.API_V1_STR}` |

---

## 2. Per-Module Enhancement Plan

### 2.1 API v1 Modules (76 files)

| Module | Current State | Enhancements |
|---|---|---|
| **agents.py** (1139 lines) | 42 endpoints, crew/swarm orchestration added. Rate-limited. | Add `GET /agents/{id}/conversations` — conversation history. Add `POST /agents/{id}/export` — export agent config. |
| **users.py** (529 lines) | 18 endpoints. JWT + local auth. Sessions, password policy. | Add `POST /users/{id}/2fa` — TOTP setup. Add `GET /users/sessions` — active sessions list. |
| **chat.py** (1020 lines) | 22 endpoints + WebSocket. Redis pub/sub backplane. | Add typing indicators via WebSocket. Add `PUT /rooms/{id}/settings`. |
| **finance.py** (1653 lines) | 46+ endpoints + forecasting + OCR. Main module. | Move forecasting/OCR to standalone modules. Add `GET /p&l` and `GET /balance-sheet` auto-generated reports. |
| **billing.py** (430 lines) | Stripe live, invoices, usage billing. | Add `GET /billing/history` — payment history. Add `POST /billing/estimate` — cost estimator. |
| **hire.py** (1290 lines) | 38 endpoints. ATS + screening + interview kits. | Add `POST /hire/{jobId}/publish` — multi-channel posting. Add `GET /hire/analytics` — pipeline metrics. |
| **it.py** (780 lines) | IT service desk + SLA dashboard. | Add `POST /tickets/{id}/escalate`. Add `GET /it/asset-lifecycle`. |
| **admin.py** (792 lines) | Full admin panel. RBAC, audit, modules. | Add `GET /admin/health` — system health dashboard. Add `POST /admin/impersonate`. |
| **pay.py** (917 lines) | 28 endpoints. Payroll + tax. | Add `POST /pay/run-automated` — scheduled payroll. Add multi-currency payslip generation. |
| **signup.py** (new) | Self-service signup. Tier selection. Stripe checkout. | Add email verification. Add `POST /signup/resend-verification`. |
| **documents.py** (new) | 3 endpoints. Offer letters, contracts, NDAs. | Add digital signature request (via DocuSign). Add template customization UI. |
| **marketplace.py** (new) | 5 endpoints. Agent publish/install/browse. | Add ratings/reviews. Add featured agents. Add `GET /marketplace/stats`. |
| **self_service.py** (new) | 5 endpoints. Profile + time-off + payslips. | Add document upload (ID, certificates). Add `GET /self-service/benefits`. |
| **interview_kits.py** (new) | 4 endpoints. 3 default kits. Scoring. | Persist kits to DB. Add `POST /kits/{id}/share`. |
| **performance.py** (new) | 3 endpoints. Calibration, promotion tracking. | Add `POST /performance/review-request`. Add `GET /performance/history`. |
| **dev_portal_api.py** (new) | 4 endpoints. API key CRUD + usage stats. | Add rate limit per key. Add webhook secret management. |
| **webhooks_api.py** (new) | 4 endpoints. Webhook subscriptions + test. | Add `GET /webhooks/delivery-log`. Add webhook payload templates. |

### 2.2 Frontend Pages (54 dashboard + 5 public)

| Page | Current State | Enhancements |
|---|---|---|
| **landing** (`/`) | Hardcoded dark theme. Uses `next/link`. | Migrate to CSS variables. Switch to `@/i18n/routing`. Add animated hero. |
| **pricing** (`/pricing`) | Hardcoded dark theme. `next/link`. | Same migration. Add monthly/annual toggle. Add enterprise contact form. |
| **careers** (`/careers`) | Hardcoded dark theme. 555 lines. | Migrate to CSS variables. Add job filters. Add "refer a friend." |
| **login** (`/login`) | Already migrated to CSS variables. Good. | Add "forgot password" flow. Add social login buttons. |
| **signup** (`/signup`) | New. Uses CSS variables. Excellent baseline. | Add tier comparison table. Add demo video. |
| **dashboard** (`/dashboard`) | CSS variables. KPIs, charts. | Add customizable widget grid. Add dark/light mode toggle. |
| **employees** (`/employees`) | 1172 lines. Full CRUD. | Add bulk actions (multi-select). Add export to CSV. |
| **chat** (`/chat`) | 858 lines. Hardcoded zinc/slate colors. | Migrate to CSS variables. Add message reactions. Add file preview. |
| **agent-studio** (`/agent-studio`) | Migrated to CSS variables. | Add agent version history. Add A/B testing UI. |
| **locale switcher** | New component. CSS variables. | Already complete. |
| **SSE streaming** | useSSE hook extracted. Both widgets migrated. | Add streaming progress bar. Add token count display. |

### 2.3 Services (40+ files)

| Service | Status | Action |
|---|---|---|
| `agent_executor.py` | 1024 lines. Core engine. | Add function call timeout. Add cost estimation before execution. |
| `task_queue.py` | Redis Streams. DLQ. Pending recovery. | Add task prioritization. Add scheduled tasks (cron). |
| `cache_advanced.py` | Tiered L1/L2. Stampede protection. | Add Redis Cluster support. Add cache warming scheduler. |
| `finance_forecasting.py` | Fixed. Cash flow, variance, anomalies. | Add seasonal decomposition. Add confidence intervals. |
| `performance_calibration.py` | Fixed. Distribution, promotion tracking. | Add calibration meeting scheduling. Add 9-box grid generation. |
| `usage_billing.py` | Fixed. Token tracking, monthly bills. | Add cost alerts. Add budget caps per tenant. |
| `expense_ocr.py` | Fixed. Receipt scanning + categorization. | Add multi-page receipt support. Add currency detection. |
| `sla_tracking.py` | IT ticket SLA. Response/resolution monitoring. | Add escalation triggers. Add SLA report PDF generation. |
| `doc_generator.py` | 3 templates. HTML→PDF via fpdf2 + Jinja2. | Add more templates (warning letter, promotion, resignation). Add bulk generation. |
| `webhook_builder.py` | Fixed. HMAC signatures. Retry with backoff. | Add webhook delivery log. Add dead-letter webhook queue. |
| `developer_portal.py` | Fixed. API key management. | Add OAuth2 client management. Add API versioning. |

---

## 3. Infrastructure Gaps

| Area | Current | Enhancement |
|---|---|---|
| **Testing** | No test framework for backend. `client.test.ts` exists for frontend. | Add pytest with async support. Add API integration tests. |
| **CI/CD** | Vercel auto-deploy. Render manual deploy. | Add GitHub Actions for lint, typecheck, test on PR. |
| **Monitoring** | OpenTelemetry instrumentation. In-memory metrics. | Add Prometheus exporter. Add Grafana dashboards. |
| **Logging** | Structured JSON logs. Correlation middleware. | Add log level configuration per module. Add log sampling for high-volume. |
| **Security** | CSRF middleware. JWT auth. CORS restricted. | Add rate limit per API key. Add IP-based throttling. Add SQL injection guard. |
| **Backups** | DB backup scheduler exists. | Add backup verification. Add point-in-time recovery. |

---

## 4. Priority Queue

### Immediate (fix before next deploy)
- [x] All 15 critical fixes applied
- [ ] Verify `_call_llm` in expense_ocr.py works with actual OpenAI key

### Week 1-2
- [ ] Migrate 4 hardcoded-theme pages (landing, pricing, careers, docs) to CSS variables
- [ ] Switch 5 pages from `next/link` to `@/i18n/routing`
- [ ] Add missing `credentials: "include"` to signup fetch calls

### Week 3-4
- [ ] Register orphan routers (health, agent_budgets, agent_schedules, agent_triggers) or document why unregistered
- [ ] Add rate limiting to remaining 20% of endpoints
- [ ] Add database-level tenant isolation (RLS)

### Month 2
- [ ] pytest test suite for backend (50+ integration tests)
- [ ] GitHub Actions CI/CD pipeline
- [ ] Prometheus + Grafana monitoring

### Month 3+
- [ ] SOC 2 compliance evidence collection
- [ ] Multi-region failover
- [ ] Read replica for analytics queries
