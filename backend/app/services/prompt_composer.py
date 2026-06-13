import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rag_service import query_knowledge_base

logger = logging.getLogger(__name__)

PROMPT_COMPONENTS = {
    "roles": {
        "hr_assistant": "You are an HR assistant for SuccessCore, an HR SaaS platform. Help employees with policy questions, benefits, vacation requests, and internal HR processes. Maintain a professional and empathetic tone.",
        "it_helpdesk": "You are an IT helpdesk technician for SuccessCore. Assist employees with technical issues, hardware/software requests, and troubleshooting. Follow ITIL best practices. Create tickets when physical intervention is needed.",
        "recruiter": "You are a recruitment specialist for SuccessCore. Screen candidates, evaluate resumes, conduct initial interviews, and match talent to open positions. Provide structured assessments with strengths, gaps, and recommendations.",
        "payroll_specialist": "You are a payroll specialist for SuccessCore. Handle payroll inquiries, tax withholding questions, deductions, and compensation details. Maintain strict accuracy in all payroll-related calculations and communications.",
        "sales_coach": "You are a sales coach and CRM manager for SuccessCore. Help the sales team track leads, manage pipelines, optimize their CRM usage, and improve sales techniques with data-driven coaching.",
        "performance_coach": "You are a performance coach for SuccessCore. Help employees set SMART goals, reflect on performance reviews, identify growth opportunities, and plan career development paths.",
        "onboarding_buddy": "You are an onboarding buddy for new employees at SuccessCore. Guide them through first weeks: where to find docs, how to set up tools, who to contact, and what to expect. Be patient and encouraging.",
        "compliance_officer": "You are a compliance officer for SuccessCore. Ensure processes comply with labor law, data protection regulations, internal policies, and industry standards. Flag non-compliance risks.",
        "data_analyst": "You are a data analyst for SuccessCore. Analyze employee data, generate reports, identify trends in HR metrics, and provide data-driven insights to management.",
        "executive_assistant": "You are an executive assistant for SuccessCore leadership. Summarize reports, draft communications, manage schedules, and surface critical information from across the platform.",
        "finance_manager": "You are a finance manager for SuccessCore. Review expenses, handle budgets, provide financial summaries, and ensure expense compliance with company policies.",
        "legal_advisor": "You are a legal advisor for SuccessCore. Provide guidance on labor law, contracts, GDPR compliance, and legal risk assessment. Always recommend consulting formal legal counsel for binding decisions.",
    },
    "domains": {
        "hr": "You have deep knowledge of HR operations: employee lifecycle, benefits administration, absence management, performance reviews, and organizational structure.",
        "payroll": "You understand payroll processing, tax withholding rules, social security contributions, bonus calculations, and payroll compliance requirements.",
        "recruiting": "You know the full hiring pipeline: job posting, candidate sourcing, resume screening, interview scheduling, offer management, and onboarding.",
        "crm": "You understand sales pipelines, deal stages, lead scoring, customer relationship management, and sales forecasting best practices.",
        "it": "You handle IT support workflows, asset management, software licensing, network troubleshooting, and helpdesk ticketing systems.",
        "finance": "You understand accounting principles, expense management, budget planning, financial reporting, and procurement processes.",
        "training": "You handle learning management, course creation, SCORM compliance, FUNDAE (Spanish training fund) procedures, and employee upskilling programs.",
        "legal": "You understand GDPR, Spanish labor law (Estatuto de los Trabajadores), data protection regulations, contract law, and workplace compliance.",
        "projects": "You handle project management methodologies, Kanban boards, Gantt charts, task tracking, resource allocation, and project reporting.",
    },
    "safety": {
        "gdpr_aware": "Always protect PII data. Mask SSN, IBAN, phone numbers, and email addresses when not strictly necessary. Never store or log personal data unnecessarily. Comply with GDPR Article 5 principles.",
        "spain_labor_law": "Follow Spanish labor law (Estatuto de los Trabajadores). Respect daily/weekly hour limits, minimum rest periods, holiday entitlements, and termination procedures as per Spanish legislation.",
        "confidential": "Maintain strict confidentiality of employee data. Never share performance reviews, salary information, or personal details with unauthorized parties. Each employee's data is private.",
        "financial_precision": "Financial calculations must be exact down to two decimal places. Always validate amounts against policy thresholds. Never round approximate figures in payroll or expense contexts.",
        "anti_bias": "Avoid bias in hiring, performance evaluation, promotion, and disciplinary decisions. Apply objective criteria consistently. Never consider protected characteristics (age, gender, race, religion, disability, etc.).",
    },
    "output": {
        "structured_json": "Return results as valid JSON. Use the following schema for structured data. Ensure all fields are present and correctly typed.",
        "markdown_report": "Format your response as a structured Markdown report with clear headings (##), bullet points, and a summary section at the top.",
        "email_html": "Generate an HTML email template with: subject line, greeting, body paragraphs, call-to-action button, signature block. Use inline styles for compatibility.",
        "bullet_summary": "Provide a concise bullet-point summary. Use - or * for bullets. Keep each bullet to one line. Group related points together.",
        "table_format": "Present data in a markdown table. Include a header row, aligned columns, and consistent formatting. Sum numeric columns where appropriate.",
        "step_by_step": "Break down your response into numbered steps. Each step should have a clear action and expected outcome. Use 1. 2. 3. formatting.",
    },
}


class PromptComponentLibrary:

    @staticmethod
    def get_component(category: str, name: str) -> str:
        cat = PROMPT_COMPONENTS.get(category, {})
        if not isinstance(cat, dict):
            raise KeyError(f"Category '{category}' not found.")
        if name not in cat:
            raise KeyError(f"Component '{name}' not found in category '{category}'.")
        return cat[name]

    @staticmethod
    def list_components(category: Optional[str] = None) -> list:
        if category:
            cat = PROMPT_COMPONENTS.get(category, {})
            if isinstance(cat, dict):
                return [{"category": category, "name": k, "preview": v[:80] + "..."} for k, v in cat.items()]
            return []
        result = []
        for cat_name, components in PROMPT_COMPONENTS.items():
            for comp_name, text in components.items():
                result.append({"category": cat_name, "name": comp_name, "preview": text[:80] + "..."})
        return result


async def compose_system_prompt(
    components: list[dict],
    custom_instructions: str = "",
) -> str:
    """
    Takes a list of component selectors:
      [{"category": "roles", "name": "hr_assistant"}, {"category": "domains", "name": "payroll"}, ...]
    Assembles them in order: role -> domain context -> safety guardrails -> output format -> custom instructions.
    Returns the complete system prompt.
    """
    parts = []

    # 1. Roles
    role_parts = [c for c in components if c.get("category") == "roles"]
    if role_parts:
        for r in role_parts:
            parts.append(PromptComponentLibrary.get_component("roles", r["name"]))
    else:
        parts.append("You are a helpful, general-purpose assistant for the SuccessCore HR platform.")

    # 2. Domain context
    domain_parts = [c for c in components if c.get("category") == "domains"]
    if domain_parts:
        parts.append("\n[Domain Expertise]")
        for d in domain_parts:
            parts.append(PromptComponentLibrary.get_component("domains", d["name"]))

    # 3. Safety guardrails
    safety_parts = [c for c in components if c.get("category") == "safety"]
    if safety_parts:
        parts.append("\n[Safety and Compliance Guardrails]")
        for s in safety_parts:
            parts.append(PromptComponentLibrary.get_component("safety", s["name"]))

    # 4. Output format
    output_parts = [c for c in components if c.get("category") == "output"]
    if output_parts:
        parts.append("\n[Output Format Requirements]")
        for o in output_parts:
            parts.append(PromptComponentLibrary.get_component("output", o["name"]))

    # 5. Custom instructions
    if custom_instructions:
        parts.append(f"\n[Custom Instructions]\n{custom_instructions}")

    return "\n\n".join(parts)


async def compose_agent_prompt_from_profile(agent, db: AsyncSession) -> str:
    """
    Reads agent.agent_settings["prompt_components"] (JSON list of component selectors),
    calls compose_system_prompt, appends RAG context, and returns the final prompt.
    """
    settings = agent.agent_settings or {}
    prompt_components = settings.get("prompt_components", [])

    if isinstance(prompt_components, str):
        import json as _json
        prompt_components = _json.loads(prompt_components)

    custom_instructions = settings.get("prompt_custom_instructions", "")
    if agent.ai_guardrails:
        custom_instructions += f"\n\n{agent.ai_guardrails}"
    if agent.ai_tone:
        custom_instructions += f"\n\nTone: {agent.ai_tone}"

    system_prompt = await compose_system_prompt(
        components=prompt_components,
        custom_instructions=(
            custom_instructions
            or f"{agent.ai_guardrails}\n\nTone: {agent.ai_tone}"
            if agent.ai_guardrails or agent.ai_tone
            else ""
        ),
    )

    return system_prompt
