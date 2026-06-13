import logging
import uuid
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rag import KnowledgeDocument
from app.models.agent import Agent
from app.services.rag_service import add_document_to_knowledge, query_knowledge_base

logger = logging.getLogger(__name__)

PLATFORM_KNOWLEDGE_DOCUMENTS: Dict[str, str] = {
    "module_hr_users": """# HR / Users Module

## Overview
The HR module is the core of the SuccessCore platform, managing employee lifecycle from onboarding to offboarding. It centralizes all employee data including profiles, department assignments, organizational hierarchy, PTO tracking, and self-service capabilities.

## API Endpoints
- **POST /api/v1/employees** - Create a new employee (requires hr_admin role). Fields: email, full_name, department, role, base_salary, country, contract_type, hire_date, vacation_allowance.
- **PUT /api/v1/employees/{id}** - Update employee fields dynamically via a fields dict. Any column on the User table can be updated.
- **DELETE /api/v1/employees/{id}** - Archive an employee by setting is_active=False. Does not physically delete. Fires employee.archived event.
- **GET /api/v1/employees/search** - Multi-field search by name, email, department, role, and active status. Returns up to 20 results.
- **GET /api/v1/employees/{id}** - Get full employee profile with all non-PII canonical fields.
- **GET /api/v1/org-chart** - Returns nested tree of the entire organization using manager_id relationships. Max depth configurable.
- **GET /api/v1/span-of-control** - Returns direct report counts per manager, sorted by report count descending.
- **GET /api/v1/employees/{id}/pto-balance** - Returns PTO allowance, days used (from approved vacation requests), and remaining days.
- **GET /api/v1/departments/{name}/members** - Lists all active employees in a department.
- **GET /api/v1/employees/recent-hires** - Lists employees hired in the last N days (default 30).

## Data Entities
### User
Fields: id (uuid), email, full_name, department, role (employee|manager|hr_admin|it_admin), base_salary, country, contract_type, hire_date, vacation_allowance, is_active, currency, manager_id, timezone, locale, phone_number, created_at, updated_at.

## Business Rules & Validation
- Email must be unique across all active employees.
- Vacation allowance defaults to 22 days for Spanish employees (30 for new hires via promote_to_employee).
- Archive is soft-delete (is_active=False), never hard-delete employee records.
- Manager assignment uses manager_id self-referential FK.
- Base salary is stored in Euro cents (float) with default currency EUR.
- Contract types: indefinido, temporal, practicas, formacion.

## Common Workflows
1. **New Hire**: create_employee -> assign manager -> generate_onboarding_plan -> assign_onboarding_buddy -> trigger_workflow
2. **Employee Search**: search_employees -> get_employee_profile_full -> check PTO/team info
3. **Org Review**: get_org_chart -> get_span_of_control -> identify managers with too many/too few reports
4. **Department Analysis**: get_department_members -> get_department_stats (headcount + avg salary) -> identify gaps

## Edge Cases & Limitations
- Org chart depth is limited to prevent circular references (self-referencing manager_id)
- PTO calculation counts full days only (weekends included in date range)
- Archived employees still appear in historical data but are excluded from active queries
- No bulk import/export endpoints yet (planned for v2)
- Department field is free-text, not a FK to a departments table""",

    "module_calendar": """# Calendar Module

## Overview
The Calendar module manages vacation requests, meetings, tasks, and work schedules across the organization. It integrates with the HR module for PTO balance validation and provides team-wide visibility into availability.

## API Endpoints
- **POST /api/v1/vacation-requests** - Request vacation (request_vacation tool). Required: employee_id, start_date, end_date, optional reason. Validates no overlapping approved/pending requests.
- **PUT /api/v1/vacation-requests/{id}/approve** - Approve or reject vacation. Sets reviewed_by and reviewed_at. Status becomes approved or rejected.
- **GET /api/v1/team-calendar** - Returns combined calendar of vacations, meetings, and tasks for a department. Filter by department and days ahead (default 30).
- **POST /api/v1/meetings** - Create meeting with organizer, attendees list, start/end datetime, location, and description.
- **GET /api/v1/employees/{id}/work-schedule** - Returns employee's work schedule by day of week with start/end times and flexible flag.
- **GET /api/v1/vacations/upcoming** - Returns all approved vacations starting from now (used for planning coverage).

## Data Entities
### VacationRequest
Fields: id, user_id, start_date, end_date, reason, status (pending|approved|rejected), reviewed_by, reviewed_at, days_requested.

### Meeting
Fields: id, title, description, start_datetime, end_datetime, location, organizer_id, attendees (JSON array of user IDs).

### Task
Fields: id, title, description, assigned_to, due_date, priority (low|medium|high|urgent), status (pending|in_progress|completed), context (optional, e.g., "lead:ID").

### WorkSchedule
Fields: id, user_id, day_of_week (0-6), start_time, end_time, flexible (bool).

## Business Rules & Validation
- Vacation dates: start_date must be strictly before end_date.
- Overlap detection: no employee can have two approved/pending vacation requests that overlap in date ranges.
- Meeting time validation: start_datetime must be before end_datetime.
- Vacation approval is manual; system does not auto-approve based on balance.
- PTO balance is computed live: allowance minus sum of days in approved vacation requests.
- Work schedules support flexible working (flexible=True means core hours only).

## Common Workflows
1. **Vacation Request**: employee -> request_vacation -> manager reviews PTO balance -> approve_vacation -> calendar updated
2. **Team Planning**: manager -> get_team_calendar -> check coverage gaps -> schedule meetings around vacations
3. **Meeting Coordination**: organizer -> get_team_calendar for availability -> create_meeting with attendees
4. **Task Management**: create_task -> assign to employee -> update status on completion

## Edge Cases & Limitations
- Vacation overlap check uses date comparison, not timezone-aware.
- Meetings don't check attendee conflicts (planned enhancement).
- Tasks don't support recurring patterns yet.
- No iCal export endpoint implemented yet (planned).
- PTO accrual is annual, not pro-rated for mid-year hires. No carry-over logic.
- Task context field (like "lead:ID") is informal, not FK-constrained.""",

    "module_payroll": """# Payroll Module

## Overview
The Payroll module handles payroll cycles, payslip generation, tax calculations (Spanish IRPF brackets), compensation changes, and bonus management. This module contains highly sensitive financial data and is restricted to HR admins for write operations.

## API Endpoints
- **POST /api/v1/payroll-cycles** - Create a new payroll cycle with period_name, start_date, end_date. Starts in draft status.
- **POST /api/v1/payroll-cycles/{id}/process** - Process payroll for all active employees. Generates payslips with line items (base salary as earning, IRPF 19% as deduction). Sets cycle status to processing. Calculates total_gross and total_net.
- **GET /api/v1/employees/{id}/payslips** - Get payslip for employee. Without cycle_id returns latest. Includes line_items array.
- **GET /api/v1/tax-rules** - Returns all tax rules, filterable by country_code. Spanish IRPF has progressive brackets.
- **PUT /api/v1/employees/{id}/compensation** - Update base_salary and currency. Fires salary.changed event. Logs old and new values.
- **POST /api/v1/bonuses** - Create a bonus for an employee with amount, description, and type (standard|performance|retention|signing). Status starts as pending.

## Data Entities
### PayrollCycle
Fields: id, period_name, start_date, end_date, status (draft|processing|completed), total_gross, total_net.

### Payslip
Fields: id, cycle_id (FK), employee_id, gross_salary, deductions, net_salary, currency, status (draft|final), created_at.

### PayslipLineItem
Fields: id, payslip_id (FK), description, amount, type (earning|deduction).

### TaxRule
Fields: id, country_code, name, calculation_type, rate, min_salary, max_salary, is_deduction, is_marginal.

### Bonus
Fields: id, employee_id, amount, description, type (standard|performance|retention|signing), status (pending|approved|paid).

## Business Rules & Validation
- Payroll cycles can only be processed when in draft status.
- Processing generates one payslip per active employee with flat 19% IRPF deduction.
- Spanish IRPF brackets (progressive): up to 12450 EUR = 19%, 12450-20200 = 24%, 20200-35200 = 30%, 35200-60000 = 37%, 60000-300000 = 45%, above 300000 = 47%.
- Current implementation uses simplified 19% flat rate for all employees.
- Compensation changes fire salary.changed event for audit trail.
- Bonus status lifecycle: pending -> approved -> paid.
- Currency defaults to EUR for Spanish tenants.

## Common Workflows
1. **Monthly Payroll**: create_payroll_cycle -> process_payroll -> get_payslip per employee -> cycle marked as completed
2. **Salary Review**: update_compensation -> create_bonus (if applicable) -> notify employee
3. **Tax Query**: get_tax_rules(country_code="ES") -> review brackets -> calculate estimated net

## Edge Cases & Limitations
- Flat 19% IRPF is a simplification. Real implementation should use progressive brackets.
- No bonus approval workflow yet - bonuses are created as pending but no approval mechanism.
- Payroll processing does not yet handle: social security contributions, meal allowances, travel per diem, overtime, sick leave deductions.
- No multi-country payroll support beyond ES (country field exists but processing is ES-only).
- Payslip generation is not idempotent - running process_payroll twice on same cycle would create duplicate payslips.
- No payslip PDF generation yet.""",

    "module_finance": """# Finance Module

## Overview
The Finance module manages expense claims, time tracking (clock-in/out for Spanish labor law compliance), journal entries for the general ledger, and ERP exports. It ensures compliance with Spanish labor regulations (RD-ley 8/2019 requiring mandatory time tracking).

## API Endpoints
- **GET /api/v1/finance/ledger** - Get journal entries within date range. Includes line items with account codes, debits, and credits. Default limit 50 entries.
- **GET /api/v1/finance/expenses** - Aggregated expense summary by department and category. Returns totals, by_category breakdown, and by_department breakdown.
- **POST /api/v1/finance/expenses** - Create an expense claim with amount, category, and description. Status starts as pending.
- **POST /api/v1/time-tracking/clock-in** - Clock in for an employee. Validates no active session exists (no clock_out=None entry). Records timestamp.
- **POST /api/v1/time-tracking/{id}/clock-out** - Clock out on an existing active TimeLog entry. Appends notes.
- **GET /api/v1/employees/{id}/time-logs** - Get time tracking entries for an employee filtered by date range.

## Data Entities
### JournalEntry
Fields: id, reference, date, description, created_at.

### JournalLine
Fields: id, entry_id (FK), account_code, account_name, debit, credit.

### ExpenseClaim
Fields: id, user_id (FK), total_amount, category, description, status (pending|approved|rejected|paid), date, created_at.

### TimeLog
Fields: id, user_id (FK), clock_in (datetime), clock_out (datetime), notes.

## Business Rules & Validation
- **Spanish Labor Law (RD-ley 8/2019)**: Time tracking is mandatory for all employees. Must record start and end time daily.
- Clock-in validation: an employee cannot clock in if they have an active session (clock_out is NULL).
- Clock-out validation: the TimeLog must exist and not already have a clock_out value.
- Expense claims require user_id, amount, and category. Status lifecycle: pending -> approved/rejected -> paid.
- Journal entries follow double-entry accounting (debits = credits per entry).
- Expense aggregation groups by both category and department for cross-analysis.

## Common Workflows
1. **Daily Time Tracking**: clock_in at start of day -> clock_out at end of day -> manager reviews get_time_logs
2. **Expense Reimbursement**: employee creates expense -> manager approves -> finance processes payment -> status set to paid
3. **Financial Reporting**: get_financial_ledger (monthly) -> review journal lines -> export to ERP
4. **Department Budget Review**: get_expense_summary per department -> compare against budget

## Edge Cases & Limitations
- No overtime calculation yet (hours beyond work schedule not computed).
- Expense approval is implicit - no explicit approval step implemented.
- Journal entries cannot be edited after creation (immutable for audit).
- No ERP export format (SAP, Sage, etc.) implemented yet.
- Time tracking doesn't enforce work schedule compliance (no late arrival detection).
- No meal break tracking (mandatory in Spain for shifts >6 hours).
- No bank reconciliation or accounts payable/receivable modules yet.""",

    "module_it": """# IT / Helpdesk Module

## Overview
The IT module provides helpdesk ticketing, IT asset management, knowledge base search with semantic matching, and automated ticket categorization using AI. It integrates with the Agent Studio for agent-driven ticket resolution.

## API Endpoints
- **POST /api/v1/it/tickets** - Create IT support ticket. Required: requester_id, title, description, category (Hardware|Software|Network|Access|Other). Default priority Medium, status Open.
- **PUT /api/v1/it/tickets/{id}/assign** - Assign ticket to support agent. Sets assignee_id and status to in_progress.
- **PUT /api/v1/it/tickets/{id}/resolve** - Resolve ticket with resolution_notes. Sets status=resolved, resolved_at, generates KB reference (KB-{ticket_id_prefix}).
- **GET /api/v1/it/assets** - List IT assets. Filter by assigned_to_id or category. Returns name, serial_number, category, status, purchase_date, cost.
- **GET /api/v1/it/tickets/stats** - Ticket statistics for last N days. Returns opened count, resolved count, avg_resolution_hours, breakdown by category.
- **POST /api/v1/it/kb/search** - Semantic search of IT knowledge base for solutions to technical problems.
- **POST /api/v1/it/tickets/{id}/auto-tag** - AI-powered auto-categorization of ticket. Suggests category, priority, tags, and best assignee.
- **POST /api/v1/it/tickets/{id}/suggest-solution** - AI suggestion of solutions from historically resolved similar tickets with similarity scores.

## Data Entities
### ITTicket
Fields: id, title, description, category (Hardware|Software|Network|Access|Other), priority (Low|Medium|High|Critical), status (Open|In Progress|Resolved|Closed), requester_id (FK User), assignee_id (FK User), resolution_notes, resolved_at, created_at, updated_at.

### ITAsset
Fields: id, name, serial_number, category, status, assigned_to_id (FK User), purchase_date, cost.

## Business Rules & Validation
- Ticket lifecycle: Open -> In Progress (on assign) -> Resolved (on resolve, generates KB reference) -> Closed.
- Auto-tag uses AI to analyze ticket content and suggest category/priority/tags/assignee.
- KB suggestions use similarity scoring from resolved tickets.
- IT assets track hardware lifecycle: purchase_date, cost, assigned_to.
- Resolution notes are required when resolving - they feed into the KB.

## Common Workflows
1. **Employee Report**: user reports issue -> create_it_ticket -> auto_tag for categorization -> assign_it_ticket -> resolve_it_ticket with notes
2. **Self-Service KB**: user -> search_it_knowledge_base -> find solution -> if unresolved, create ticket
3. **Asset Management**: IT admin -> get_it_assets -> filter by assigned employee -> track hardware refresh cycles
4. **Performance Monitoring**: get_ticket_stats -> analyze resolution times -> identify bottlenecks by category

## Edge Cases & Limitations
- No SLA tracking per ticket priority (planned).
- KB search is semantic (cosine similarity) but doesn't weight by resolution success.
- Asset depreciation not calculated (accounting integration planned).
- No automatic ticket routing by category (uses manual assignment or auto-tag suggestions).
- KB reference generation is simple (prefix only), not a full KB article creation.
- No license management tracking for software assets.""",

    "module_training": """# Training / Learning Module

## Overview
The Training module manages course catalog, employee enrollments, SCORM-compliant content, FUNDAE (Fundacion Estatal para la Formacion en el Empleo) compliance validation, and AI-powered course recommendations based on role, department, and learning history.

## API Endpoints
- **POST /api/v1/training/enroll** - Enroll employee in a course. Validates no duplicate enrollment. Sets status=enrolled, progress=0%.
- **GET /api/v1/training/catalog** - List all courses. Filter by category (keyword search in title) or fundae_only (boolean, only FUNDAE-eligible courses).
- **GET /api/v1/training/progress/{employee_id}** - Get training progress for employee. Returns each enrollment with course name, status, progress_pct, score, completed_at, time_spent_seconds.
- **POST /api/v1/training/recommend/{employee_id}** - AI-generated course recommendations based on role, department, and history. Returns limit recommendations (default 3).
- **POST /api/v1/training/validate-fundae/{enrollment_id}** - Run FUNDAE compliance validation: checks duration (>minimum), progress (>=75%), test score (>=50%), and survey completion. Returns overall_eligible.

## Data Entities
### Course
Fields: id, title, description, is_scorm (bool), min_duration_hours (float), is_fundae_eligible (bool).

### CourseEnrollment
Fields: id, user_id (FK), course_id (FK), status (enrolled|in_progress|completed|dropped), progress_percentage (0-100), score, completed_at, time_spent_seconds, created_at.

### FundaeValidation
Fields: id, enrollment_id (FK), duration_valid, progress_valid, test_valid, survey_valid, overall_eligible, generated_at.

## Business Rules & Validation
- **FUNDAE Compliance** requires all four criteria:
  1. Duration: time_spent_seconds >= course.min_duration_hours * 3600
  2. Progress: progress_percentage >= 75.0%
  3. Test: score >= 50.0
  4. Survey: completed (currently always true)
- Duplicate enrollment detection: same employee cannot enroll twice in the same course.
- SCORM courses track progress automatically via the SCORM API.
- Course recommendations use AI (external recommender service) based on employee profile.

## Common Workflows
1. **Self-Directed Learning**: browse catalog -> enroll_in_course -> complete modules -> validate_fundae for compliance
2. **Manager Assignment**: manager -> recommend_courses for employee -> enroll -> monitor get_training_progress
3. **FUNDAE Audit**: compliance officer -> validate_fundae for all enrollments -> generate reports -> submit to FUNDAE
4. **Career Development**: AI recommends courses -> employee enrolls -> completes -> skill matrix updates

## Edge Cases & Limitations
- Survey validation is currently a placeholder (always true) - needs actual survey integration.
- Course recommendations have a hard dependency on the external course_recommender service.
- No prerequisite chain validation (should course B require course A completion).
- No certification/credential tracking beyond course completion.
- SCORM progress tracking depends on SCORM API being integrated in the course player.
- FUNDAE validation is point-in-time snapshot, not continuous monitoring.
- No learning path / curriculum grouping (multiple courses as a program).""",

    "module_recruitment": """# Recruitment / ATS Module

## Overview
The Recruitment module provides a full Applicant Tracking System (ATS) with job postings, candidate pipeline management, interview scheduling, AI-powered resume screening, candidate ranking, and automated interview question generation. It integrates with the HR module for candidate-to-employee promotion.

## API Endpoints
- **POST /api/v1/jobs** - Create job posting. Fields: title, department, description, location, employment_type (full-time|part-time|contract|internship). Status starts as open.
- **POST /api/v1/candidates** - Add candidate to a job. Fields: job_id, first_name, last_name, email, phone, source, notes. Stage starts as applied.
- **PUT /api/v1/candidates/{id}/stage** - Move candidate through pipeline stages: applied -> screening -> interview -> offer -> hired -> rejected. Validates stage name.
- **POST /api/v1/interviews** - Schedule interview for candidate with interviewer. Fields: candidate_id, interviewer_id, scheduled_at, duration_minutes, interview_type (video|phone|onsite).
- **GET /api/v1/jobs/{id}/applications** - Get all candidates and stage distribution for a job.
- **GET /api/v1/recruitment/stats** - Pipeline metrics: open jobs, total candidates, stage distribution, avg time-to-hire.
- **POST /api/v1/candidates/{id}/promote** - Convert hired candidate to employee. Creates User record, marks candidate as hired.
- **POST /api/v1/recruitment/screen-resume** - Full resume screening pipeline: parse + match. Optional job_id for matching.
- **POST /api/v1/recruitment/screen-candidate** - AI-powered screening: parse, score, bias detection, interview questions.
- **POST /api/v1/recruitment/rank-candidates** - Rank multiple candidates against a job posting.
- **POST /api/v1/recruitment/generate-interview-questions** - Generate 5-8 tailored interview questions for candidate vs job.

## Data Entities
### JobPosting
Fields: id, title, department, description, location, employment_type, status (open|closed|on_hold), created_at, updated_at.

### Candidate
Fields: id, job_id (FK), first_name, last_name, email, phone, source, notes, stage (applied|screening|interview|offer|hired|rejected), created_at, updated_at.

### Interview
Fields: id, candidate_id (FK), interviewer_id (FK User), scheduled_at, duration_minutes, interview_type, feedback (text), created_at.

## Business Rules & Validation
- Pipeline stages are strictly defined: applied, screening, interview, offer, hired, rejected.
- Moving a candidate to hired stage suggests using promote_to_employee.
- Screen resume uses AI to parse PDF/DOCX/TXT files and extract structured data.
- Candidate ranking returns scores 0-100 with sub-scores and recommendations.
- Interview questions cover: technical, behavioral, situational, and cultural fit categories.
- Email uniqueness: a candidate's email must not already exist as a User email when promoting.

## Common Workflows
1. **Full Recruitment**: create_job_posting -> source candidates -> add_candidate -> screen_resume -> move_candidate_stage through pipeline -> schedule_interview -> promote_to_employee
2. **Bulk Screening**: rank_candidates (multiple) -> shortlist -> schedule_interviews
3. **Interview Prep**: generate_interview_questions -> schedule_interview -> conduct interview
4. **Pipeline Analysis**: get_pipeline_stats -> get_job_applications per job -> identify bottlenecks

## Edge Cases & Limitations
- No email notification system for stage changes or interview scheduling.
- Interview feedback is a single text field, not structured scoring.
- No offer letter generation (planned).
- Candidate deduplication by email only (same person applying to multiple jobs).
- Resume screening requires file path on disk, not direct upload in API.
- No integration with external job boards (LinkedIn, Indeed) for automatic posting.
- Time-to-hire calculated only for hired candidates, not including rejected.""",

    "module_performance": """# Performance / Grow Module

## Overview
The Performance module enables OKR (Objectives and Key Results) management, performance review cycles, SMART goal generation with AI, and peer recognition through kudos. It supports both individual and team-level goal tracking with real-time progress monitoring.

## API Endpoints
- **POST /api/v1/okrs** - Create an Objective with optional Key Results array. Each KR has title, target_value, current_value, unit.
- **PUT /api/v1/krs/{id}** - Update current_value of a Key Result. Calculates progress_pct automatically.
- **POST /api/v1/reviews** - Create performance review cycle. Fields: employee_id, manager_id, cycle_name, self_assessment (optional). Status starts as Self Evaluation or Draft.
- **GET /api/v1/okrs/team** - Get all OKRs for a department with nested Key Results and progress percentages.
- **GET /api/v1/employees/{id}/kudos** - Get kudos received by employee. Sorted by most recent.
- **GET /api/v1/kudos/leaderboard** - Top kudos receivers across the organization.
- **POST /api/v1/kudos** - Send kudos to a colleague with message and badge emoji.
- **POST /api/v1/goals/smart** - Generate AI-powered SMART goals based on employee role and department.
- **POST /api/v1/goals/adjust** - Mid-quarter review with AI-suggested goal adjustments.

## Data Entities
### Objective
Fields: id, title, description, owner_id (FK User), status (On Track|At Risk|Behind|Completed), created_at.

### KeyResult
Fields: id, objective_id (FK), title, target_value (int), current_value (int), unit (%, #, EUR, etc.).

### PerformanceReview
Fields: id, employee_id (FK), manager_id (FK), cycle_name, status (Draft|Self Evaluation|Manager Review|Calibration|Complete), self_evaluation (JSON), manager_evaluation (JSON), created_at, completed_at.

### Kudos
Fields: id, sender_id, receiver_id (FK User), message, badge, created_at.

## Business Rules & Validation
- KR progress: progress_pct = (current_value / target_value) * 100, clamped to 0-100.
- Performance review cycles progress through defined stages.
- SMART goals are AI-generated based on employee profile (role, department, company strategy).
- Goal adjustments use AI to analyze current progress and suggest modifications.
- Kudos are public recognition visible to all employees.
- KR unit field supports custom units for different measurement types.

## Common Workflows
1. **Quarterly OKR Setting**: employee -> create_okr with KRs -> manager reviews -> team views get_team_okrs -> weekly update_key_result
2. **Performance Review**: manager -> create_review -> employee self_assessment -> manager evaluation -> calibration -> complete
3. **Peer Recognition**: employee -> create_kudos to colleague -> visible on get_kudos_received and leaderboard
4. **Goal Planning**: employee -> generate_smart_goals -> review suggestions -> create_okr with selected goals
5. **Mid-Quarter Adjustment**: employee -> suggest_goal_adjustments -> review AI suggestions -> update_key_result

## Edge Cases & Limitations
- KR progress is linear calculation, no weighted KRs per objective.
- Performance reviews don't yet have structured scoring rubrics (text-based evaluations only).
- No 360-degree feedback mechanism (peer/upward reviews).
- SMART goal generation quality depends on AI model quality.
- No goal cascading (company OKR -> department OKR -> individual OKR alignment).
- Kudos don't have categories or point systems.
- No performance improvement plan (PIP) workflow.""",

    "module_crm": """# CRM / Sales Module

## Overview
The CRM module manages the complete sales lifecycle: clients, leads, pipeline tracking, AI-powered lead scoring, email template generation, and deal analytics. It provides a full sales pipeline from prospecting to closed deals.

## API Endpoints
- **GET /api/v1/crm/pipeline** - Full pipeline overview with leads grouped by stage, showing count, total value, and average probability per stage.
- **GET /api/v1/crm/clients/{id}** - Client details with all associated leads/deals.
- **GET /api/v1/crm/clients** - Search clients by company name or industry keyword.
- **GET /api/v1/crm/deals/stats** - Deal statistics for a period (month|quarter|year): won count, won value, lost count, loss rate %, avg deal size.
- **POST /api/v1/crm/clients** - Create a new client record with company_name, email, contact_person, phone.
- **POST /api/v1/crm/tasks** - Create a calendar task linked to a lead for follow-up actions.
- **POST /api/v1/crm/activities** - Log CRM activity (call, email, meeting, note) against a lead.
- **POST /api/v1/crm/leads/{id}/score** - AI-powered multi-factor lead scoring (0-100). Returns quality tier and conversion probability.
- **POST /api/v1/crm/leads/{id}/suggest-action** - Recommend next best action for a lead (call, email, meeting, demo, proposal, follow_up, nurture, disqualify).
- **POST /api/v1/crm/leads/{id}/email-template** - Generate personalized email template: cold_outreach, follow_up, demo_invite, proposal_cover, check_in, re_engagement, breakup.

## Data Entities
### Client
Fields: id, company_name, industry, website, primary_contact_name, primary_contact_email, primary_contact_phone, created_at.

### Lead
Fields: id, title, client_id (FK), stage, estimated_value, probability, created_at, updated_at.

## Business Rules & Validation
- Lead stages represent the sales pipeline from prospecting to closed.
- Lead scoring uses multi-factor AI analysis returning 0-100 score with quality tier.
- Suggested actions are AI-generated based on lead stage, score, and activity history.
- Email templates are personalized based on lead context and intended communication type.
- Deal statistics calculate: win rate = won / total, loss rate = lost / total, avg deal size = sum(estimated_value) / total.
- Tasks for leads can be created as calendar reminders with due dates.

## Common Workflows
1. **Lead Qualification**: create_client -> capture lead -> score_lead -> suggest_sales_action -> take action
2. **Deal Pipeline**: leads move through stages -> get_pipeline_overview for tracking -> get_deal_stats for metrics
3. **Client Management**: search_clients -> get_client_details -> log_lead_activity -> create_task_for_lead
4. **Email Outreach**: generate_email_template -> customize -> send -> log activity -> track response

## Edge Cases & Limitations
- No email sending integration (templates are generated but not sent via email service).
- Lead scoring AI quality depends on model used.
- No revenue forecasting based on pipeline weighted values.
- Client-company relationship is 1:1 (no parent/subsidiary relationships).
- No custom pipeline stages per tenant (stages are standardized).
- Activity logging is text-based, no structured activity types with metadata.
- No territory or sales rep assignment/territory management.""",

    "module_projects": """# Projects / Work Management Module

## Overview
The Projects module provides project management with Kanban-style task boards, project tracking, wiki pages for documentation, and real-time collaboration via WebSocket. It supports task assignment, status tracking, and project-level progress monitoring.

## API Endpoints
- **POST /api/v1/projects** - Create a project with name, description, and status. Default status: active.
- **POST /api/v1/projects/{id}/tasks** - Create a task within a project. Fields: title, description, assignee_id, priority, due_date. Default status: todo.
- **GET /api/v1/projects/{id}** - Get project status with task breakdown: total, completed, in_progress, blocked, todo counts.
- **POST /api/v1/wiki** - Create a wiki page. Optionally linked to a project via project_id. Fields: title, content.
- **POST /api/v1/tasks** - Create a standalone task/reminder (not tied to a project). Fields: title, description, assigned_to_email, priority. Default status: pending.

## Data Entities
### Project
Fields: id, name, description, status (active|completed|on_hold|cancelled), due_date, created_at.

### Task (Work)
Fields: id, project_id (FK, nullable), title, description, assignee_id (FK User), priority (low|medium|high|urgent), status (todo|in_progress|completed|blocked|done), due_date, created_at.

### WikiPage
Fields: id, title, content, project_id (FK, nullable), created_at, updated_at.

## Business Rules & Validation
- Project status lifecycle: active -> completed (or on_hold, cancelled).
- Task statuses: todo, in_progress, completed, blocked. "done" is an alias for completed.
- Tasks can be standalone (no project) or project-linked.
- Priority levels: low, medium, high, urgent.
- Wiki pages are global by default, project-scoped if project_id is set.
- Real-time WebSocket notifications on task/project changes (via kanban_ws service).

## Common Workflows
1. **Project Planning**: create_project -> create_project_task for each work item -> assign to team members
2. **Kanban Management**: tasks start at todo -> moved to in_progress -> completed -> get_project_status for progress
3. **Documentation**: create_wiki_page linked to project -> collaborate on docs -> keep updated with project changes
4. **Personal Tasks**: create_task for individual reminders -> update status -> track completion

## Edge Cases & Limitations
- No Kanban board columns configured - status values are flat, not board-aware.
- No task dependencies or blocking relationships (one task blocking another).
- Wiki pages are single-version, no revision history.
- No time tracking per task (only time_logs in the Finance module).
- No sprint/iteration support (Agile features not implemented).
- No file attachments to tasks or projects.
- WebSocket is available but no API surface exposed for direct usage.
- No Gantt chart or timeline views.""",

    "module_legal": """# Legal / Compliance Module

## Overview
The Legal module provides contract management, GDPR compliance tracking, whistleblower channel (in compliance with Spanish Law 2/2023), DSAR (Data Subject Access Request) support, and labor law compliance monitoring. It ensures the platform meets EU and Spanish regulatory requirements.

## API Endpoints
- **GET /api/v1/contracts** - List contracts. Filter by status: draft, pending_signature, active, expired. Limited to 50 results.
- **GET /api/v1/compliance** - Get compliance status overview: GDPR compliance (whistleblower channel, DSAR requests, encryption), FUNDAE validated enrollments count, labor law (active contracts, whistleblower reports).
- **POST /api/v1/whistleblower** - Submit a whistleblower report. Fields: title, description, category, is_anonymous. Returns tracking_code for anonymous follow-up. Status: open.

## Data Entities
### Contract
Fields: id, title, party_name, status (draft|pending_signature|active|expired), valid_from, valid_until, created_at.

### WhistleblowerReport
Fields: id, title, description, category, is_anonymous (bool), status (open|investigating|resolved), tracking_code, created_at.

## Business Rules & Validation
- **GDPR Compliance**: whistleblower channel must be active, DSAR requests must be enabled, encryption must be enabled.
- **Whistleblower Channel**: Compliant with Spanish Law 2/2023 (transposition of EU Directive 2019/1937).
- Reports can be anonymous or named. Anonymous reports receive a tracking_code.
- Contract status lifecycle: draft -> pending_signature -> active -> expired.
- Compliance checks are read-only aggregations of platform state.
- FUNDAE validation count is aggregated from FundaeValidation.overall_eligible=True.

## Common Workflows
1. **Contract Management**: create contract -> draft review -> send for signature -> pending_signature -> active -> monitor valid_until
2. **Whistleblower Report**: employee -> submit_whistleblower (anonymous or named) -> receives tracking_code -> compliance team investigates -> resolve
3. **Compliance Audit**: get_compliance_status -> review GDPR/FUNDAE/labor metrics -> identify gaps -> remediate
4. **GDPR DSAR**: data subject requests data -> compliance officer exports -> gdpr_export service generates report

## Edge Cases & Limitations
- Contract creation is not implemented as a tool (only read/list). Contract creation is done through DocuSign integration.
- Whistleblower reports are stored with status tracking but no investigation workflow steps.
- DSAR is mentioned as enabled but no dedicated API endpoint (uses gdpr_export service internally).
- No retention policy enforcement per document type.
- No automated contract expiry notifications.
- Compliance check values are hardcoded as True for GDPR/labor (placeholder for actual checks).
- Encryption check is declarative, not runtime verification.""",

    "module_intelligence": """# Intelligence / Analytics Module

## Overview
The Intelligence module provides business intelligence, configurable dashboards, KPI widgets, automated alerts, people analytics (turnover, diversity, engagement), and NLQ (Natural Language Query) for natural language data queries. It serves as the analytics layer across all platform modules.

## API Endpoints
- **GET /api/v1/dashboards** - List available dashboards with their widgets.
- **POST /api/v1/widgets** - Configure dashboard widgets with data sources and visualization types.
- **POST /api/v1/alerts** - Set KPI alerts with thresholds and notification recipients.
- **POST /api/v1/analytics/people** - Run people analytics queries (turnover rate, diversity metrics, engagement scores).
- **POST /api/v1/query** - Natural Language Query endpoint. Converts plain-text questions to SQL via LLM and returns results.
- **GET /api/v1/dashboard-summary** - AI-generated narrative summary of dashboard data.

## Business Rules & Validation
- Dashboards are role-scoped: each user role sees relevant KPIs.
- NLQ uses LLM (GPT-4o-mini by default) to convert natural language to SQL queries.
- People analytics respects data privacy by aggregating and anonymizing results.
- KPI alerts fire when thresholds are crossed and notify configured recipients.
- Widgets can source data from any platform module.
- Dashboard summary uses AI to generate plain-language insights from raw KPI data.

## Common Workflows
1. **Daily Standup**: manager -> views department dashboard -> reads dashboard_summary -> takes action on alerts
2. **People Analytics**: HR -> run turnover analysis -> diversity metrics -> present to leadership
3. **Ad-hoc Query**: user -> NLQ "how many employees joined last quarter?" -> get structured answer
4. **KPI Monitoring**: configure alert thresholds -> system monitors -> alert fires when KPI exceeds threshold

## Edge Cases & Limitations
- NLQ quality depends on LLM model quality and database schema understanding.
- No scheduled report generation or email distribution (planned).
- Dashboard widget types are limited to predefined visualization types.
- People analytics computations are point-in-time, no historical trend comparisons.
- No data export to CSV/Excel from dashboards (planned).
- No custom SQL query interface (NLQ only, no direct SQL access).""",

    "module_chat": """# Chat / Messaging Module

## Overview
The Chat module provides real-time messaging with rooms (channels), direct messages, file uploads, and user mentions. It serves as the internal communication backbone of the platform.

## API Endpoints
- **GET /api/v1/chat/rooms** - List chat rooms the user has access to.
- **POST /api/v1/chat/rooms** - Create a new chat room with members.
- **GET /api/v1/chat/rooms/{id}/messages** - Get message history for a room.
- **POST /api/v1/chat/rooms/{id}/messages** - Send a message to a room.
- **POST /api/v1/chat/direct/{user_id}** - Send a direct message to a user.
- **POST /api/v1/chat/upload** - Upload and share a file in a chat room.
- **POST /api/v1/chat/mentions** - Mention a user in a message with notification.

## Data Entities
### ChatRoom
Fields: id, name, type (channel|direct|group), created_by (FK User), members (JSON array), created_at.

### ChatMessage
Fields: id, room_id (FK), sender_id (FK User), content, attachments (JSON array), mentions (JSON array), created_at.

## Business Rules & Validation
- Messages are delivered in real-time via WebSocket (ws_notifications service).
- Direct messages are private between two users.
- Room members control who can read and send messages.
- File uploads are stored and referenced by URL in the message attachments array.
- Mentions trigger notifications to the mentioned user.
- Chat history is persisted and paginated.

## Common Workflows
1. **Team Communication**: create room -> add members -> send messages -> mention colleagues
2. **Direct Messaging**: search user -> send direct message -> continue thread
3. **File Sharing**: upload file -> share in room -> members access attachment

## Edge Cases & Limitations
- No message editing or deletion (messages are immutable).
- No read receipts or typing indicators.
- No message threading (flat conversation model).
- Room membership changes are not broadcast in real-time to existing members.
- No emoji reactions on messages.
- File size limits not enforced at API level (depends on infrastructure).""",

    "module_operations": """# Operations / Facilities Module

## Overview
The Operations module manages facility assets (rooms, equipment, resources), space bookings, and visitor management. It supports office facility management and resource scheduling.

## API Endpoints
- **GET /api/v1/operations/assets** - List facility assets (rooms, equipment). Filter by type and location.
- **POST /api/v1/operations/bookings** - Book a facility resource (room, desk, equipment) for a time slot.
- **GET /api/v1/operations/bookings** - List upcoming bookings, filter by resource or user.
- **POST /api/v1/operations/visitors** - Register a visitor with name, company, host, and visit date/time.
- **GET /api/v1/operations/visitors** - List registered visitors for a date range.

## Data Entities
### FacilityAsset
Fields: id, name, type (room|desk|equipment|vehicle), location, capacity, status (available|occupied|maintenance), created_at.

### FacilityBooking
Fields: id, asset_id (FK), user_id (FK), start_datetime, end_datetime, purpose, status (confirmed|cancelled), created_at.

### Visitor
Fields: id, full_name, company, host_id (FK User), visit_date, check_in, check_out, status (registered|checked_in|checked_out), created_at.

## Business Rules & Validation
- Bookings require asset availability check (no overlapping reservations).
- Visitor check-in/check-out timestamps are recorded for security compliance.
- Assets have capacity constraints (room capacity, equipment availability).
- Booking status lifecycle: confirmed -> cancelled (or completed after end time).
- Visitor status: registered -> checked_in -> checked_out.

## Common Workflows
1. **Room Booking**: employee -> check availability -> book room for meeting -> confirm -> use room
2. **Visitor Management**: host -> register visitor -> visitor arrives -> check_in -> visitor leaves -> check_out
3. **Asset Tracking**: operations manager -> list assets -> track maintenance -> update status

## Edge Cases & Limitations
- No recurring booking support (each booking is one-time).
- No automatic booking conflict resolution (manual intervention).
- Visitor pre-registration doesn't send notifications to host.
- Asset maintenance scheduling not integrated with bookings.
- No floor plan/map integration for room booking.
- No catering or services add-on for bookings.""",

    "module_agent_studio": """# Agent Studio Module

## Overview
Agent Studio is the AI agent creation and orchestration environment. It allows platform administrators to create, configure, and deploy AI agents with custom tools, system prompts, model selection, and ReAct pattern execution. It supports prompt versioning, A/B testing, and multi-agent orchestration.

## API Endpoints
- **POST /api/v1/agents** - Create a new AI agent with name, avatar, agent_type, AI model, system prompt, temperature, tone, guardrails, and agent_settings (tools).
- **GET /api/v1/agents** - List all agents for the tenant.
- **PUT /api/v1/agents/{id}** - Update agent configuration.
- **POST /api/v1/agents/{id}/run** - Execute an agent run with input payload. Supports tool calling loop and ReAct pattern.
- **POST /api/v1/agents/{id}/run/stream** - Execute agent with SSE streaming response.
- **POST /api/v1/prompts/version** - Create a new prompt version for an agent.
- **POST /api/v1/prompts/compare** - A/B test two prompt versions and compare results.
- **POST /api/v1/tools/register** - Register a new tool with schema and handler for an agent.
- **POST /api/v1/orchestration** - Configure multi-agent orchestration and delegation rules.

## Key Concepts
- **Agent Types**: conversational, crm, workflow, code, custom, omni_master, COPILOT.
- **ReAct Pattern**: Reasoning + Acting loop. Agent thinks step-by-step, decides on tool calls, executes, observes results, and iterates.
- **Prompt Versioning**: Track prompt iterations with version numbers and A/B test results.
- **Tool Registry**: Central registry of available tools with JSON schemas and handler functions.
- **Model Routing**: Automatic model selection based on task complexity (simple -> gpt-4o-mini, complex -> gpt-4o, code -> claude).
- **Agent Settings**: JSON config including ai_tools list, use_react_pattern flag, and API keys.

## Tools System
Available tools are defined in AVAILABLE_TOOLS_SCHEMA (tool_executor.py) and registered in TOOL_REGISTRY. Each tool has:
- Function name (unique identifier)
- Description (for LLM to understand when to use)
- Parameters schema (JSON Schema format)
- Handler function (async, takes db + arguments, returns JSON string)

## Business Rules & Validation
- Agent execution respects max_loops limit (default 10) to prevent infinite tool calling loops.
- Max tokens per run enforced (default 50000).
- Concurrent execution limited per tenant (concurrency_limiter).
- Agent runs log: execution trace, token usage, cost estimation, and latency.
- Prompt versioning preserves history for audit and rollback.

## Common Workflows
1. **Create Agent**: define agent type -> set system prompt -> configure tools -> set model and temperature -> deploy
2. **Test Agent**: run with test input -> review trace -> iterate on prompt -> version the prompt -> A/B test
3. **Deploy Agent**: configure triggers -> set up orchestration -> monitor execution history -> optimize
4. **Debug**: review execution_trace -> check tool calls and results -> adjust prompt or tools

## Edge Cases & Limitations
- Agent cannot modify its own configuration during execution.
- Tool registration is code-level (requires backend deployment), not runtime.
- Multi-agent orchestration is configured via JSON rules, no visual builder.
- ReAct pattern is optional (use_react_pattern: true), not default.
- No agent marketplace or sharing between tenants.
- Prompt versioning stores full prompt text, no diff-based storage.""",

    "module_workflows": """# Workflows / Process Automation Module

## Overview
The Workflows module provides process automation for employee lifecycle events (onboarding, offboarding) and custom business processes. It features natural language workflow generation, step-by-step execution with role assignment, SLA tracking, and AI-powered workflow optimization suggestions.

## API Endpoints
- **POST /api/v1/workflows/trigger** - Start a workflow for a user. Can search by template_name or specify workflow_template_id.
- **POST /api/v1/workflows/steps/complete** - Mark a workflow step as completed. Records completed_by and timestamp.
- **POST /api/v1/workflows/generate** - Generate a complete workflow from a natural language description. Creates template with steps, responsible roles, and SLAs.
- **POST /api/v1/workflows/analyze** - Analyze existing workflow and suggest optimizations: parallelizable steps, redundant approvals, missing notifications, SLA improvements.

## Data Entities
### WorkflowTemplate
Fields: id, name, description, steps (JSON array of step definitions), created_at.

### UserWorkflow
Fields: id, template_id (FK), user_id (FK), status (active|completed|cancelled), started_at, completed_at.

### WorkflowStep
Fields: id, workflow_id (FK), step_name, description, responsible_role, sla_hours, status (pending|in_progress|completed|skipped), completed_by, completed_at.

## Business Rules & Validation
- **Onboarding Workflows**: Standard steps include IT equipment setup, email account creation, team introduction, initial training, 30-day check-in.
- **Offboarding Workflows**: Standard steps include access revocation, exit interview, equipment return, document handover, final paycheck.
- Natural language generation: LLM interprets description and creates structured step definitions.
- Each step has a responsible_role (who should complete it) and sla_hours (completion deadline).
- Workflow analysis looks for: parallelizable steps, redundant approvals, missing notification steps, SLA optimization.
- Steps are completed sequentially by default, but can be parallelized based on analysis suggestions.

## Common Workflows
1. **New Employee Onboarding**: HR -> trigger_workflow (template_name="Onboarding") -> steps assigned to IT/HR/manager -> complete_workflow_step as tasks are done
2. **Employee Offboarding**: HR -> trigger_workflow (template_name="Offboarding") -> revoke access -> collect equipment -> exit interview -> complete
3. **Custom Process**: describe process in natural language -> create_workflow_from_description -> review generated steps -> trigger on employees
4. **Process Optimization**: analyze_workflow -> review suggestions -> implement improvements -> re-deploy

## Edge Cases & Limitations
- No conditional branching within workflows (linear step progression only).
- No timer-based automatic step advancement (requires manual completion).
- Workflow templates are per-tenant, no cross-tenant template sharing.
- No integration with external systems for automated steps (e.g., automatically create AD account).
- SLA tracking calculates hours but doesn't send automatic reminders.
- No workflow pause/resume capability.
- Step dependencies are implicit (order in array), not explicit dependency graph."""
}

PLATFORM_COPILOT_AGENT_ID = None


async def build_platform_knowledge_index(db: AsyncSession) -> dict:
    """
    Indexes all platform knowledge documents into the RAG knowledge base.
    Uses the COPILOT agent as the document owner. Creates the agent if it doesn't exist.
    Returns count of documents indexed.
    """
    from app.models.agent import Agent, AgentConfig

    global PLATFORM_COPILOT_AGENT_ID

    # Find or create the COPILOT agent as the document owner
    agent_res = await db.execute(select(Agent).where(Agent.agent_type == "COPILOT"))
    agent = agent_res.scalar_one_or_none()

    if not agent:
        agent = Agent(
            id=uuid.uuid4().hex,
            name="Copiloto de Plataforma",
            avatar="\U0001f916",
            agent_type="COPILOT",
            ai_model="meta-llama/llama-3.3-70b-instruct:free",
            ai_system_prompt="Knowledge index agent for SuccessCore platform documentation.",
            ai_temperature=0.2,
            ai_tone="Profesional y resolutivo",
            agent_settings={},
        )
        db.add(agent)
        await db.flush()

        config = AgentConfig(
            id=uuid.uuid4().hex,
            agent_id=agent.id,
            max_loops=10,
            max_tokens_per_run=50000,
        )
        db.add(config)
        await db.commit()
        await db.refresh(agent)

    PLATFORM_COPILOT_AGENT_ID = agent.id

    indexed_count = 0
    for doc_key, doc_content in PLATFORM_KNOWLEDGE_DOCUMENTS.items():
        # Check if this document already exists to avoid duplicates
        existing_res = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.agent_id == agent.id,
                KnowledgeDocument.filename == doc_key,
            )
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            logger.info(f"Document {doc_key} already indexed, skipping.")
            continue

        try:
            await add_document_to_knowledge(
                db=db,
                agent_id=agent.id,
                filename=doc_key,
                content=doc_content,
            )
            indexed_count += 1
            logger.info(f"Indexed document: {doc_key}")
        except Exception as e:
            logger.error(f"Failed to index document {doc_key}: {e}")

    await db.commit()
    logger.info(f"Platform knowledge index built: {indexed_count} documents indexed.")
    return {"documents_indexed": indexed_count, "agent_id": agent.id}


async def query_platform_knowledge(
    query: str,
    db: AsyncSession,
    limit: int = 3,
) -> str:
    """
    Queries the platform knowledge base and returns formatted context.
    Used by the copilot to inject platform-specific knowledge into its context.
    """
    global PLATFORM_COPILOT_AGENT_ID

    if not PLATFORM_COPILOT_AGENT_ID:
        agent_res = await db.execute(select(Agent).where(Agent.agent_type == "COPILOT").limit(1))
        agent = agent_res.scalars().first()
        if not agent:
            return ""
        PLATFORM_COPILOT_AGENT_ID = agent.id

    try:
        chunks = await query_knowledge_base(
            db=db,
            agent_id=PLATFORM_COPILOT_AGENT_ID,
            query_text=query,
            limit=limit,
        )
        if not chunks:
            return ""

        knowledge_parts = []
        for c in chunks:
            knowledge_parts.append(
                f"- [Relevancia: {c.get('similarity', 0):.2f}] {c.get('content', '')[:500]}"
            )

        return "\n[CONOCIMIENTO RELEVANTE DE LA PLATAFORMA]\n" + "\n".join(knowledge_parts)
    except Exception as e:
        logger.error(f"Error querying platform knowledge: {e}")
        return ""
