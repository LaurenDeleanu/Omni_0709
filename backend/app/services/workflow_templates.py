import logging
from typing import Dict, Any, List

logger = logging.getLogger("successcore.workflow_templates")

WORKFLOW_TEMPLATES = [
    {
        "id": "onboarding_standard",
        "name": "Standard Employee Onboarding",
        "description": "Complete onboarding workflow for new employees: welcome email, IT setup, training enrollment, buddy assignment, and first-week check-in.",
        "category": "hr",
        "icon": "UserPlus",
        "estimated_duration_days": 7,
        "steps": [
            {"order": 1, "name": "Send Welcome Email", "type": "notification", "template": "welcome_email"},
            {"order": 2, "name": "Create IT Accounts", "type": "task", "assignee": "it_admin", "description": "Email, VPN, and tool access"},
            {"order": 3, "name": "Assign Onboarding Buddy", "type": "task", "assignee": "hr_admin", "description": "Pair with experienced team member"},
            {"order": 4, "name": "Enroll in Mandatory Training", "type": "task", "assignee": "employee", "description": "Security, compliance, and role-specific courses"},
            {"order": 5, "name": "First-Week Check-in", "type": "meeting", "attendees": ["manager", "employee"], "scheduled_days_after": 5},
            {"order": 6, "name": "HR Documentation Review", "type": "approval", "assignee": "hr_admin", "description": "Verify all documents signed"},
        ],
        "metrics": {"time_to_productivity": "Improves 30-60 day ramp-up"},
    },
    {
        "id": "offboarding_standard",
        "name": "Employee Offboarding",
        "description": "Structured offboarding: exit interview, asset recovery, account deactivation, knowledge transfer, and final documentation.",
        "category": "hr",
        "icon": "UserMinus",
        "estimated_duration_days": 3,
        "steps": [
            {"order": 1, "name": "Exit Interview Scheduling", "type": "meeting", "attendees": ["hr_admin", "employee"], "scheduled_days_after": 1},
            {"order": 2, "name": "Asset Recovery", "type": "task", "assignee": "it_admin", "description": "Laptop, phone, access cards, keys"},
            {"order": 3, "name": "Account Deactivation", "type": "task", "assignee": "it_admin", "description": "Email, VPN, SaaS tools"},
            {"order": 4, "name": "Knowledge Transfer", "type": "task", "assignee": "manager", "description": "Documentation handover"},
            {"order": 5, "name": "Final Settlement", "type": "approval", "assignee": "payroll_admin", "description": "Calculate final pay and benefits"},
        ],
    },
    {
        "id": "expense_approval",
        "name": "Expense Report Approval",
        "description": "Multi-level expense approval: employee submission, manager review, finance validation, and payment processing.",
        "category": "finance",
        "icon": "Receipt",
        "estimated_duration_days": 5,
        "steps": [
            {"order": 1, "name": "Submit Expense Report", "type": "form", "assignee": "employee", "fields": ["amount_cents", "category", "description", "receipt_url"]},
            {"order": 2, "name": "Manager Approval", "type": "approval", "assignee": "manager", "condition": "amount < 500"},
            {"order": 3, "name": "Finance Review", "type": "approval", "assignee": "finance_admin", "condition": "amount >= 500"},
            {"order": 4, "name": "Payment Processing", "type": "task", "assignee": "finance_admin", "description": "Schedule reimbursement"},
        ],
    },
    {
        "id": "leave_request",
        "name": "Leave/Vacation Request",
        "description": "Standard leave request flow: employee submission, manager approval, HR verification, and calendar update.",
        "category": "hr",
        "icon": "Calendar",
        "estimated_duration_days": 2,
        "steps": [
            {"order": 1, "name": "Submit Leave Request", "type": "form", "assignee": "employee", "fields": ["start_date", "end_date", "reason"]},
            {"order": 2, "name": "Manager Approval", "type": "approval", "assignee": "manager"},
            {"order": 3, "name": "HR Verification", "type": "task", "assignee": "hr_admin", "description": "Check PTO balance and coverage"},
            {"order": 4, "name": "Calendar Update", "type": "webhook", "endpoint": "/api/v1/calendar/sync"},
            {"order": 5, "name": "Notify Team", "type": "notification", "template": "leave_notification"},
        ],
    },
    {
        "id": "performance_review",
        "name": "Performance Review Cycle",
        "description": "Quarterly performance review: self-assessment, manager review, peer feedback collection, and 1:1 discussion.",
        "category": "performance",
        "icon": "Target",
        "estimated_duration_days": 14,
        "steps": [
            {"order": 1, "name": "Self-Assessment", "type": "form", "assignee": "employee", "due_days": 3},
            {"order": 2, "name": "Peer Feedback Collection", "type": "task", "assignee": "hr_admin", "description": "Send 360 feedback requests to 3-5 peers"},
            {"order": 3, "name": "Manager Assessment", "type": "form", "assignee": "manager", "due_days": 5},
            {"order": 4, "name": "1:1 Discussion Meeting", "type": "meeting", "attendees": ["manager", "employee"], "scheduled_days_after": 10},
            {"order": 5, "name": "Goal Setting for Next Quarter", "type": "task", "assignee": "employee", "description": "Set 3-5 OKRs with manager"},
            {"order": 6, "name": "HR Review & Filing", "type": "approval", "assignee": "hr_admin"},
        ],
    },
    {
        "id": "it_ticket_triage",
        "name": "IT Support Ticket Triage",
        "description": "IT ticket management: auto-categorization, assignment, resolution, and user notification.",
        "category": "it",
        "icon": "Wrench",
        "estimated_duration_days": 1,
        "steps": [
            {"order": 1, "name": "Auto-Categorize Ticket", "type": "ai_task", "assignee": "it_helpdesk", "description": "Categorize and prioritize incoming ticket"},
            {"order": 2, "name": "Assign to Technician", "type": "task", "assignee": "it_admin", "description": "Route to appropriate IT specialist"},
            {"order": 3, "name": "Resolution", "type": "task", "assignee": "assigned_tech", "description": "Resolve and document solution"},
            {"order": 4, "name": "User Confirmation", "type": "approval", "assignee": "requester", "description": "Confirm issue resolved"},
            {"order": 5, "name": "KB Article Generation", "type": "ai_task", "assignee": "it_helpdesk", "description": "Auto-generate knowledge base article from resolution"},
        ],
    },
    {
        "id": "recruitment_pipeline",
        "name": "Recruitment Pipeline",
        "description": "End-to-end hiring: job posting, candidate screening, interviews, offer, and onboarding handoff.",
        "category": "recruitment",
        "icon": "Briefcase",
        "estimated_duration_days": 21,
        "steps": [
            {"order": 1, "name": "Job Posting Creation", "type": "form", "assignee": "recruiter", "fields": ["title", "description", "requirements", "department", "salary_range"]},
            {"order": 2, "name": "Candidate Screening", "type": "ai_task", "assignee": "recruiter", "description": "AI-powered resume screening and ranking"},
            {"order": 3, "name": "Phone Screen", "type": "meeting", "attendees": ["recruiter", "candidate"], "scheduled_days_after": 3},
            {"order": 4, "name": "Technical Interview", "type": "meeting", "attendees": ["hiring_manager", "candidate"], "scheduled_days_after": 7},
            {"order": 5, "name": "Offer Letter Generation", "type": "task", "assignee": "hr_admin", "description": "Generate and send offer with DocuSign"},
            {"order": 6, "name": "Onboarding Handoff", "type": "trigger", "target_workflow": "onboarding_standard"},
        ],
    },
    {
        "id": "payroll_processing",
        "name": "Monthly Payroll Processing",
        "description": "End-to-end payroll: data validation, calculation, review, approval, payment generation, and SEPA export.",
        "category": "payroll",
        "icon": "DollarSign",
        "estimated_duration_days": 3,
        "steps": [
            {"order": 1, "name": "Gather Time & Attendance Data", "type": "task", "assignee": "hr_admin", "description": "Collect clock-ins, absences, overtime"},
            {"order": 2, "name": "Validate Employee Data", "type": "ai_task", "assignee": "payroll_specialist", "description": "Check for anomalies, missing data"},
            {"order": 3, "name": "Calculate Payroll", "type": "ai_task", "assignee": "payroll_specialist", "description": "Generate payslips with taxes and deductions"},
            {"order": 4, "name": "Manager Review", "type": "approval", "assignee": "finance_admin"},
            {"order": 5, "name": "Generate SEPA File", "type": "task", "assignee": "payroll_admin", "description": "Export SEPA XML for bank"},
            {"order": 6, "name": "Notify Employees", "type": "notification", "template": "payslip_available"},
        ],
    },
]


def get_template(template_id: str) -> dict:
    for t in WORKFLOW_TEMPLATES:
        if t["id"] == template_id:
            return t
    return {}


def list_templates(category: str = "") -> List[Dict[str, Any]]:
    filtered = [
        {
            "id": t["id"], "name": t["name"], "description": t["description"],
            "category": t["category"], "icon": t["icon"],
            "estimate_duration_days": t["estimated_duration_days"],
            "step_count": len(t["steps"]),
        }
        for t in WORKFLOW_TEMPLATES
        if not category or t["category"] == category
    ]
    return filtered


def get_categories() -> List[str]:
    return sorted(set(t["category"] for t in WORKFLOW_TEMPLATES))
