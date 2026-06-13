import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CONFIDENCE_SYSTEM_PROMPT = """You are a confidence scoring engine. Rate the confidence of an AI agent's response on a scale from 0 to 100%.

Consider these factors:
- **Tool-call success rate**: Were all tool calls successful? Did any fail or return errors?
- **Data freshness**: Is the data up to date or could it be stale?
- **Factual grounding**: Are all factual claims supported by evidence or retrievals, or are they speculative?
- **Query ambiguity**: Was the original question ambiguous or underspecified?

For any uncertain claims, flag them with a reason and suggestion for verification.

Respond with valid JSON:
{
  "confidence_score": 87,
  "uncertainty_flags": [
    {
      "claim": "The specific uncertain claim",
      "reason": "Why it is uncertain",
      "suggestion": "How to verify or what caveat to add"
    }
  ]
}"""


async def score_response_confidence(
    response: str,
    model: str = "gpt-4o-mini",
    tools_used: list = None,
    query_complexity: str = "medium",
) -> dict:
    from app.services.llm_router import get_llm_client

    tools_text = ", ".join(tools_used) if tools_used else "None"

    score_messages = [
        {"role": "system", "content": CONFIDENCE_SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Query complexity: {query_complexity}\n"
            f"Tools used: {tools_text}\n\n"
            f"Response to evaluate:\n---\n{response[:3000]}\n---\n\n"
            "Rate your confidence in this response and flag any uncertain claims. Respond with JSON."
        )},
    ]

    try:
        client, _ = await get_llm_client(model, None, None)
        completion = await client.chat.completions.create(
            model=model,
            messages=score_messages,
            temperature=0.1,
        )
        content = completion.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return {
                "confidence_score": 50,
                "uncertainty_flags": [],
                "parse_error": content[:200],
            }
    except Exception as e:
        logger.warning(f"Confidence scoring call failed: {e}")
        return {
            "confidence_score": 50,
            "uncertainty_flags": [],
            "error": str(e),
        }


async def append_confidence_metadata(response: str, confidence: dict) -> str:
    score = confidence.get("confidence_score", 50)
    flags = confidence.get("uncertainty_flags", [])

    flags_text = ""
    if flags:
        parts = []
        for f in flags[:3]:
            parts.append(f"{f.get('claim', '')}: {f.get('reason', '')}")
        if parts:
            flags_text = " - " + " | ".join(parts)

    confidence_line = f"\n\n[Confidence: {score}%{flags_text}]"

    return response + confidence_line
