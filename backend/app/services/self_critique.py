import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CRITIQUE_SYSTEM_PROMPT = """You are a quality assurance reviewer for AI agent responses.
Review the given agent response for the following dimensions:

1. **Completeness** (1-5): Did it address all parts of the query?
2. **Accuracy** (1-5): Any factual errors or contradictions?
3. **Hallucination Risk** (1-5): Any made-up facts, citations, or data? (1 = high hallucination, 5 = no hallucination)
4. **Policy Compliance** (1-5): Does it respect GDPR, fairness, confidentiality, and internal policies?
5. **Clarity** (1-5): Is the response well-structured, concise, and helpful?

Rate each dimension 1-5. Identify specific issues with line references. Suggest rewrites for problematic sections.

Respond with valid JSON:
{
  "overall_score": 3.5,
  "completeness": 4,
  "accuracy": 4,
  "hallucination_risk": 3,
  "policy_compliance": 5,
  "clarity": 4,
  "issues": [
    {
      "dimension": "accuracy",
      "description": "Specific issue found",
      "suggestion": "How to fix it",
      "severity": "high"
    }
  ]
}"""


async def critique_response(
    response: str,
    original_query: str,
    tools_used: list,
    agent_context: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
) -> dict:
    from app.services.llm_router import get_llm_client

    critique_messages = [
        {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Original query: {original_query}\n\n"
            f"Agent context: {agent_context[:1000]}\n\n"
            f"Tools used: {', '.join(tools_used) if tools_used else 'None'}\n\n"
            f"Agent response to review:\n---\n{response}\n---\n\n"
            "Review this response and provide your critique as JSON."
        )},
    ]

    from openai import AsyncOpenAI
    try:
        client, _ = await get_llm_client(model, None, None)
        completion = await client.chat.completions.create(
            model=model,
            messages=critique_messages,
            temperature=temperature,
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
                "overall_score": 3.0,
                "completeness": 3,
                "accuracy": 3,
                "hallucination_risk": 3,
                "policy_compliance": 3,
                "clarity": 3,
                "issues": [],
                "parse_error": content[:200],
            }
    except Exception as e:
        logger.warning(f"Critique call failed: {e}")
        return {
            "overall_score": 3.0,
            "completeness": 3,
            "accuracy": 3,
            "hallucination_risk": 3,
            "policy_compliance": 3,
            "clarity": 3,
            "issues": [],
            "error": str(e),
        }


async def auto_correct_response(
    response: str,
    critique: dict,
    original_query: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.4,
) -> str:
    from app.services.llm_router import get_llm_client

    issues_text = ""
    for issue in critique.get("issues", []):
        issues_text += f"- [{issue.get('dimension', 'unknown')}] {issue.get('description', '')} -> {issue.get('suggestion', '')}\n"

    correct_messages = [
        {"role": "system", "content": (
            "You are a response improvement engine. You have received a critique of a previous response. "
            "Your task is to rewrite the response incorporating the suggested fixes while preserving the useful content. "
            "Improve completeness, accuracy, clarify any vague statements, and remove any unsupported claims."
        )},
        {"role": "user", "content": (
            f"Original query: {original_query}\n\n"
            f"Original response:\n---\n{response}\n---\n\n"
            f"Critique scores: Overall={critique.get('overall_score')}, "
            f"Completeness={critique.get('completeness')}, Accuracy={critique.get('accuracy')}, "
            f"HallucinationRisk={critique.get('hallucination_risk')}, "
            f"Policy={critique.get('policy_compliance')}, Clarity={critique.get('clarity')}\n\n"
            f"Identified issues:\n{issues_text}\n\n"
            "Provide the corrected/improved response now. Only output the final corrected response."
        )},
    ]

    try:
        client, _ = await get_llm_client(model, None, None)
        completion = await client.chat.completions.create(
            model=model,
            messages=correct_messages,
            temperature=temperature,
        )
        return completion.choices[0].message.content or response
    except Exception as e:
        logger.warning(f"Auto-correct call failed: {e}")
        return response


async def run_self_critique_cycle(
    response: str,
    original_query: str,
    tools_used: list,
    agent_context: str,
    max_iterations: int = 2,
    critique_model: str = "gpt-4o-mini",
    correct_model: str = "gpt-4o-mini",
) -> dict:
    all_versions = [{"response": response, "critique": None, "score": None}]
    best_version = response
    best_score = 0.0

    current_response = response

    for iteration in range(max_iterations):
        critique = await critique_response(
            current_response, original_query, tools_used, agent_context,
            model=critique_model,
        )

        score = critique.get("overall_score", 3.0)
        all_versions[-1]["critique"] = critique
        all_versions[-1]["score"] = score

        if score > best_score:
            best_score = score
            best_version = current_response

        if score >= 4.0:
            break

        corrected = await auto_correct_response(
            current_response, critique, original_query,
            model=correct_model,
        )

        if corrected == current_response:
            break

        current_response = corrected
        all_versions.append({"response": corrected, "critique": None, "score": None})

    return {
        "final_response": best_version,
        "best_score": best_score,
        "iterations": len(all_versions),
        "all_versions": all_versions,
    }
