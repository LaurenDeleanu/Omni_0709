"""
Multi-Model Router (Phase 1 — P0)
==================================
Intelligence-driven model selection with tiered reasoning.
Routes tasks to appropriate model tier based on complexity analysis.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Tier definitions with cost per 1K tokens (input/output)
MODEL_TIERS: Dict[str, Dict[str, Any]] = {
    "tier1_fast": {
        "description": "Fast — simple lookups, greetings, single-tool calls",
        "models": ["nvidia/nemotron-3-nano-30b-a3b:free", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"],
        "max_complexity": 3,
        "cost_1k_input": 0.0,
        "cost_1k_output": 0.0,
        "target_latency_ms": 500,
    },
    "tier2_standard": {
        "description": "Standard — multi-step reasoning, complex HR queries",
        "models": ["nvidia/nemotron-3-super-120b-a12b:free", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "qwen/qwen3-next-80b-a3b-instruct:free"],
        "max_complexity": 7,
        "cost_1k_input": 0.0,
        "cost_1k_output": 0.0,
        "target_latency_ms": 2000,
    },
    "tier3_reasoning": {
        "description": "Reasoning — code generation, multi-agent orchestration, precision",
        "models": ["nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia/nemotron-3-super-120b-a12b:free", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"],
        "max_complexity": 10,
        "cost_1k_input": 0.0,
        "cost_1k_output": 0.0,
        "target_latency_ms": 5000,
    },
}

# Complexity scoring factors
COMPLEXITY_FACTORS = {
    "tool_calls_predicted": 2.0,  # Weight per predicted tool call
    "domain_complexity": 1.5,  # Multiplier for complex domains
    "safety_sensitivity": 1.2,  # Multiplier for sensitive operations
    "token_estimate_per_1000": 0.5,  # Weight per 1000 estimated tokens
}

# Domain complexity presets
DOMAIN_COMPLEXITY: Dict[str, int] = {
    "greeting": 1,
    "simple_query": 2,
    "employee_lookup": 2,
    "pto_check": 2,
    "calendar_query": 3,
    "hr_policy": 4,
    "payroll": 5,
    "tax_calculation": 6,
    "legal_compliance": 7,
    "multi_module": 8,
    "code_generation": 9,
    "multi_agent_orchestration": 10,
}


@dataclass
class RoutingDecision:
    """Result of the model routing decision."""
    selected_model: str
    tier: str
    complexity_score: float
    reasoning: str
    estimated_latency_ms: int
    estimated_cost_usd: float
    speculative: bool = False
    fallback_models: List[str] = field(default_factory=list)


def classify_domain(user_message: str) -> Tuple[str, int]:
    """Classify the domain of a user message and return its complexity."""
    lower = user_message.lower()

    patterns = {
        "greeting": ["hola", "buenos días", "buenas tardes", "hello", "hi", "gracias", "adiós", "thanks", "bye"],
        "payroll": ["nómina", "salario", "sueldo", "paga", "payslip", "irpf", "impuesto", "retención", "payroll", "salary", "wage"],
        "tax_calculation": ["calcular impuesto", "cálculo irpf", "tramo", "base imponible", "deducción", "calculate tax", "tax bracket"],
        "legal_compliance": ["contrato", "despido", "legal", "cumplimiento", "normativa", "gdpr", "fundae", "compliance", "regulation"],
        "employee_lookup": ["buscar empleado", "perfil de", "quién es", "datos de", "find employee", "search staff"],
        "pto_check": ["vacaciones", "días libres", "ausencia", "permiso", "baja", "vacation", "pto", "leave", "time off"],
        "calendar_query": ["calendario", "reunión", "evento", "agenda", "calendar", "meeting", "schedule"],
        "hr_policy": ["política", "procedimiento", "protocolo", "norma interna", "policy", "handbook", "guideline"],
        "multi_module": ["y también", "además", "al mismo tiempo", "por otro lado", "and also", "as well as"],
        "code_generation": ["código", "script", "programa", "función", "clase", "api", "code", "write a function"],
        "multi_agent_orchestration": ["procesar nómina y contratar", "onboarding y payroll", "run onboarding"],
    }

    for domain, keywords in patterns.items():
        if any(kw in lower for kw in keywords):
            return domain, DOMAIN_COMPLEXITY.get(domain, 3)

    return "simple_query", DOMAIN_COMPLEXITY["simple_query"]


def estimate_tool_calls(user_message: str) -> int:
    """Estimate number of tool calls based on message patterns."""
    lower = user_message.lower()

    # Multi-action indicators
    multi_action_count = 0
    indicators = [" también ", " además ", " y ", " luego ", " después "]
    for indicator in indicators:
        multi_action_count += lower.count(indicator)

    # Specific tool patterns
    tool_patterns = {
        "buscar": 1,
        "crear": 1,
        "actualizar": 1,
        "eliminar": 1,
        "generar": 1,
        "calcular": 1,
        "procesar": 2,
        "analizar": 2,
        "comparar": 2,
    }

    base_tool_calls = 0
    for pattern, weight in tool_patterns.items():
        if pattern in lower:
            base_tool_calls += weight

    # Cap at reasonable limits
    estimated = min(base_tool_calls + multi_action_count, 10)
    return max(1, estimated)


def calculate_complexity_score(
    user_message: str,
    estimated_tokens: int = 0,
    domain_override: Optional[str] = None,
) -> float:
    """Calculate a complexity score (1-10) for routing decisions."""
    domain, domain_score = classify_domain(user_message)
    if domain_override:
        domain_score = DOMAIN_COMPLEXITY.get(domain_override, domain_score)

    tool_calls = estimate_tool_calls(user_message)
    token_factor = (estimated_tokens / 1000) * COMPLEXITY_FACTORS["token_estimate_per_1000"]

    # Safety sensitivity: check for destructive or sensitive operations
    lower = user_message.lower()
    safety_multiplier = 1.0
    sensitive_keywords = [
        "eliminar", "borrar", "despedir", "procesar nómina",
        "cambiar salario", "modificar contrato", "datos bancarios",
    ]
    if any(kw in lower for kw in sensitive_keywords):
        safety_multiplier = COMPLEXITY_FACTORS["safety_sensitivity"]

    score = (
        domain_score * 0.4
        + tool_calls * COMPLEXITY_FACTORS["tool_calls_predicted"] * 0.3
        + token_factor * 0.2
        + safety_multiplier * 0.1
    )

    return round(min(max(score, 1), 10), 1)


def select_tier(complexity_score: float) -> Tuple[str, Dict[str, Any]]:
    """Select the appropriate model tier based on complexity score."""
    tier_order = ["tier1_fast", "tier2_standard", "tier3_reasoning"]

    for tier_name in tier_order:
        tier_config = MODEL_TIERS[tier_name]
        if complexity_score <= tier_config["max_complexity"]:
            return tier_name, tier_config

    return "tier3_reasoning", MODEL_TIERS["tier3_reasoning"]


def select_model_for_tier(
    tier_config: Dict[str, Any],
    preferred_provider: Optional[str] = None,
    exclude_models: Optional[List[str]] = None,
) -> str:
    """Select a specific model from a tier, considering provider preferences."""
    models = tier_config["models"]
    exclude = exclude_models or []

    available = [m for m in models if m not in exclude]
    if not available:
        available = models

    # If preferred provider specified, try to match
    if preferred_provider:
        provider_prefixes = {
            "openai": ["gpt-", "o1", "o3"],
            "anthropic": ["claude-"],
            "google": ["gemini-"],
        }
        matching = [
            m
            for m in available
            for prefix in provider_prefixes.get(preferred_provider, [])
            if m.startswith(prefix)
        ]
        if matching:
            return matching[0]

    return available[0]


async def route_task(
    user_message: str,
    estimated_tokens: int = 0,
    preferred_provider: Optional[str] = None,
    budget_constrained: bool = False,
    domain: Optional[str] = None,
) -> RoutingDecision:
    """
    Main routing function. Analyzes the task and returns a routing decision.
    """
    complexity_score = calculate_complexity_score(
        user_message, estimated_tokens, domain
    )
    tier_name, tier_config = select_tier(complexity_score)

    # Budget constraint: force tier1 if budget is tight
    if budget_constrained and complexity_score <= 5:
        tier_name = "tier1_fast"
        tier_config = MODEL_TIERS["tier1_fast"]

    selected_model = select_model_for_tier(tier_config, preferred_provider)

    # Build fallback list (models from same or lower tiers)
    fallback_models = []
    all_tiers = ["tier1_fast", "tier2_standard", "tier3_reasoning"]
    tier_idx = all_tiers.index(tier_name)
    for i in range(tier_idx, len(all_tiers)):
        for m in MODEL_TIERS[all_tiers[i]]["models"]:
            if m != selected_model and m not in fallback_models:
                fallback_models.append(m)

    # Estimate cost
    est_input_tokens = estimated_tokens or 500
    est_output_tokens = 200
    est_cost = (
        est_input_tokens / 1000 * tier_config["cost_1k_input"]
        + est_output_tokens / 1000 * tier_config["cost_1k_output"]
    )

    routing = RoutingDecision(
        selected_model=selected_model,
        tier=tier_name,
        complexity_score=complexity_score,
        reasoning=f"Task classified with complexity {complexity_score}/10. "
        f"Domain: {classify_domain(user_message)[0]}. "
        f"Estimated tool calls: {estimate_tool_calls(user_message)}. "
        f"Routing to {tier_name} ({selected_model}).",
        estimated_latency_ms=tier_config["target_latency_ms"],
        estimated_cost_usd=round(est_cost, 6),
        fallback_models=fallback_models[:5],
    )

    logger.info(
        f"Model routing: {selected_model} (tier={tier_name}, "
        f"complexity={complexity_score}, cost=${routing.estimated_cost_usd:.6f})"
    )

    return routing


def get_tier_for_model(model_name: str) -> Optional[str]:
    """Get the tier name for a given model."""
    for tier_name, tier_config in MODEL_TIERS.items():
        if model_name in tier_config["models"]:
            return tier_name
    return None


def get_all_available_models() -> List[str]:
    """Get list of all available models across all tiers."""
    models = []
    for tier_config in MODEL_TIERS.values():
        models.extend(tier_config["models"])
    return models


def estimate_savings(
    complexity_score: float,
    default_model_cost_per_1k: float = 0.003,
) -> Dict[str, Any]:
    """Estimate cost savings from intelligent routing vs always using top tier."""
    _, selected_tier = select_tier(complexity_score)
    selected_cost = selected_tier["cost_1k_input"]

    savings_pct = ((default_model_cost_per_1k - selected_cost) / default_model_cost_per_1k) * 100

    return {
        "default_cost_per_1k": default_model_cost_per_1k,
        "selected_cost_per_1k": selected_cost,
        "savings_percentage": round(max(savings_pct, 0), 1),
        "tier_selected": selected_tier["description"],
    }


class MultiModelRouter:
    """
    Multi-model router that analyzes task complexity and selects
    the appropriate model tier for intelligent cost/performance routing.
    Wraps the standalone route_task function with caching support.
    """

    def __init__(self):
        self._cache: Dict[str, RoutingDecision] = {}

    async def route(
        self,
        user_message: str,
        agent: Optional[Any] = None,
        db: Optional[AsyncSession] = None,
        use_cache: bool = True,
        prefer_fast: bool = True,
    ) -> RoutingDecision:
        if prefer_fast:
            try:
                from app.services.model_router_fast import fast_model_route
                fast = fast_model_route(user_message)
                if fast:
                    decision = RoutingDecision(
                        selected_model=fast["selected_model"],
                        tier=fast["tier"],
                        complexity_score=fast["complexity_score"],
                        reasoning=f"Fast keyword routing: {fast['complexity_score']}/10",
                        estimated_latency_ms=fast.get("estimated_latency_ms", 500),
                        estimated_cost_usd=0.0001,
                        speculative=True,
                        fallback_models=MODEL_TIERS.get(fast["tier"], {}).get("models", [])[1:3],
                    )
                    self._last_tier = decision.tier
                    self._last_confidence = decision.complexity_score / 10.0
                    return decision
            except Exception as e:
                logger.debug(f"Fast routing skipped: {e}")
        # Determine budget constraint dynamically
        budget_constrained = False
        preferred_provider = None
        if agent:
            if agent.agent_settings:
                preferred_provider = agent.agent_settings.get("preferred_provider")
            
            if db:
                from app.services.agent_budget import check_budget, BudgetCheckResult
                try:
                    res = await check_budget(agent.id, 0.02, db)
                    if res in (BudgetCheckResult.WARNING, BudgetCheckResult.BLOCKED):
                        budget_constrained = True
                except Exception:
                    pass

        cache_key = f"{user_message[:100]}|{preferred_provider}|{budget_constrained}"
        if use_cache and cache_key in self._cache:
            logger.debug(f"Model routing cache hit for: {cache_key[:60]}...")
            decision = self._cache[cache_key]
            self._last_tier = decision.tier
            self._last_confidence = decision.complexity_score / 10.0
            return decision

        decision = await route_task(
            user_message=user_message,
            estimated_tokens=len(user_message) // 3,
            preferred_provider=preferred_provider,
            budget_constrained=budget_constrained,
        )

        self._last_tier = decision.tier
        self._last_confidence = decision.complexity_score / 10.0

        if use_cache:
            self._cache[cache_key] = decision
            if len(self._cache) > 100:
                self._cache.pop(next(iter(self._cache)))

        return decision

    def clear_cache(self):
        self._cache.clear()


async def record_model_performance(
    model_name: str,
    latency_ms: int,
    tokens_used: int,
    estimated_cost_usd: float,
    success: bool,
    task_complexity: Optional[float] = None,
    tenant_id: str = "unknown",
):
    """
    Record model performance metrics for analysis and future routing optimization.
    """
    try:
        logger.debug(
            f"Model performance recorded: {model_name} "
            f"(latency={latency_ms}ms, tokens={tokens_used}, "
            f"cost=${estimated_cost_usd:.6f}, success={success})"
        )
    except Exception as e:
        logger.warning(f"Failed to record model performance: {e}")
