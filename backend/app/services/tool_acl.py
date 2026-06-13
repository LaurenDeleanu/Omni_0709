import logging
from typing import NamedTuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent import Agent

logger = logging.getLogger(__name__)

DESTRUCTIVE_TOOLS: set[str] = {
    "process_payroll", "update_compensation", "create_bonus", "archive_employee",
    "tool_archive_employee", "approve_vacation", "tool_approve_vacation",
    "move_candidate_stage", "tool_move_candidate_stage", "promote_to_employee",
    "tool_promote_to_employee", "create_payroll_cycle", "submit_whistleblower"
}

ROLE_TOOL_BINDINGS: dict[str, set[str]] = {
    "employee": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "enroll_in_course", "get_course_catalog", "recommend_courses",
        "get_pipeline_overview", "get_client_details", "search_clients",
        "create_project", "create_project_task", "get_project_status", "create_wiki_page",
        "get_org_chart", "get_team_okrs", "get_kudos_received",
    },
    "hr_admin": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "enroll_in_course", "get_course_catalog", "recommend_courses",
        "get_pipeline_overview", "get_client_details", "search_clients",
        "create_project", "create_project_task", "get_project_status", "create_wiki_page",
        "get_org_chart", "get_team_okrs", "get_kudos_received",
        "tool_create_employee", "tool_update_employee", "tool_archive_employee",
        "tool_search_employees", "tool_get_employee_profile", "tool_get_org_chart",
        "tool_get_span_of_control", "tool_get_pto_balance", "tool_get_department_members",
        "tool_get_recent_hires", "tool_request_vacation", "tool_approve_vacation",
        "tool_get_team_calendar", "tool_create_meeting", "tool_get_work_schedule",
        "tool_create_payroll_cycle", "tool_process_payroll", "tool_get_payslip",
        "tool_get_tax_rules", "tool_update_compensation", "tool_create_bonus",
        "tool_get_financial_ledger", "tool_get_expense_summary",
        "tool_clock_in", "tool_clock_out", "tool_get_time_logs",
        "tool_assign_it_ticket", "tool_resolve_it_ticket", "tool_get_it_assets",
        "tool_get_ticket_stats", "tool_enroll_in_course",
        "tool_get_training_progress", "tool_get_course_catalog",
        "tool_recommend_courses", "tool_validate_fundae",
        "tool_create_job_posting", "tool_add_candidate",
        "tool_move_candidate_stage", "tool_schedule_interview",
        "tool_get_job_applications", "tool_get_pipeline_stats",
        "tool_promote_to_employee", "tool_create_okr", "tool_update_key_result",
        "tool_create_review", "tool_get_team_okrs", "tool_get_kudos_received",
        "tool_get_contracts", "tool_get_compliance_status",
        "tool_submit_whistleblower", "create_employee",
        "generate_onboarding_plan", "assign_onboarding_buddy",
        "parse_resume", "match_candidate_to_job", "screen_resume", "screen_candidate",
        "rank_candidates", "draft_offer_letter", "send_offer_email",
    },
    "sys_admin": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "enroll_in_course", "get_course_catalog", "recommend_courses",
        "get_pipeline_overview", "get_client_details", "search_clients",
        "create_project", "create_project_task", "get_project_status", "create_wiki_page",
        "get_org_chart", "get_team_okrs", "get_kudos_received",
        "tool_create_employee", "tool_update_employee", "tool_archive_employee",
        "tool_search_employees", "tool_get_employee_profile", "tool_get_org_chart",
        "tool_get_span_of_control", "tool_get_pto_balance", "tool_get_department_members",
        "tool_get_recent_hires", "tool_request_vacation", "tool_approve_vacation",
        "tool_get_team_calendar", "tool_create_meeting", "tool_get_work_schedule",
        "tool_create_payroll_cycle", "tool_process_payroll", "tool_get_payslip",
        "tool_get_tax_rules", "tool_update_compensation", "tool_create_bonus",
        "tool_get_financial_ledger", "tool_get_expense_summary",
        "tool_clock_in", "tool_clock_out", "tool_get_time_logs",
        "tool_assign_it_ticket", "tool_resolve_it_ticket", "tool_get_it_assets",
        "tool_get_ticket_stats", "tool_enroll_in_course",
        "tool_get_training_progress", "tool_get_course_catalog",
        "tool_recommend_courses", "tool_validate_fundae",
        "tool_create_job_posting", "tool_add_candidate",
        "tool_move_candidate_stage", "tool_schedule_interview",
        "tool_get_job_applications", "tool_get_pipeline_stats",
        "tool_promote_to_employee", "tool_create_okr", "tool_update_key_result",
        "tool_create_review", "tool_get_team_okrs", "tool_get_kudos_received",
        "tool_get_pipeline_overview", "tool_get_client_details",
        "tool_search_clients", "tool_get_deal_stats",
        "tool_create_task_for_lead", "tool_log_lead_activity",
        "tool_create_project", "tool_create_project_task",
        "tool_get_project_status", "tool_create_wiki_page",
        "tool_get_contracts", "tool_get_compliance_status",
        "tool_submit_whistleblower", "create_employee",
        "trigger_workflow", "complete_workflow_step",
        "create_workflow_from_description", "analyze_workflow",
        "search_it_knowledge_base", "auto_tag_it_ticket", "suggest_it_solution",
        "generate_onboarding_plan", "assign_onboarding_buddy",
        "parse_resume", "match_candidate_to_job", "screen_resume", "screen_candidate",
        "rank_candidates", "draft_offer_letter", "send_offer_email",
        "run_compliance_audit", "generate_compliance_report",
        "predict_attrition_risk", "predict_churn_risk",
        "forecast_revenue", "forecast_headcount",
    },
    "manager": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "enroll_in_course", "get_course_catalog", "recommend_courses",
        "get_pipeline_overview", "get_client_details", "search_clients",
        "create_project", "create_project_task", "get_project_status", "create_wiki_page",
        "get_org_chart", "get_team_okrs", "get_kudos_received",
        "tool_get_employee_profile", "tool_get_org_chart",
        "tool_get_span_of_control", "tool_get_pto_balance", "tool_get_department_members",
        "tool_get_recent_hires", "tool_get_team_calendar", "tool_create_meeting",
        "tool_get_work_schedule", "tool_get_payslip", "tool_get_tax_rules",
        "tool_get_financial_ledger", "tool_get_expense_summary",
        "tool_get_time_logs", "tool_get_ticket_stats",
        "tool_get_training_progress", "tool_get_course_catalog",
        "tool_recommend_courses", "tool_get_job_applications", "tool_get_pipeline_stats",
        "tool_create_okr", "tool_update_key_result",
        "tool_create_review", "tool_get_team_okrs", "tool_get_kudos_received",
        "tool_get_pipeline_overview", "tool_get_client_details",
        "tool_search_clients", "tool_get_deal_stats",
        "tool_get_project_status", "tool_get_contracts", "tool_get_compliance_status",
        "tool_request_vacation", "tool_approve_vacation",
        "trigger_workflow", "complete_workflow_step",
        "search_it_knowledge_base",
    },
    "payroll_admin": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "tool_create_payroll_cycle", "tool_process_payroll", "tool_get_payslip",
        "tool_get_tax_rules", "tool_update_compensation", "tool_create_bonus",
        "tool_get_financial_ledger", "tool_get_expense_summary",
        "tool_get_time_logs", "tool_get_employee_profile",
        "tool_get_department_members", "tool_get_org_chart",
        "tool_get_contracts", "tool_get_compliance_status",
    },
    "compliance_officer": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "tool_get_contracts", "tool_get_compliance_status",
        "tool_submit_whistleblower", "tool_get_employee_profile",
        "tool_get_department_members", "tool_get_org_chart",
        "generate_compliance_report", "run_compliance_audit",
    },
    "recruiter": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "tool_create_job_posting", "tool_add_candidate",
        "tool_move_candidate_stage", "tool_schedule_interview",
        "tool_get_job_applications", "tool_get_pipeline_stats",
        "tool_promote_to_employee", "tool_get_employee_profile",
        "tool_get_department_members",
        "parse_resume", "match_candidate_to_job", "screen_resume", "screen_candidate",
        "rank_candidates", "draft_offer_letter",
    },
    "sales_rep": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "get_pipeline_overview", "get_client_details", "search_clients",
        "get_deal_stats", "create_task_for_lead", "log_lead_activity",
        "tool_get_pipeline_overview", "tool_get_client_details",
        "tool_search_clients", "tool_get_deal_stats",
        "tool_create_task_for_lead", "tool_log_lead_activity",
    },
    "it_support": {
        "get_employee_profile", "list_department_members", "get_vacation_balance",
        "create_it_ticket", "search_employees", "get_department_stats",
        "get_expense_summary", "get_training_progress", "get_company_announcements",
        "get_upcoming_vacations", "get_kudos_leaderboard",
        "create_client", "book_vacation", "create_kudos", "create_expense", "create_task",
        "tool_assign_it_ticket", "tool_resolve_it_ticket", "tool_get_it_assets",
        "tool_get_ticket_stats", "tool_get_employee_profile",
        "search_it_knowledge_base", "auto_tag_it_ticket", "suggest_it_solution",
    },
}

DEFAULT_TOOLS: set[str] = ROLE_TOOL_BINDINGS.get("employee", set())


class PermissionResult(NamedTuple):
    denied: bool
    reason: str
    message: str
    requires_confirmation: bool = False


def get_allowed_tools_for_roles(user_roles: list) -> set[str]:
    allowed: set[str] = set()
    for role in user_roles:
        role_lower = role.lower()
        bindings = ROLE_TOOL_BINDINGS.get(role_lower, None)
        if bindings is not None:
            allowed.update(bindings)
        else:
            allowed.update(DEFAULT_TOOLS)
    if not allowed:
        allowed = DEFAULT_TOOLS
    return allowed


def build_copilot_tool_list(user_roles: list, tool_schemas: list) -> list:
    allowed = get_allowed_tools_for_roles(user_roles)
    return [t for t in tool_schemas if t.get("function", {}).get("name") in allowed]


async def check_tool_permission(
    tool_name: str,
    user_role: str,
    user_id: str,
    db: AsyncSession,
) -> PermissionResult:
    role_lower = user_role.lower() if user_role else "employee"
    allowed = ROLE_TOOL_BINDINGS.get(role_lower, DEFAULT_TOOLS)

    try:
        from app.services.tool_binding_registry import TOOL_BINDINGS
        for binding_name, binding in TOOL_BINDINGS.items():
            if binding.get("tool") == tool_name and binding.get("requires_role") == role_lower:
                allowed.add(tool_name)
                break
    except Exception:
        pass

    if tool_name in DESTRUCTIVE_TOOLS:
        return PermissionResult(
            denied=True,
            reason="requires_confirmation",
            message=f"La herramienta '{tool_name}' requiere confirmación adicional.",
            requires_confirmation=True,
        )

    if tool_name not in allowed:
        return PermissionResult(
            denied=True,
            reason="insufficient_role",
            message=f"El rol '{user_role}' no tiene permiso para ejecutar la herramienta '{tool_name}'.",
        )

    return PermissionResult(denied=False, reason="", message="")


async def enforce_tool_acl(
    tool_name: str,
    user_payload: dict,
    db: AsyncSession,
) -> PermissionResult:
    user_role = user_payload.get("role", "")
    user_id = user_payload.get("user_id", "")
    if not user_role:
        roles = user_payload.get("https://successcore.com/roles", []) or user_payload.get("roles", [])
        user_role = roles[0] if roles else "employee"

    result = await check_tool_permission(tool_name, user_role, user_id, db)
    if result.denied:
        logger.warning(
            f"ACL DENIED: tool='{tool_name}' user='{user_id}' role='{user_role}' reason='{result.reason}'"
        )
    return result
