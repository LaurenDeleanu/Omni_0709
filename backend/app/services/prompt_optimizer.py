import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.harness_service import run_evaluation_suite

logger = logging.getLogger("successcore.prompt_tuning")

VARIANTS = [
    {"label": "original", "prompt_suffix": "", "temperature": None},
    {"label": "concise", "prompt_suffix": "\nSe conciso y directo en tu respuesta. Usa viñetas cuando sea apropiado.", "temperature": 0.3},
    {"label": "detailed", "prompt_suffix": "\nProporciona una respuesta detallada y exhaustiva con ejemplos concretos.", "temperature": 0.7},
    {"label": "empathetic", "prompt_suffix": "\nResponde con empatia y calidez humana. Reconoce las emociones del usuario.", "temperature": 0.8},
]


async def optimize_prompt(
    db: AsyncSession,
    agent_id: str,
    suite_id: str,
    iterations: int = 3,
) -> dict:
    from app.models.agent import Agent
    from sqlalchemy import select

    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise ValueError("Agent not found")

    original_prompt = agent.ai_system_prompt
    results: List[dict] = []

    for variant in VARIANTS:
        test_prompt = original_prompt + variant["prompt_suffix"]
        orig_temp = agent.ai_temperature

        agent.ai_system_prompt = test_prompt
        if variant["temperature"] is not None:
            agent.ai_temperature = variant["temperature"]
        await db.flush()

        try:
            suite_result = await run_evaluation_suite(db, agent_id, suite_id)
            results.append({
                "variant": variant["label"],
                "passed": suite_result["passed_count"],
                "failed": suite_result["failed_count"],
                "total": suite_result["total_count"],
                "pass_rate": round(suite_result["passed_count"] / max(suite_result["total_count"], 1) * 100, 1),
                "description": variant["prompt_suffix"].strip()[:100] if variant["prompt_suffix"] else "Baseline",
            })
        except Exception as e:
            results.append({"variant": variant["label"], "error": str(e)})

        agent.ai_system_prompt = original_prompt
        agent.ai_temperature = orig_temp

    await db.flush()

    results.sort(key=lambda r: r.get("pass_rate", 0), reverse=True)
    best = results[0] if results else {}

    return {
        "agent_id": agent_id,
        "suite_id": suite_id,
        "variants_tested": len(results),
        "results": results,
        "best_variant": best.get("variant"),
        "best_pass_rate": best.get("pass_rate"),
        "recommendation": f"Switch to '{best.get('variant')}' variant for {best.get('pass_rate')}% pass rate" if best else "No results",
    }
