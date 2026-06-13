import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent import Agent

logger = logging.getLogger("successcore.specialist_registry")

SPECIALIST_REGISTRY: Dict[str, Dict[str, Any]] = {
    "hr_assistant": {
        "display_name": "HR Assistant",
        "icon": "👤",
        "description": "Employee profiles, department info, vacation balances, org charts",
        "domain": "hr",
        "default_tools": [
            "get_employee_profile", "list_department_members", "get_vacation_balance",
            "search_employees", "get_department_stats", "get_org_chart",
            "get_span_of_control", "get_team_okrs",
        ],
        "priority": 1,
    },
    "payroll_specialist": {
        "display_name": "Payroll Specialist",
        "icon": "💰",
        "description": "Payslips, tax rules, payroll cycles, compensation, bonuses",
        "domain": "payroll",
        "default_tools": [
            "tool_create_payroll_cycle", "tool_process_payroll", "tool_get_payslip",
            "tool_get_tax_rules", "tool_update_compensation", "tool_create_bonus",
            "tool_get_financial_ledger",
        ],
        "priority": 2,
    },
    "it_helpdesk": {
        "display_name": "IT Helpdesk",
        "icon": "🔧",
        "description": "Ticket creation, asset management, knowledge base search, auto-tagging",
        "domain": "it",
        "default_tools": [
            "tool_assign_it_ticket", "tool_resolve_it_ticket", "tool_get_it_assets",
            "tool_get_ticket_stats", "create_it_ticket",
        ],
        "priority": 3,
    },
    "recruiter": {
        "display_name": "Recruiter",
        "icon": "🎯",
        "description": "Job postings, candidate management, interview scheduling, pipeline stats",
        "domain": "recruitment",
        "default_tools": [
            "tool_create_job_posting", "tool_add_candidate", "tool_move_candidate_stage",
            "tool_schedule_interview", "tool_get_job_applications", "tool_get_pipeline_stats",
            "tool_promote_to_employee",
        ],
        "priority": 4,
    },
    "sales_coach": {
        "display_name": "Sales Coach",
        "icon": "📊",
        "description": "Pipeline overview, client details, deal stats, lead activity",
        "domain": "crm",
        "default_tools": [
            "tool_get_pipeline_overview", "tool_get_client_details", "tool_search_clients",
            "tool_get_deal_stats", "tool_create_task_for_lead", "tool_log_lead_activity",
        ],
        "priority": 5,
    },
    "performance_coach": {
        "display_name": "Performance Coach",
        "icon": "📈",
        "description": "OKRs, key results, reviews, team OKRs, kudos, training progress",
        "domain": "performance",
        "default_tools": [
            "tool_create_okr", "tool_update_key_result", "tool_create_review",
            "tool_get_team_okrs", "tool_get_kudos_received", "tool_get_training_progress",
        ],
        "priority": 6,
    },
    "onboarding_buddy": {
        "display_name": "Onboarding Buddy",
        "icon": "🤝",
        "description": "New hire setup, onboarding plans, training enrollment, buddy assignments",
        "domain": "onboarding",
        "default_tools": [
            "tool_enroll_in_course", "tool_get_training_progress", "tool_get_course_catalog",
            "assign_onboarding_buddy",
        ],
        "priority": 7,
    },
    "compliance_officer": {
        "display_name": "Compliance Officer",
        "icon": "🛡️",
        "description": "Contracts, compliance status, whistleblower reports, audit reports",
        "domain": "legal",
        "default_tools": [
            "tool_get_contracts", "tool_get_compliance_status", "tool_submit_whistleblower",
        ],
        "priority": 8,
    },
    "data_analyst": {
        "display_name": "Data Analyst",
        "icon": "📉",
        "description": "Department stats, pipeline stats, ticket stats, trend analysis, forecasting",
        "domain": "analytics",
        "default_tools": [
            "get_department_stats", "tool_get_pipeline_stats", "tool_get_ticket_stats",
            "get_expense_summary",
        ],
        "priority": 9,
    },
    "finance_manager": {
        "display_name": "Finance Manager",
        "icon": "🏦",
        "description": "Financial ledger, expense summaries, budget tracking, financial reports",
        "domain": "finance",
        "default_tools": [
            "tool_get_financial_ledger", "tool_get_expense_summary", "tool_update_compensation",
            "tool_create_bonus",
        ],
        "priority": 10,
    },
}


def get_all_specialist_types() -> List[str]:
    return list(SPECIALIST_REGISTRY.keys())


def get_specialist_info(agent_type: str) -> Optional[Dict[str, Any]]:
    return SPECIALIST_REGISTRY.get(agent_type)


def get_specialist_display(agent_type: str) -> str:
    info = SPECIALIST_REGISTRY.get(agent_type, {})
    icon = info.get("icon", "🤖")
    name = info.get("display_name", agent_type.replace("_", " ").title())
    return f"{icon} {name}"


def get_default_tools(agent_type: str) -> List[str]:
    info = SPECIALIST_REGISTRY.get(agent_type, {})
    return info.get("default_tools", [])


def get_specialists_summary() -> List[Dict[str, Any]]:
    return [
        {
            "agent_type": atype,
            "display_name": info["display_name"],
            "icon": info["icon"],
            "description": info["description"],
            "domain": info["domain"],
            "default_tools": info["default_tools"],
        }
        for atype, info in SPECIALIST_REGISTRY.items()
    ]


async def discover_active_specialists(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(Agent).where(Agent.is_active == True))
    active_agents = result.scalars().all()

    specialists = []
    seen_types = set()
    for agent in active_agents:
        a_type = agent.agent_type.lower()
        if a_type in SPECIALIST_REGISTRY and a_type not in seen_types:
            info = SPECIALIST_REGISTRY[a_type]
            specialists.append({
                "agent_id": agent.id,
                "agent_type": a_type,
                "display_name": info["display_name"],
                "icon": info["icon"],
                "domain": info["domain"],
                "model": agent.ai_model,
                "is_active": agent.is_active,
            })
            seen_types.add(a_type)

    return specialists


async def get_specialist_health(db: AsyncSession) -> List[Dict[str, Any]]:
    from app.services.agent_health import get_agent_health_status

    specialists = []
    for agent_type, info in SPECIALIST_REGISTRY.items():
        agents_res = await db.execute(
            select(Agent).where(
                Agent.agent_type == agent_type.upper(),
                Agent.is_active == True,
            )
        )
        agents = agents_res.scalars().all()

        health_data = []
        for agent in agents:
            health = await get_agent_health_status(agent.id)
            health_data.append({
                "agent_id": agent.id,
                "name": agent.name,
                "healthy": health.get("healthy", False),
                "latency_ms": health.get("latency_ms", 0),
                "consecutive_failures": health.get("consecutive_failures", 0),
            })

        specialists.append({
            "agent_type": agent_type,
            "display_name": info["display_name"],
            "icon": info["icon"],
            "domain": info["domain"],
            "total_agents": len(agents),
            "active_agents": len(health_data),
            "healthy_agents": sum(1 for h in health_data if h["healthy"]),
            "instances": health_data,
        })

    return specialists
