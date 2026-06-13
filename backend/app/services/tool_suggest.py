import logging
from typing import List, Dict

logger = logging.getLogger("successcore.tool_suggest")

TOOL_KEYWORDS = {
    "employee": ["get_employee_profile", "search_employees"],
    "department": ["list_department_members", "get_department_stats"],
    "it": ["create_it_ticket"],
    "vacation": ["get_vacation_balance", "book_vacation", "get_upcoming_vacations"],
    "training": ["get_training_progress"],
    "finance": ["get_expense_summary", "create_expense"],
    "expense": ["get_expense_summary", "create_expense"],
    "kudos": ["create_kudos", "get_kudos_leaderboard"],
    "client": ["create_client"],
    "lead": ["create_client"],
    "task": ["create_task"],
    "announcement": ["get_company_announcements"],
    "search": ["search_employees"],
    "hire": ["get_employee_profile", "create_client"],
    "recruit": ["get_employee_profile", "create_client"],
    "report": ["get_department_stats", "get_expense_summary", "get_kudos_leaderboard"],
    "payroll": ["get_department_stats", "get_vacation_balance"],
    "chat": ["get_employee_profile", "search_employees"],
    "support": ["create_it_ticket", "get_department_stats"],
    "onboarding": ["get_employee_profile", "list_department_members", "get_company_announcements"],
    "help": ["get_employee_profile", "search_employees", "create_it_ticket"],
}


def suggest_tools(description: str, purpose: str = "") -> List[str]:
    text = f"{description} {purpose}".lower()
    suggested: List[str] = []
    for keyword, tools in TOOL_KEYWORDS.items():
        if keyword in text:
            for tool in tools:
                if tool not in suggested:
                    suggested.append(tool)
    if not suggested:
        suggested = ["get_employee_profile", "search_employees"]
    return suggested
