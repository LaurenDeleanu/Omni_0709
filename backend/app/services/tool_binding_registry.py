import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

TOOL_BINDINGS: Dict[str, Dict[str, str]] = {
    # ── HR Module (17 tools) ──
    "create_employee": {"tool": "create_employee", "module": "hr", "category": "create", "requires_role": "hr_admin"},
    "update_employee": {"tool": "update_employee", "module": "hr", "category": "update", "requires_role": "hr_admin"},
    "archive_employee": {"tool": "archive_employee", "module": "hr", "category": "delete", "requires_role": "hr_admin"},
    "get_employee_profile": {"tool": "get_employee_profile", "module": "hr", "category": "read", "requires_role": "employee"},
    "search_employees": {"tool": "search_employees", "module": "hr", "category": "read", "requires_role": "employee"},
    "search_employees_advanced": {"tool": "search_employees_advanced", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_employee_profile_full": {"tool": "get_employee_profile_full", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_org_chart": {"tool": "get_org_chart", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_span_of_control": {"tool": "get_span_of_control", "module": "hr", "category": "read", "requires_role": "manager"},
    "get_pto_balance": {"tool": "get_pto_balance", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_department_members": {"tool": "get_department_members", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_recent_hires": {"tool": "get_recent_hires", "module": "hr", "category": "read", "requires_role": "employee"},
    "list_department_members": {"tool": "list_department_members", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_vacation_balance": {"tool": "get_vacation_balance", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_department_stats": {"tool": "get_department_stats", "module": "hr", "category": "read", "requires_role": "manager"},
    "get_company_announcements": {"tool": "get_company_announcements", "module": "hr", "category": "read", "requires_role": "employee"},
    "generate_onboarding_plan": {"tool": "generate_onboarding_plan", "module": "hr", "category": "action", "requires_role": "manager"},
    "assign_onboarding_buddy": {"tool": "assign_onboarding_buddy", "module": "hr", "category": "action", "requires_role": "manager"},

    # ── Calendar Module (6 tools) ──
    "request_vacation": {"tool": "request_vacation", "module": "calendar", "category": "create", "requires_role": "employee"},
    "approve_vacation": {"tool": "approve_vacation", "module": "calendar", "category": "update", "requires_role": "manager"},
    "book_vacation": {"tool": "book_vacation", "module": "calendar", "category": "create", "requires_role": "employee"},
    "get_team_calendar": {"tool": "get_team_calendar", "module": "calendar", "category": "read", "requires_role": "employee"},
    "get_upcoming_vacations": {"tool": "get_upcoming_vacations", "module": "calendar", "category": "read", "requires_role": "employee"},
    "create_meeting": {"tool": "create_meeting", "module": "calendar", "category": "create", "requires_role": "employee"},
    "get_work_schedule": {"tool": "get_work_schedule", "module": "calendar", "category": "read", "requires_role": "employee"},

    # ── Payroll Module (7 tools) ──
    "create_payroll_cycle": {"tool": "create_payroll_cycle", "module": "payroll", "category": "create", "requires_role": "hr_admin"},
    "process_payroll": {"tool": "process_payroll", "module": "payroll", "category": "action", "requires_role": "hr_admin"},
    "get_payslip": {"tool": "get_payslip", "module": "payroll", "category": "read", "requires_role": "employee"},
    "get_tax_rules": {"tool": "get_tax_rules", "module": "payroll", "category": "read", "requires_role": "employee"},
    "update_compensation": {"tool": "update_compensation", "module": "payroll", "category": "update", "requires_role": "hr_admin"},
    "create_bonus": {"tool": "create_bonus", "module": "payroll", "category": "create", "requires_role": "hr_admin"},

    # ── Finance Module (8 tools) ──
    "get_financial_ledger": {"tool": "get_financial_ledger", "module": "finance", "category": "read", "requires_role": "manager"},
    "get_expense_summary": {"tool": "get_expense_summary", "module": "finance", "category": "read", "requires_role": "employee"},
    "get_expense_summary_agg": {"tool": "get_expense_summary_agg", "module": "finance", "category": "read", "requires_role": "manager"},
    "create_expense": {"tool": "create_expense", "module": "finance", "category": "create", "requires_role": "employee"},
    "clock_in": {"tool": "clock_in", "module": "finance", "category": "create", "requires_role": "employee"},
    "clock_out": {"tool": "clock_out", "module": "finance", "category": "update", "requires_role": "employee"},
    "get_time_logs": {"tool": "get_time_logs", "module": "finance", "category": "read", "requires_role": "employee"},

    # ── IT Module (8 tools) ──
    "create_it_ticket": {"tool": "create_it_ticket", "module": "it", "category": "create", "requires_role": "employee"},
    "assign_it_ticket": {"tool": "assign_it_ticket", "module": "it", "category": "update", "requires_role": "it_admin"},
    "resolve_it_ticket": {"tool": "resolve_it_ticket", "module": "it", "category": "update", "requires_role": "it_admin"},
    "get_it_assets": {"tool": "get_it_assets", "module": "it", "category": "read", "requires_role": "employee"},
    "get_ticket_stats": {"tool": "get_ticket_stats", "module": "it", "category": "read", "requires_role": "it_admin"},
    "search_it_knowledge_base": {"tool": "search_it_knowledge_base", "module": "it", "category": "read", "requires_role": "employee"},
    "auto_tag_it_ticket": {"tool": "auto_tag_it_ticket", "module": "it", "category": "action", "requires_role": "it_admin"},
    "suggest_it_solution": {"tool": "suggest_it_solution", "module": "it", "category": "read", "requires_role": "it_admin"},

    # ── Training Module (5 tools) ──
    "enroll_in_course": {"tool": "enroll_in_course", "module": "training", "category": "create", "requires_role": "employee"},
    "get_training_progress": {"tool": "get_training_progress", "module": "training", "category": "read", "requires_role": "employee"},
    "get_course_catalog": {"tool": "get_course_catalog", "module": "training", "category": "read", "requires_role": "employee"},
    "recommend_courses": {"tool": "recommend_courses", "module": "training", "category": "read", "requires_role": "employee"},
    "validate_fundae": {"tool": "validate_fundae", "module": "training", "category": "action", "requires_role": "manager"},

    # ── Recruitment Module (10 tools) ──
    "create_job_posting": {"tool": "create_job_posting", "module": "recruitment", "category": "create", "requires_role": "manager"},
    "add_candidate": {"tool": "add_candidate", "module": "recruitment", "category": "create", "requires_role": "manager"},
    "move_candidate_stage": {"tool": "move_candidate_stage", "module": "recruitment", "category": "update", "requires_role": "manager"},
    "schedule_interview": {"tool": "schedule_interview", "module": "recruitment", "category": "create", "requires_role": "manager"},
    "get_job_applications": {"tool": "get_job_applications", "module": "recruitment", "category": "read", "requires_role": "manager"},
    "get_pipeline_stats": {"tool": "get_pipeline_stats", "module": "recruitment", "category": "read", "requires_role": "manager"},
    "promote_to_employee": {"tool": "promote_to_employee", "module": "recruitment", "category": "action", "requires_role": "hr_admin"},
    "parse_resume": {"tool": "parse_resume", "module": "recruitment", "category": "action", "requires_role": "manager"},
    "screen_resume": {"tool": "screen_resume", "module": "recruitment", "category": "action", "requires_role": "manager"},
    "screen_candidate": {"tool": "screen_candidate", "module": "recruitment", "category": "action", "requires_role": "manager"},
    "match_candidate_to_job": {"tool": "match_candidate_to_job", "module": "recruitment", "category": "action", "requires_role": "manager"},
    "rank_candidates": {"tool": "rank_candidates", "module": "recruitment", "category": "action", "requires_role": "manager"},
    "generate_interview_questions": {"tool": "generate_interview_questions", "module": "recruitment", "category": "action", "requires_role": "manager"},

    # ── Performance / Grow Module (8 tools) ──
    "create_okr": {"tool": "create_okr", "module": "performance", "category": "create", "requires_role": "employee"},
    "update_key_result": {"tool": "update_key_result", "module": "performance", "category": "update", "requires_role": "employee"},
    "create_review": {"tool": "create_review", "module": "performance", "category": "create", "requires_role": "manager"},
    "get_team_okrs": {"tool": "get_team_okrs", "module": "performance", "category": "read", "requires_role": "employee"},
    "get_kudos_received": {"tool": "get_kudos_received", "module": "performance", "category": "read", "requires_role": "employee"},
    "get_kudos_leaderboard": {"tool": "get_kudos_leaderboard", "module": "performance", "category": "read", "requires_role": "employee"},
    "create_kudos": {"tool": "create_kudos", "module": "performance", "category": "create", "requires_role": "employee"},
    "generate_smart_goals": {"tool": "generate_smart_goals", "module": "performance", "category": "action", "requires_role": "employee"},
    "suggest_goal_adjustments": {"tool": "suggest_goal_adjustments", "module": "performance", "category": "action", "requires_role": "manager"},

    # ── CRM / Sales Module (9 tools) ──
    "get_pipeline_overview": {"tool": "get_pipeline_overview", "module": "crm", "category": "read", "requires_role": "manager"},
    "get_client_details": {"tool": "get_client_details", "module": "crm", "category": "read", "requires_role": "manager"},
    "search_clients": {"tool": "search_clients", "module": "crm", "category": "read", "requires_role": "employee"},
    "get_deal_stats": {"tool": "get_deal_stats", "module": "crm", "category": "read", "requires_role": "manager"},
    "create_task_for_lead": {"tool": "create_task_for_lead", "module": "crm", "category": "create", "requires_role": "manager"},
    "log_lead_activity": {"tool": "log_lead_activity", "module": "crm", "category": "create", "requires_role": "employee"},
    "create_client": {"tool": "create_client", "module": "crm", "category": "create", "requires_role": "manager"},
    "score_lead": {"tool": "score_lead", "module": "crm", "category": "action", "requires_role": "manager"},
    "suggest_sales_action": {"tool": "suggest_sales_action", "module": "crm", "category": "action", "requires_role": "manager"},
    "generate_email_template": {"tool": "generate_email_template", "module": "crm", "category": "action", "requires_role": "manager"},

    # ── Projects / Work Module (5 tools) ──
    "create_project": {"tool": "create_project", "module": "projects", "category": "create", "requires_role": "manager"},
    "create_project_task": {"tool": "create_project_task", "module": "projects", "category": "create", "requires_role": "employee"},
    "get_project_status": {"tool": "get_project_status", "module": "projects", "category": "read", "requires_role": "employee"},
    "create_wiki_page": {"tool": "create_wiki_page", "module": "projects", "category": "create", "requires_role": "employee"},
    "create_task": {"tool": "create_task", "module": "projects", "category": "create", "requires_role": "employee"},

    # ── Legal Module (3 tools) ──
    "get_contracts": {"tool": "get_contracts", "module": "legal", "category": "read", "requires_role": "manager"},
    "get_compliance_status": {"tool": "get_compliance_status", "module": "legal", "category": "read", "requires_role": "manager"},
    "submit_whistleblower": {"tool": "submit_whistleblower", "module": "legal", "category": "create", "requires_role": "employee"},

    # ── Workflows Module (4 tools) ──
    "trigger_workflow": {"tool": "trigger_workflow", "module": "workflows", "category": "action", "requires_role": "manager"},
    "complete_workflow_step": {"tool": "complete_workflow_step", "module": "workflows", "category": "update", "requires_role": "employee"},
    "create_workflow_from_description": {"tool": "create_workflow_from_description", "module": "workflows", "category": "create", "requires_role": "manager"},
    "analyze_workflow": {"tool": "analyze_workflow", "module": "workflows", "category": "read", "requires_role": "manager"},

    # ── HR Extended (4 tools) ──
    "get_employee_attendance": {"tool": "get_employee_attendance", "module": "hr", "category": "read", "requires_role": "manager"},
    "get_employee_documents": {"tool": "get_employee_documents", "module": "hr", "category": "read", "requires_role": "employee"},
    "get_compensation_benchmarks": {"tool": "get_compensation_benchmarks", "module": "hr", "category": "read", "requires_role": "manager"},

    # ── Finance Extended (1 tool) ──
    "get_budget_summary": {"tool": "get_budget_summary", "module": "finance", "category": "read", "requires_role": "manager"},

    # ── CRM Extended (2 tools) ──
    "update_deal_stage": {"tool": "update_deal_stage", "module": "crm", "category": "update", "requires_role": "manager"},
    "get_activity_timeline": {"tool": "get_activity_timeline", "module": "crm", "category": "read", "requires_role": "employee"},

    # ── Projects Extended (2 tools) ──
    "get_project_timeline": {"tool": "get_project_timeline", "module": "projects", "category": "read", "requires_role": "employee"},
    "update_task_status": {"tool": "update_task_status", "module": "projects", "category": "update", "requires_role": "employee"},

    # ── Performance Extended (3 tools) ──
    "get_my_okrs": {"tool": "get_my_okrs", "module": "performance", "category": "read", "requires_role": "employee"},
    "get_review_feedback": {"tool": "get_review_feedback", "module": "performance", "category": "read", "requires_role": "employee"},
    "generate_career_path": {"tool": "generate_career_path", "module": "performance", "category": "read", "requires_role": "employee"},

    # ── Legal Extended (1 tool) ──
    "get_gdpr_export": {"tool": "get_gdpr_export", "module": "legal", "category": "read", "requires_role": "employee"},

    # ── Platform Extended (7 tools) ──
    "create_announcement": {"tool": "create_announcement", "module": "platform", "category": "create", "requires_role": "manager"},
    "get_workflow_templates": {"tool": "get_workflow_templates", "module": "workflows", "category": "read", "requires_role": "employee"},
    "get_workflow_status": {"tool": "get_workflow_status", "module": "workflows", "category": "read", "requires_role": "employee"},
    "get_user_notifications": {"tool": "get_user_notifications", "module": "platform", "category": "read", "requires_role": "employee"},
    "mark_notification_read": {"tool": "mark_notification_read", "module": "platform", "category": "update", "requires_role": "employee"},
    "get_active_integrations": {"tool": "get_active_integrations", "module": "platform", "category": "read", "requires_role": "employee"},
    "get_tenant_config": {"tool": "get_tenant_config", "module": "platform", "category": "read", "requires_role": "employee"},
    "get_billing_status": {"tool": "get_billing_status", "module": "platform", "category": "read", "requires_role": "manager"},
    "get_surveys": {"tool": "get_surveys", "module": "platform", "category": "read", "requires_role": "employee"},
    "get_chat_channels": {"tool": "get_chat_channels", "module": "platform", "category": "read", "requires_role": "employee"},
    "search_messages": {"tool": "search_messages", "module": "platform", "category": "read", "requires_role": "employee"},
}


async def get_tools_for_role(role: str) -> list:
    """Returns tool names that the given role can use."""
    return [
        name
        for name, binding in TOOL_BINDINGS.items()
        if binding["requires_role"] == role or binding["requires_role"] in ("employee",)
        and role != "employee"
    ]


async def get_module_tools(module_name: str) -> list:
    """Returns all tools for a given module with their metadata."""
    return [
        {"name": name, **binding}
        for name, binding in TOOL_BINDINGS.items()
        if binding["module"] == module_name
    ]


async def build_copilot_tool_list(user_roles: list) -> list:
    """
    Builds the complete tool list for the copilot based on the user's roles.
    HR admin gets all tools, employee gets read-only tools + safe creates.
    """
    if not user_roles:
        user_roles = ["employee"]

    role_set = set(user_roles)

    if "hr_admin" in role_set or "admin" in role_set:
        return list(TOOL_BINDINGS.keys())

    if "manager" in role_set:
        excluded = {"create_employee", "update_employee", "archive_employee", "process_payroll", "create_payroll_cycle", "update_compensation", "create_bonus", "promote_to_employee"}
        return [name for name in TOOL_BINDINGS if name not in excluded]

    if "it_admin" in role_set:
        it_tools = [name for name, b in TOOL_BINDINGS.items() if b["module"] in ("it", "hr", "calendar", "projects") and b["category"] != "delete"]
        safe_tools = get_safe_employee_tools()
        return list(set(it_tools + safe_tools))

    return get_safe_employee_tools()


def get_safe_employee_tools() -> list:
    """Returns the safe subset of tools for regular employees."""
    safe = [
        # Read tools
        "get_employee_profile", "get_employee_profile_full", "search_employees", "search_employees_advanced",
        "get_org_chart", "get_department_members", "list_department_members",
        "get_pto_balance", "get_vacation_balance",
        "get_team_calendar", "get_upcoming_vacations",
        "get_payslip", "get_tax_rules",
        "get_financial_ledger", "get_expense_summary",
        "get_work_schedule", "get_time_logs",
        "get_it_assets",
        "get_training_progress", "get_course_catalog", "recommend_courses",
        "get_job_applications", "get_pipeline_stats",
        "get_team_okrs", "get_kudos_received", "get_kudos_leaderboard",
        "get_pipeline_overview", "search_clients", "get_deal_stats",
        "get_project_status",
        "get_contracts", "get_compliance_status",
        "get_company_announcements",
        "get_department_stats",
        # Safe creates
        "request_vacation", "book_vacation",
        "create_meeting",
        "create_expense",
        "create_it_ticket",
        "search_it_knowledge_base",
        "enroll_in_course",
        "create_okr", "update_key_result",
        "create_kudos",
        "create_task", "create_project_task",
        "create_wiki_page",
        "update_task_status",
        "clock_in", "clock_out",
        "submit_whistleblower",
        "complete_workflow_step",
        "generate_smart_goals",
        "log_lead_activity",
        "mark_notification_read",
        # New platform-wide tools
        "get_employee_attendance", "get_employee_documents",
        "get_budget_summary", "get_project_timeline",
        "get_my_okrs", "get_review_feedback", "generate_career_path",
        "get_gdpr_export",
        "get_workflow_templates", "get_workflow_status",
        "get_user_notifications", "mark_notification_read",
        "get_active_integrations", "get_tenant_config",
        "get_surveys", "get_chat_channels", "search_messages",
        "get_activity_timeline",
    ]
    return safe
