import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

COMPLEXITY_KEYWORDS = {
    "tier1_fast": {
        "greetings": ["hola", "buenos d", "hello", "hi ", "gracias", "thanks", " bye"],
        "simple_lookup": ["buscar", "ver ", "mostrar", "quién es", "dónde está", "show", "list", "find", "who is"],
        "quick_actions": ["clock in", "clock out", "kudos", "anuncio", "ticket"],
        "max_complexity": 3,
    },
    "tier2_standard": {
        "multi_step": ["crear y", " actualizar", " procesar", "analizar", "create and", "update and"],
        "hr_policy": ["política", "policy", "procedimiento", "norma", "regla"],
        "reports": ["reporte", "informe", "dashboard", "report", "summary"],
        "max_complexity": 7,
    },
    "tier3_reasoning": {
        "code_gen": ["código", "script", "programar", "función", "api", "code", "write a function"],
        "payroll_process": ["procesar nómina", "payroll", "nómina completa", "process payroll"],
        "legal_complex": ["contrato legal", "auditoría", "compliance completo", "legal audit"],
        "multi_agent": ["orquestar", "múltiples agentes", "onboarding completo", "full onboarding"],
        "max_complexity": 10,
    },
}

COMPLEXITY_TOKENS_FAST = {
    "hola": 1, "hello": 1, "hi": 1, "gracias": 1, "thanks": 1, "bye": 1, "adiós": 1,
    "buscar": 2, "busca": 2, "find": 2, "search": 2, "ver": 2, "show": 2, "mostrar": 2,
    "quién": 2, "dónde": 2, "cuándo": 2, "who": 2, "where": 2, "when": 2,
    "crear": 4, "create": 4, "actualizar": 4, "update": 4,
    "eliminar": 5, "delete": 5, "borrar": 5, "remove": 5,
    "nómina": 5, "payroll": 5, "salario": 5, "salary": 5,
    "procesar": 6, "process": 6, "analizar": 6, "analyze": 6,
    "contrato": 7, "contract": 7, "legal": 7, "auditoría": 7, "audit": 7,
    "código": 9, "code": 9, "script": 9, "generar código": 9,
    "orquestar": 10, "orchestrate": 10,
}


def fast_complexity_score(user_message: str) -> float:
    lower = user_message.lower().strip()

    if len(lower) < 10 and any(g in lower for g in ["hola", "hello", "hi", "bye", "ok", "gracias"]):
        return 1.0

    score = 2.0
    matched_tokens = 0

    for token, weight in COMPLEXITY_TOKENS_FAST.items():
        if token in lower:
            score = max(score, weight)
            matched_tokens += 1

    if " y " in f" {lower} " or " also " in lower or " además " in lower:
        score += 1.5
        matched_tokens += 1

    if "?" in lower:
        if matched_tokens <= 1 and score <= 3:
            score = min(score, 3.0)

    if any(kw in lower for kw in ["todos los", "completo", "cada", "full", "all ", "every"]):
        score += 1.0

    return min(round(score, 1), 10.0)


def fast_select_tier(complexity_score: float) -> Tuple[str, Dict[str, Any]]:
    from app.services.model_router import MODEL_TIERS
    tier_order = ["tier1_fast", "tier2_standard", "tier3_reasoning"]
    for tier_name in tier_order:
        tier_config = MODEL_TIERS[tier_name]
        if complexity_score <= tier_config["max_complexity"]:
            return tier_name, tier_config
    return "tier3_reasoning", MODEL_TIERS["tier3_reasoning"]


def fast_model_route(user_message: str) -> Optional[dict]:
    score = fast_complexity_score(user_message)
    tier_name, tier_config = fast_select_tier(score)
    models = tier_config["models"]
    selected_model = models[0] if models else "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

    return {
        "selected_model": selected_model,
        "tier": tier_name,
        "complexity_score": score,
        "method": "keyword",
        "estimated_latency_ms": tier_config["target_latency_ms"],
    }
