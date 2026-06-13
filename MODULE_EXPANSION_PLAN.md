# SAS/SuccessCore — Module Expansion & Enhancement Plan
### Competitive Analysis & Upgrades Roadmap • June 2026

---

## Executive Summary

SuccessCore has 12 fleet AI agents, a working copilot widget, and functional module pages — but modules vary wildly in completeness. Some (IT, Hire, Chat) are deep and production-grade. Others (Reports, Ops, Data Imports) are shells. None have Playwright E2E coverage. The AI agent fleet is the platform's strongest differentiator, but module-specific inline Copilots are only wired on 2 of 8 pages. This plan prioritizes closing the biggest competitive gaps with the highest ROI.

---

## Module-by-Module Analysis

---

### 1. RECRUITING / HIRE ▸ Score: 8/10

**Current State**
- Full Kanban pipeline (applied→screening→interview→offer→hired→rejected)
- AI resume parsing, screening, ranking, interview question generation, batch screening, offer letter generation — all functional
- Rate limiting per tenant
- No public job board endpoint, no email/SMS notification, no calendar integration

**Competitive Landscape (2026)**

| Competitor | Recruiting Edge | SuccessCore Gap |
|-----------|----------------|-----------------|
| **Rippling** | Unified employee lifecycle — hire starts in ATS, auto-flows to onboarding, I-9, payroll | No employee→onboarding auto-flow (promote endpoint exists but isn't triggered on hire) |
| **BambooHR** | Career page hosting, branded job board, LinkedIn/Indeed cross-posting | No public-facing jobs page, no external job board syndication |
| **Workday** | ML-powered candidate matching from employee success patterns | AI screening exists but no historical success-based matching |
| **Greenhouse** | Scorecards, structured interviewing, interviewer calibration | No scorecard model, no calibration tools |
| **Lever** | Nurture campaigns, talent CRM, automated drip sequences | No CRM/talent pool nurturing |
| **Juicebox (2026)** | LLM-native recruiting with AI search across talent data, CRM + automated outreach | AI exists but no automated passive outreach |
| **Deel** | Global hiring compliance in 150+ countries with localized contracts | No multi-country hiring compliance |

**Recommended Upgrades (Priority Order)**

| # | Feature | Effort | Impact | Competitors Match |
|---|---------|--------|--------|-------------------|
| 1 | **Job Board + External Posting** — Public `/careers` page, XML feed for LinkedIn/Indeed, branded company page | 3d | High | BambooHR, Greenhouse |
| 2 | **Talent CRM & Nurture Campaigns** — Candidate pools, tagging, automated drip email sequences, engagement scoring | 4d | High | Lever, Juicebox |
| 3 | **Structured Interview Scorecards** — Per-role criteria templates, interviewer calibration, weighted scoring | 2d | Medium | Greenhouse, Workday |
| 4 | **Auto-Hire → Onboarding Flow** — When candidate reaches `hired` stage, auto-create employee record, assign onboarding plan, trigger enrollment | 2d | Medium | Rippling, BambooHR |
| 5 | **Email + Calendar Integration** — Send interview invites via Google/Outlook Calendar, SMS reminders | 3d | Medium | All competitors |
| 6 | **Passive Candidate Sourcing** — AI-driven LinkedIn profile matching, automated outreach messages | 4d | Low | Juicebox |
| 7 | **Video Interview AI Analysis** — Un-mock the `/interviews/video-analysis` endpoint with real Whisper + emotion detection | 5d | Low | HireVue, Modern Hire |

---

### 2. IT HELPDESK ▸ Score: 9/10 (Strongest Module)

**Current State**
- 4-tab dashboard: Tickets, Assets, Licenses, Requisitions — all fully functional
- AI knowledge base: semantic search, auto-generated articles, recurring issue detection, preventive actions, auto-tag, SLA estimation
- Jira integration, OData/Power BI feed, warranty alerts
- **Missing:** KB UI in frontend, no ticket age charts, no real-time notifications, no SLA dashboards

**Competitive Landscape (2026)**

| Competitor | ITSM Edge | SuccessCore Gap |
|-----------|-----------|-----------------|
| **Jira Service Management** | Incident/change/problem management, CMDB, SLA-driven queues | SLA exists via AI estimate but no SLA breach alerts or queue views |
| **ServiceNow** | Virtual Agent (chatbot), automated workflows, asset lifecycle | AI copilot exists but no dedicated IT chatbot widget |
| **Freshservice** | Ticket lifecycle automation, agent collision detection, integrated asset discovery | No automated ticket routing (assignee is manual) |
| **Zendesk** | Multi-channel (email, chat, social), macros, triggers, SLAs | Chat exists but IT tickets are manual, no email→ticket bridge |

**Recommended Upgrades**

| # | Feature | Effort | Impact | 
|---|---------|--------|--------|
| 1 | **IT KB Frontend** — Visible KB article browser, search UI, link from ticket resolution | 2d | High |
| 2 | **SLA Dashboards & Alerts** — Ticket age charts, breach count, resolution time trends, email alerts | 2d | High |
| 3 | **Automated Ticket Routing** — Round-robin or skill-based assignment using AI, load balancing | 2d | Medium |
| 4 | **Email-to-Ticket Bridge** — Inbound email parsing → auto-create tickets, email thread attachment | 3d | Medium |
| 5 | **Asset Lifecycle Management** — Procurement→deployment→maintenance→retirement workflows, depreciation schedule | 3d | Low |
| 6 | **Real-Time IT Notifications** — WebSocket alerts for new tickets, SLA breaches, asset warranty expirations | 1d | Medium |
| 7 | **Change Management Module** — RFC forms, CAB approval workflow, rollback plans, audit trail | 5d | Low |

---

### 3. FINANCE ▸ Score: 6/10

**Current State**
- Expense claims with AI OCR receipt scanning
- Time tracking with clock-in/out, geolocation, break logs, Spanish labor law compliance
- Journal entries auto-generated on expense approval
- SEPA export, CSV ERP export (Holded, Sage)
- Payroll intelligence (tax optimization, payslip PDF, compensation)
- **Missing:** No budget module, no inline Copilot, no multi-currency, no recurring payments, no invoice management, no financial dashboards

**Competitive Landscape (2026)**

| Competitor | Finance Edge | SuccessCore Gap |
|-----------|-------------|-----------------|
| **Rippling** | Full payroll + benefits in 50 states + 50 countries, PTO sync with payroll | Payroll intelligence exists but no multi-country payroll engine |
| **Gusto** | Automated tax filing, benefits administration, workers comp | Tax engines exist per-country but no automated tax filing |
| **ADP** | Enterprise payroll, 401(k), complex compliance | Good for mid-market but ADP dominates enterprise |
| **Odoo** | Full accounting module (double-entry, bank reconciliation, invoicing, budgets) | No accounting module at all |
| **Holded/Sage** | ERP integration, accounting automation | Has CSV export but no live API sync |
| **Expensify** | AI receipt scanning, automatic policy enforcement, corporate card reconciliation | OCR exists but no policy engine |

**Recommended Upgrades**

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **Budget Management** — Department/project budgets, tracking vs actual, variance alerts, forecasting | 4d | High |
| 2 | **Inline Finance Copilot** — Add `InlineCopilot` to finance page with expense/budget analysis quick actions | 1d | High |
| 3 | **Financial Dashboards** — Revenue/expense trends, budget burn rate, department spend comparisons | 3d | Medium |
| 4 | **Invoice Management** — AP/AR ledger, invoice creation, payment tracking, aging reports | 5d | Medium |
| 5 | **Multi-Currency Support** — Currency conversion, exchange rate API, multi-currency expense reporting | 2d | Medium |
| 6 | **Corporate Card Integration** — Transaction feed import, auto-categorization, receipt matching | 3d | Low |
| 7 | **Live ERP Sync** — Replace CSV export with REST API integration for Holded, Sage, SAP | 4d | Low |

---

### 4. TRAINING & GROW ▸ Score: 5/10

**Current State (Training)**
- Course catalog with SCORM mock player (4 hardcoded slides)
- FUNDAE compliance engine (XML export, validation, bonus calculation)
- xAPI statement endpoint exists (no frontend)
- AI course recommendations endpoint exists (not called from UI)
- No course creation UI, no actual SCORM content rendering

**Current State (Grow/OKR)**
- OKR grid with key results, progress bars, CRUD
- Performance reviews with self-eval, manager feedback, peer nominations
- AI goal generation, adjustment, alignment, development planning — all backend only
- No career path visualization, no 9-box grid, no team analytics

**Competitive Landscape (2026)**

| Competitor | L&D Edge | SuccessCore Gap |
|-----------|----------|-----------------|
| **Workday** | Skills cloud, career hub, ML-driven learning recommendations, internal mobility | Career paths exist backend, no skills cloud |
| **BambooHR** | Performance management with e-signatures, goal cascading, self/manager assessments | OKRs exist, no goal cascading tree |
| **Lattice** | Continuous feedback, 360 reviews, compensation tied to performance, engagement surveys | Reviews exist, no comp-to-perf link, no engagement surveys |
| **Culture Amp** | Engagement surveys, pulse checks, action frameworks, benchmarking | No engagement or pulse survey module |
| **Docebo** | AI-powered learning platform, social learning, gamification, content marketplace | SCORM mock only, no gamification |
| **Cornerstone** | Skills ontology, AI-driven content curation, compliance training automation | No skills ontology |

**Recommended Upgrades**

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **SCORM 1.2/2004 Real Player** — Replace mock with actual `pipwerks-scorm-api-wrapper` or `rustici-software` SCORM runtime | 5d | High |
| 2 | **Course Creator UI** — Admin form to create courses, upload SCORM packages, set FUNDAE eligibility | 2d | High |
| 3 | **Surface AI Features in UI** — Wire up goal generation, review summaries, career paths to frontend | 2d | High |
| 4 | **Goal Cascading Tree** — Visual tree of company→department→team→individual OKRs with alignment lines | 3d | Medium |
| 5 | **Employee Engagement Surveys** — Pulse surveys, eNPS, sentiment analysis, action planning | 4d | Medium |
| 6 | **Skills Matrix & Gap Analysis** — Per-role skill requirements, employee self-assessment, gap visualization, training recommendations | 4d | Medium |
| 7 | **9-Box Talent Grid** — Performance vs potential matrix, calibration sessions, succession planning | 3d | Low |
| 8 | **Gamification** — Badges, leaderboards, learning paths, certification tracking | 3d | Low |

---

### 5. DATA IMPORTS ▸ Score: 3/10

**Current State**
- Drag-and-drop CSV/XLSX upload for employees only
- Redis-backed async import with progress polling
- Backend supports candidates, courses, expenses — but no UI for those
- No column mapping, no duplicate detection UI, no import history

**Competitive Landscape (2026)**

| Competitor | Import Edge | SuccessCore Gap |
|-----------|------------|-----------------|
| **BambooHR** | Bulk import wizards for every entity type, column mapping UI, duplicate merge | Only employees entity has frontend |
| **Rippling** | API-first imports, SFTP automation, webhook-based sync | No automated/scheduled imports |
| **Workday** | EIB (Enterprise Interface Builder), packaged integrations, transformation templates | No transformation engine |
| **Flatfile** | Embedded CSV import with AI column mapping, validation, error highlighting | No AI column mapping, no inline error highlighting |

**Recommended Upgrades**

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **Multi-Entity Import UI** — Add entity selector (Employees, Candidates, Courses, Expenses, IT Assets) with entity-specific validation | 2d | High |
| 2 | **AI Column Mapping** — Auto-detect column meanings (e.g., "Nombre"→first_name), suggest mappings, handle aliases | 2d | High |
| 3 | **Import History & Rollback** — Past imports table, error logs viewer, single-click rollback for failed/partial imports | 2d | Medium |
| 4 | **Scheduled/Automated Imports** — SFTP/API source connectors, cron-based auto-import, email success reports | 4d | Medium |
| 5 | **Inline Error Highlighting** — Show row-level errors directly in the preview table with fix suggestions | 2d | Low |
| 6 | **Excel Template Generator** — Dynamic .xlsx template generation per entity with data validation rules | 1d | Low |

---

### 6. REPORTS ▸ Score: 3/10

**Current State**
- PDF executive report, Excel employee export, 4 summary stat cards, role distribution bar chart
- Scheduled reports model exists, `schedules` page exists (basic)
- `/dashboard/report` is a whistleblower portal — naming collision with `/dashboard/reports`
- No interactive dashboards, no drill-down, no custom report builder, no period comparisons

**Competitive Landscape (2026)**

| Competitor | Analytics Edge | SuccessCore Gap |
|-----------|---------------|-----------------|
| **Workday** | Prism Analytics, discovery boards, predictive analytics, embedded BI | No BI layer, no predictive analytics |
| **BambooHR** | Custom report builder, saved reports, scheduled delivery, custom fields in filters | Only 2 hardcoded export types |
| **Rippling** | Unified analytics across HR, IT, Finance modules, custom dashboards | Siloed data — no cross-module analytics |
| **Power BI / Tableau** | Self-service analytics, drill-down, multiple chart types, live connectivity | IT has OData but no other module has live connectors |
| **Visier** | People analytics platform with benchmarking, workforce planning, predictive turnover | No workforce planning or benchmarking |

**Recommended Upgrades**

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **Interactive Dashboard Builder** — Drag-and-drop widget grid, chart type selector (bar, line, pie, table, KPI), module data source picker | 5d | High |
| 2 | **Custom Report Builder** — Filter builder (employee, department, date range, metric), column selector, saved reports, scheduled email delivery | 4d | High |
| 3 | **Cross-Module Analytics** — Unified dashboard combining HR + IT + Finance metrics in one view | 3d | Medium |
| 4 | **OData/API Export for All Modules** — Extend OData from IT-only to all entity types for Power BI/Tableau connectivity | 3d | Medium |
| 5 | **Predictive People Analytics** — Turnover risk scoring, flight risk alerts, headcount forecasting, compensation benchmarking | 5d | Medium |
| 6 | **Drill-Down Charts** — Click any chart segment to drill into underlying data, export filtered subset | 2d | Low |
| 7 | **Fix Naming Collision** — Rename `/dashboard/report` (whistleblower) to `/dashboard/legal` or `/dashboard/whistleblower` | 0.5d | Low |

---

### 7. CHAT & AI ▸ Score: 8/10

**Current State**
- Full-featured chat with auto-provisioned rooms, WebSocket messaging, file upload, typing indicators, unread badges
- 12 fleet AI agents with copilot widget, tool execution, streaming SSE, feedback collection
- Agent Studio for agent management and configuration
- Omni Master orchestrator for multi-agent coordination
- Encrypted message content (Fernet), GDPR 90-day retention
- **Missing:** Message search, reactions, read receipts, group chat creation UI, AI budget tracking UI, prompt versioning UI

**Competitive Landscape (2026)**

| Competitor | Chat/AI Edge | SuccessCore Gap |
|-----------|-------------|-----------------|
| **Slack** | Channels, threads, app integrations, reactions, search, workflows | No threads, no reactions, no app integrations |
| **Microsoft Teams** | Deep Office 365 integration, meeting scheduling, file collaboration, apps | Chat exists but no document co-editing or meeting integration |
| **MoveWorks** | Enterprise AI copilot that auto-resolves IT/HR tickets, integrates with 100+ enterprise apps | Copilot exists but no automated resolution (only suggestions) |
| **Glean** | Enterprise search across all SaaS tools, AI-powered answers from company data | RAG is module-specific, no unified enterprise search |
| **Jasper / Copy.ai** | Marketing AI, content generation, brand voice | No marketing/content AI module |

**Recommended Upgrades**

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **Inline Copilot Expansion** — Add to Finance, Training, Ops, Reports, Grow, Imports pages (6 pages missing) | 2d | High |
| 2 | **Message Search & Threads** — Full-text message search, thread replies, per-message read status | 3d | High |
| 3 | **AI Budget Tracking UI** — Show per-agent/per-user cost dashboards, usage limits, alerts | 2d | Medium |
| 4 | **Message Reactions & Emoji** — Unicode reactions on messages, hover reaction picker | 1d | Medium |
| 5 | **Automated AI Resolution** — Copilot auto-executes tool calls for common requests (PTO, ticket creation) without manual approval when confidence > 0.95 | 3d | Medium |
| 6 | **Unified Enterprise Search** — Single search bar across employees, tickets, courses, documents, chat messages | 4d | Low |
| 7 | **Group Chat Creation UI** — Let users create ad-hoc group rooms, set room topic/description | 1d | Low |
| 8 | **Prompt A/B Testing UI** — Agent Studio panel to compare prompt variants, show win rates, cost-per-request | 3d | Low |

---

### 8. OPERATIONS ▸ Score: 4/10

**Current State**
- Hot-desking (desk, parking, room booking) with overlap detection
- Visitor registration (check-in timestamping)
- Workflow engine exists (backend) with templates but no Ops page integration
- Gantt chart service, Kanban WebSocket exist for project management (separate pages)
- **Missing:** No inline Copilot, no calendar view, no equipment tracking, no facility maintenance, no visitor check-out UI

**Competitive Landscape (2026)**

| Competitor | Ops Edge | SuccessCore Gap |
|-----------|----------|-----------------|
| **Envoy** | Visitor management, desk booking, delivery management, health screening | Visitor reg exists, no health screening |
| **Robin** | Interactive floor plans, room scheduling, desk booking, analytics | No floor plan, no room scheduling conflict UI |
| **OfficeSpace** | Space planning, move management, real estate forecasting, scenario modeling | No space planning |
| **ServiceNow FM** | Full facility management, maintenance scheduling, asset lifecycle | No maintenance system |
| **Monday.com** | Visual workflow builder, automation recipes, dashboard views | Workflow engine exists, no visual builder |
| **Asana** | Project templates, timeline view, workload management, goals | Gantt and Kanban exist as services, need better UI |

**Recommended Upgrades**

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | **Inline Ops Copilot** — Add to Ops page with booking/resource/vendor quick actions | 1d | High |
| 2 | **Interactive Calendar View** — Day/week/month calendar view for desk/room/parking bookings with drag-to-book | 3d | High |
| 3 | **Facility Maintenance System** — Maintenance request form, ticket lifecycle, vendor assignment, recurring maintenance schedules | 4d | Medium |
| 4 | **Visitor Check-Out** — Add check-out button, auto-checkout after X hours, visitor badge number tracking | 1d | Medium |
| 5 | **Equipment Tracking** — IT equipment checkout/return, maintenance history, depreciation, location tracking | 3d | Medium |
| 6 | **Floor Plan Visualization** — SVG/Canvas floor plan editor, drag-and-drop desk assignment, occupancy heat map | 5d | Low |
| 7 | **Visual Workflow Builder** — No-code drag-and-drop workflow designer with approval steps, conditionals, triggers | 5d | Low |

---

## Cross-Cutting Improvements (All Modules)

| # | Initiative | Effort | Rationale |
|---|-----------|--------|-----------|
| 1 | **Playwright E2E Tests for All Modules** — Hire, IT, Finance, Training, Chat, Ops, Reports, Imports | 8d | Zero E2E coverage outside agent-studio; critical for regression safety |
| 2 | **API Contract Tests** — FastAPI TestClient tests for all CRUD endpoints across all modules | 5d | Most modules have zero API-level tests |
| 3 | **Standardize Model Style** — Migrate hire.py, grow.py, ops.py from `Column()` to `Mapped`/`mapped_column` | 1d | Inconsistent across 3 of 8 model files |
| 4 | **Unified Notification System** — In-app toasts, email, SMS, push notifications with user preferences per module | 5d | No notification infrastructure exists |
| 5 | **Mobile PWA Enablement** — Service worker, offline support, push notifications, responsive audit | 3d | No mobile strategy |
| 6 | **RBAC Granularity Audit** — Ensure fine-grained permissions per module (view/edit/delete/approve per entity) | 2d | Role-based access exists but granularity varies by module |
| 7 | **Fix Naming Collisions** — `/dashboard/report` (Legal) vs `/dashboard/reports` (Analytics), duplicate time-tracking | 1d | Confusing UX |
| 8 | **Performance Optimization** — React Server Components, streaming, bundle splitting, image optimization | 5d | Large bundles, no code splitting |
| 9 | **Audit Logging** — Every CUD operation across all modules to an immutable audit trail | 3d | Missing in most modules |

---

## Priority Roadmap (90-Day Sprint)

### Sprint 1 (Days 1–15): High-Impact Quick Wins
- [ ] Inline Copilot on 6 missing pages (Finance, Training, Ops, Reports, Grow, Imports)
- [ ] IT KB frontend + SLA dashboards
- [ ] Finance budget management module
- [ ] Reports interactive dashboard builder
- [ ] Fix report/legal naming collision

### Sprint 2 (Days 16–30): Competitive Baseline
- [ ] Hire job board + public careers page
- [ ] Training real SCORM player + course creator UI
- [ ] Imports multi-entity UI + AI column mapping
- [ ] Chat message search + threads
- [ ] Ops calendar view + inline copilot

### Sprint 3 (Days 31–45): Depth & Polish
- [ ] Hire talent CRM & nurture campaigns
- [ ] Finance invoice management + multi-currency
- [ ] Reports cross-module analytics + OData expansion
- [ ] Playwright E2E for Hire, IT, Finance
- [ ] Unified notification system foundation

### Sprint 4 (Days 46–60): Advanced Features
- [ ] Training skills matrix & gap analysis
- [ ] Grow surface AI features in UI (goal gen, review summaries, career paths)
- [ ] Ops facility maintenance system + equipment tracking
- [ ] Chat AI budget tracking UI + automated resolution
- [ ] Scheduled/automated imports

### Sprint 5 (Days 61–75): Enterprise Readiness
- [ ] Hire email + calendar integration (Google/Outlook)
- [ ] Reports predictive people analytics
- [ ] Grow 9-box grid + engagement surveys
- [ ] API contract tests for all modules
- [ ] RBAC granularity audit + fixes

### Sprint 6 (Days 76–90): Differentiators
- [ ] Chat unified enterprise search
- [ ] Reports drill-down + export builder
- [ ] Operations visual workflow builder + floor plan
- [ ] Mobile PWA enablement
- [ ] Audit logging across all modules
- [ ] Remaining E2E tests + performance optimization
