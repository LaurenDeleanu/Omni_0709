import logging
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_router import get_llm_client
from app.models.agent import Agent

logger = logging.getLogger("successcore.hallucination")


async def detect_hallucination(
    output: str,
    agent: Agent,
    db: Optional[AsyncSession] = None,
    context: Optional[str] = None,
) -> Tuple[bool, dict]:
    if not output or len(output) < 20:
        return False, {"score": 0, "reason": "Output too short to evaluate"}

    try:
        client, _ = await get_llm_client("gpt-4o-mini", agent, db)

        grounding_info = f"\nContexto de referencia:\n{context[:3000]}\n" if context else ""

        judge_prompt = (
            "Eres un detector de alucinaciones para salidas de IA. Analiza el siguiente texto "
            "generado por un asistente de RRHH y determina si contiene informacion inventada, "
            "falsa o no respaldada por el contexto de referencia suministrado.\n\n"
            f"{grounding_info}\n"
            "Criterios de alucinacion:\n"
            "- Nombres de empleados o entidades no mencionadas en el contexto ni la base de datos\n"
            "- Cifras, estadisticas, fechas o plazos que no esten explicitamente en el contexto\n"
            "- Afirmaciones o politicas de empresa contradichas o no sustentadas por el contexto\n\n"
            f"Texto a evaluar:\n{output[:2000]}\n\n"
            "Responde estrictamente con JSON:\n"
            '{"hallucination_detected": true/false, "confidence": 0.0-1.0, "reason": "explicacion breve"}'
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[{"role": "user", "content": judge_prompt}]
        )

        raw = response.choices[0].message.content.strip() if response.choices else ""
        import json
        clean = raw
        if "{" in clean and "}" in clean:
            clean = clean[clean.find("{"):clean.rfind("}")+1]
        result = json.loads(clean)

        is_hallucination = result.get("hallucination_detected", False)
        if is_hallucination:
            logger.warning(f"Hallucination detected in agent output: {result.get('reason', '')[:200]}")
        return is_hallucination, {"confidence": result.get("confidence", 0), "reason": result.get("reason", "")}
    except Exception as e:
        logger.error(f"Hallucination detection error: {e}")
        return False, {"error": str(e)}

