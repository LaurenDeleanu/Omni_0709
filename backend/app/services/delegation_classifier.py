import logging
import json
import re
from typing import Optional
from app.services.llm_router import get_llm_client

logger = logging.getLogger(__name__)

SPECIALIST_KEYWORD_PATTERNS = {
    "PAYROLL_SPECIALIST": {
        "keywords": [
            "nómina", "salario", "sueldo", "paga", "payslip", "irpf", "retención",
            "seguridad social", "baja laboral", "incapacidad", "prestación",
            "payroll", "salary", "wage", "compensation", "tax", "bonus",
            "finiquito", "liquidación", "indemnización",
        ],
        "confidence": 0.92,
    },
    "IT_HELPDESK": {
        "keywords": [
            "ordenador", "portátil", "vpn", "wifi", "contraseña", "acceso",
            "ticket", "incidencia", "pantalla", "teclado", "ratón", "impresora",
            "software", "instalar", "actualizar", "error", "bug", "crash",
            "laptop", "computer", "password", "reset", "login", "network",
            "asset", "hardware", "it support",
        ],
        "confidence": 0.90,
    },
    "RECRUITER": {
        "keywords": [
            "candidato", "entrevista", "cv", "currículum", "oferta", "contratar",
            "vacante", "puesto", "job posting", "reclutar", "selección",
            "candidate", "interview", "hire", "job", "recruitment", "resume",
            "aplicación", "applicant", "screening",
        ],
        "confidence": 0.90,
    },
    "SALES_COACH": {
        "keywords": [
            "cliente", "lead", "pipeline", "deal", "venta", "oportunidad",
            "crm", "contacto", "prospecto", "comercial", "client", "sale",
            "account", "prospect", "opportunity",
        ],
        "confidence": 0.88,
    },
    "PERFORMANCE_COACH": {
        "keywords": [
            "okr", "objetivo", "key result", "evaluación", "desempeño",
            "review", "feedback", "kpi", "meta", "performance", "goal",
            "kudos", "reconocimiento",
        ],
        "confidence": 0.88,
    },
    "ONBOARDING_BUDDY": {
        "keywords": [
            "onboarding", "nuevo empleado", "alta", "incorporación", "bienvenida",
            "inducción", "new hire", "welcome", "setup", "buddy",
        ],
        "confidence": 0.90,
    },
    "COMPLIANCE_OFFICER": {
        "keywords": [
            "contrato", "legal", "gdpr", "compliance", "normativa", "regulación",
            "auditoría", "denuncia", "whistleblower", "cumplimiento",
            "contract", "regulation", "audit", "policy", "política",
        ],
        "confidence": 0.85,
    },
    "DATA_ANALYST": {
        "keywords": [
            "estadística", "reporte", "dashboard", "analítica", "tendencia",
            "métrica", "kpi", "forecast", "predicción", "gráfico",
            "analytics", "statistics", "trend", "report", "metric",
            "department stats", "pipeline stats",
        ],
        "confidence": 0.88,
    },
    "FINANCE_MANAGER": {
        "keywords": [
            "gasto", "factura", "presupuesto", "contabilidad", "ledger",
            "balance", "tesorería", "reembolso", "expense", "invoice",
            "budget", "accounting", "financial", "reimbursement",
        ],
        "confidence": 0.88,
    },
    "HR_ASSISTANT": {
        "keywords": [
            "vacaciones", "pto", "días libres", "ausencia", "departamento", "equipo",
            "empleado", "compañero", "perfil", "organigrama", "vacation", "leave",
            "employee", "department", "org chart", "team", "profile",
        ],
        "confidence": 0.85,
    },
}

GENERAL_KEYWORDS = [
    "hola", "buenos días", "buenas tardes", "hello", "hi", "gracias", "thanks",
    "ayuda", "help", "qué puedes hacer", "what can you do", "quién eres",
    "cómo funciona", "how does", "explícame", "explain", "navegar",
    "dónde está", "where is", "muéstrame", "show me",
]


def keyword_prefilter(user_message: str) -> Optional[dict]:
    lower = user_message.lower().strip()

    if len(lower) < 10:
        return {
            "should_delegate": False,
            "agent_type": "",
            "reason": "Short message, likely general",
            "confidence": 0.95,
        }

    if any(greeting in lower for greeting in GENERAL_KEYWORDS if len(greeting) > 2):
        if len(lower) < 30:
            return {
                "should_delegate": False,
                "agent_type": "",
                "reason": "General greeting or question",
                "confidence": 0.95,
            }

    best_match = None
    best_score = 0
    best_confidence = 0.0

    for agent_type, config in SPECIALIST_KEYWORD_PATTERNS.items():
        matches = 0
        total_weight = 0
        for keyword in config["keywords"]:
            if keyword in lower:
                weight = 1.0 if len(keyword) > 5 else 0.7
                total_weight += weight
                matches += 1
        if matches == 0:
            continue
        score = matches * (1 + total_weight / max(len(config["keywords"]), 1))
        if score > best_score:
            best_score = score
            best_match = agent_type
            best_confidence = min(config["confidence"] + matches * 0.02, 0.98)

    if best_match and best_score >= 1.0:
        logger.debug(
            f"Keyword prefilter matched: {best_match} "
            f"(score={best_score:.1f}, confidence={best_confidence:.2f})"
        )
        return {
            "should_delegate": True,
            "agent_type": best_match.lower(),
            "reason": f"Keyword match: {best_score:.1f} score with {best_confidence:.0%} confidence",
            "confidence": best_confidence,
        }

    return None


async def detect_delegation_intent_smart(
    user_message: str,
    db,
    force_llm: bool = False,
) -> dict:
    if not force_llm:
        keyword_result = keyword_prefilter(user_message)
        if keyword_result is not None:
            return keyword_result

    SPECIALIST_AGENT_TYPES = [
        "HR_ASSISTANT", "PAYROLL_SPECIALIST", "IT_HELPDESK", "RECRUITER",
        "SALES_COACH", "PERFORMANCE_COACH", "ONBOARDING_BUDDY",
        "COMPLIANCE_OFFICER", "DATA_ANALYST", "FINANCE_MANAGER",
    ]

    SPECIALIST_CAPABILITIES = {
        "HR_ASSISTANT": "Handles HR queries: employee profiles, department info, vacation balances, time off requests, org charts, team members, OKRs, performance reviews.",
        "PAYROLL_SPECIALIST": "Handles payroll: payslips, tax rules, payroll cycles, compensation changes, bonuses, financial ledger queries, expense summaries.",
        "IT_HELPDESK": "Handles IT support: ticket creation, asset management, ticket resolution, knowledge base search, IT ticket statistics, auto-tagging.",
        "RECRUITER": "Handles recruitment: job postings, candidate management, interview scheduling, pipeline stats, resume parsing, candidate screening, offer letters.",
        "SALES_COACH": "Handles CRM/sales: pipeline overview, client details, deal stats, lead activity, task creation for leads.",
        "PERFORMANCE_COACH": "Handles performance management: OKRs, key results, reviews, team OKRs, kudos, training progress, course recommendations.",
        "ONBOARDING_BUDDY": "Handles onboarding: new hire setup, onboarding plans, training enrollment, course catalog, buddy assignments.",
        "COMPLIANCE_OFFICER": "Handles compliance: contracts, compliance status, whistleblower reports, audit reports, regulatory checks.",
        "DATA_ANALYST": "Handles data analysis: department stats, pipeline stats, ticket stats, deal stats, trend analysis, forecasting.",
        "FINANCE_MANAGER": "Handles finance: financial ledger, expense summaries, budget tracking, financial reports, contract financials.",
    }

    capabilities_str = "\n".join(
        f"- {agent_type}: {cap}"
        for agent_type, cap in SPECIALIST_CAPABILITIES.items()
    )
    agent_types_str = ", ".join(SPECIALIST_AGENT_TYPES)

    prompt = """You are a delegation classifier. Determine if this message should be delegated to a specialist.

Available specialists:
{capabilities}

Rules:
1. Delegate (should_delegate=true) only for clearly single-domain specialist tasks
2. Greetings, simple questions, platform help, multi-domain queries → should_delegate=false
3. Confidence below 0.6 → should_delegate=false
4. agent_type MUST be one of: {agent_types}

Return JSON: {{"should_delegate": true/false, "agent_type": "...", "reason": "...", "confidence": 0.0-1.0}}""".format(
        capabilities=capabilities_str,
        agent_types=agent_types_str,
    )

    try:
        client, _ = await get_llm_client("meta-llama/llama-3.3-70b-instruct:free", None, db)
        response = await client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            temperature=0.1,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
        )

        raw = response.choices[0].message.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw[raw.find("\n"):raw.rfind("```")].strip()

        data = json.loads(raw)
        should_delegate = data.get("should_delegate", False)
        confidence = float(data.get("confidence", 0.0))
        agent_type = data.get("agent_type", "")

        if confidence < 0.6:
            should_delegate = False
        if agent_type not in SPECIALIST_AGENT_TYPES:
            should_delegate = False
            agent_type = ""

        return {
            "should_delegate": should_delegate,
            "agent_type": agent_type,
            "reason": data.get("reason", ""),
            "confidence": confidence,
        }
    except Exception as e:
        logger.warning(f"LLM delegation detection failed: {e}")
        return {
            "should_delegate": False,
            "agent_type": "",
            "reason": f"Classification error: {e}",
            "confidence": 0.0,
        }
