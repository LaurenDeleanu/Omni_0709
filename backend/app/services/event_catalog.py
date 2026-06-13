# app/services/event_catalog.py — Canonical domain event types and publisher
# All modules should use these constants for event type strings.

# ── HR Core Events ─────────────────────────────────────────────────────────────
EMPLOYEE_CREATED          = "employee.created"
EMPLOYEE_UPDATED          = "employee.updated"
EMPLOYEE_ARCHIVED         = "employee.archived"
EMPLOYEE_DELETED          = "employee.deleted"
EMPLOYEE_REACTIVATED      = "employee.reactivated"
SALARY_CHANGED            = "salary.changed"
ROLE_CHANGED              = "role.changed"
DEPARTMENT_CHANGED        = "department.changed"
PROFILE_CHANGE_REQUESTED  = "profile.change_requested"
PROFILE_CHANGE_APPROVED   = "profile.change_approved"
PROFILE_CHANGE_REJECTED   = "profile.change_rejected"

# ── Calendar / Time-Off Events ──────────────────────────────────────────────────
VACATION_REQUESTED        = "vacation.requested"
VACATION_APPROVED         = "vacation.approved"
VACATION_REJECTED         = "vacation.rejected"
MEETING_CREATED           = "meeting.created"
TASK_ASSIGNED             = "task.assigned"

# ── Payroll Events ──────────────────────────────────────────────────────────────
PAYROLL_CYCLE_CREATED     = "payroll.cycle_created"
PAYROLL_PROCESSED         = "payroll.processed"
PAYSLIP_GENERATED         = "payslip.generated"
BONUS_CREATED             = "bonus.created"

# ── Recruitment Events ──────────────────────────────────────────────────────────
JOB_POSTED                = "job.posted"
CANDIDATE_ADDED           = "candidate.added"
CANDIDATE_STAGE_CHANGED   = "candidate.stage_changed"
CANDIDATE_HIRED           = "candidate.hired"
INTERVIEW_SCHEDULED       = "interview.scheduled"

# ── Training Events ─────────────────────────────────────────────────────────────
COURSE_CREATED            = "course.created"
TRAINING_ENROLLED         = "training.enrolled"
COURSE_COMPLETED          = "course.completed"
CERTIFICATION_EXPIRING    = "certification.expiring"

# ── Performance / Grow Events ───────────────────────────────────────────────────
OBJECTIVE_CREATED         = "objective.created"
OBJECTIVE_COMPLETED       = "objective.completed"
REVIEW_STARTED            = "review.started"
REVIEW_COMPLETED          = "review.completed"

# ── IT Events ──────────────────────────────────────────────────────────────────
IT_TICKET_CREATED         = "it.ticket_created"
IT_TICKET_RESOLVED        = "it.ticket_resolved"
IT_ASSET_ASSIGNED         = "it.asset_assigned"
IT_ASSET_RETIRED          = "it.asset_retired"

# ── Finance Events ──────────────────────────────────────────────────────────────
EXPENSE_SUBMITTED         = "expense.submitted"
EXPENSE_APPROVED          = "expense.approved"
EXPENSE_REJECTED          = "expense.rejected"

# ── Work / Project Events ───────────────────────────────────────────────────────
PROJECT_CREATED           = "project.created"
TASK_STATUS_CHANGED       = "task.status_changed"
SPRINT_STARTED            = "sprint.started"
SPRINT_COMPLETED          = "sprint.completed"

# ── Workflow Events ─────────────────────────────────────────────────────────────
WORKFLOW_ASSIGNED         = "workflow.assigned"
WORKFLOW_STEP_COMPLETED    = "workflow.step_completed"
ONBOARDING_COMPLETED      = "onboarding.completed"
OFFBOARDING_COMPLETED     = "offboarding.completed"

# ── Notification / Collab Events ────────────────────────────────────────────────
NOTIFICATION_CREATED      = "notification.created"
KUDOS_RECEIVED            = "kudos.received"
ANNOUNCEMENT_CREATED      = "announcement.created"

# ── AI Agent Events ─────────────────────────────────────────────────────────────
AGENT_RUN_STARTED         = "agent.run_started"
AGENT_RUN_COMPLETED       = "agent.run_completed"
AGENT_CREATED             = "agent.created"

# ── Legal / Compliance Events ──────────────────────────────────────────────────
CONTRACT_CREATED          = "contract.created"
CONTRACT_EXPIRING         = "contract.expiring"
WHISTLEBLOWER_REPORTED    = "whistleblower.reported"

# ── All event types for validation ──────────────────────────────────────────────
ALL_EVENT_TYPES = frozenset({
    EMPLOYEE_CREATED, EMPLOYEE_UPDATED, EMPLOYEE_ARCHIVED, EMPLOYEE_DELETED,
    EMPLOYEE_REACTIVATED, SALARY_CHANGED, ROLE_CHANGED, DEPARTMENT_CHANGED,
    PROFILE_CHANGE_REQUESTED, PROFILE_CHANGE_APPROVED, PROFILE_CHANGE_REJECTED,
    VACATION_REQUESTED, VACATION_APPROVED, VACATION_REJECTED,
    MEETING_CREATED, TASK_ASSIGNED,
    PAYROLL_CYCLE_CREATED, PAYROLL_PROCESSED, PAYSLIP_GENERATED, BONUS_CREATED,
    JOB_POSTED, CANDIDATE_ADDED, CANDIDATE_STAGE_CHANGED, CANDIDATE_HIRED, INTERVIEW_SCHEDULED,
    COURSE_CREATED, TRAINING_ENROLLED, COURSE_COMPLETED, CERTIFICATION_EXPIRING,
    OBJECTIVE_CREATED, OBJECTIVE_COMPLETED, REVIEW_STARTED, REVIEW_COMPLETED,
    IT_TICKET_CREATED, IT_TICKET_RESOLVED, IT_ASSET_ASSIGNED, IT_ASSET_RETIRED,
    EXPENSE_SUBMITTED, EXPENSE_APPROVED, EXPENSE_REJECTED,
    PROJECT_CREATED, TASK_STATUS_CHANGED, SPRINT_STARTED, SPRINT_COMPLETED,
    WORKFLOW_ASSIGNED, WORKFLOW_STEP_COMPLETED, ONBOARDING_COMPLETED, OFFBOARDING_COMPLETED,
    NOTIFICATION_CREATED, KUDOS_RECEIVED, ANNOUNCEMENT_CREATED,
    AGENT_RUN_STARTED, AGENT_RUN_COMPLETED, AGENT_CREATED,
    CONTRACT_CREATED, CONTRACT_EXPIRING, WHISTLEBLOWER_REPORTED,
})
