import json
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def generate_explanation_chain(
    decision: str,
    evidence: list,
    reasoning_steps: list,
    risks: Optional[list] = None,
    alternatives: Optional[list] = None,
    confidence: float = 0.8,
) -> str:
    evidence_lines = []
    for i, (ev, reason) in enumerate(zip(evidence, reasoning_steps), 1):
        evidence_lines.append(f"{i}. **{ev}** which indicates *{reason}*")

    evidence_text = "\n".join(evidence_lines) if evidence_lines else "No evidence provided."

    risks_text = ""
    if risks:
        risks_text = "\n**Risks of this decision:**\n"
        for r in risks:
            risks_text += f"- {r}\n"

    alternatives_text = ""
    if alternatives:
        alternatives_text = "\n**Alternatives considered:**\n"
        for a in alternatives:
            alternatives_text += f"- {a}\n"

    confidence_pct = int(confidence * 100)

    return (
        f"I recommend **{decision}** because:\n\n"
        f"{evidence_text}\n"
        f"{risks_text}"
        f"{alternatives_text}"
        f"\n**Confidence:** {confidence_pct}%"
    )


async def explain_tool_decision(
    tool_name: str,
    tool_args: dict,
    tool_result: str,
    rationale: str,
) -> str:
    args_str = json.dumps(tool_args, default=str)
    result_summary = tool_result[:300] + "..." if len(tool_result) > 300 else tool_result

    return (
        f"I used the `{tool_name}` tool with `{args_str}` because {rationale}. "
        f"The tool returned: {result_summary}"
    )


async def build_reasoning_tree(
    agent_run_id: str,
    db: AsyncSession,
) -> dict:
    from app.models.agent import AgentExecutionRun

    result = await db.execute(
        select(AgentExecutionRun).where(AgentExecutionRun.id == agent_run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        return {"error": f"AgentExecutionRun {agent_run_id} not found", "tree": None}

    trace_raw = run.execution_trace

    try:
        if isinstance(trace_raw, str):
            trace = json.loads(trace_raw)
        else:
            trace = trace_raw or []
    except (json.JSONDecodeError, TypeError):
        trace = []

    if not isinstance(trace, list):
        trace = []

    query_text = ""
    if run.input_payload:
        if isinstance(run.input_payload, str):
            try:
                query_text = json.loads(run.input_payload).get("message", "")
            except json.JSONDecodeError:
                query_text = run.input_payload
        elif isinstance(run.input_payload, dict):
            query_text = run.input_payload.get("message", "")

    nodes = []
    edges = []

    root_id = "query_root"
    nodes.append({
        "id": root_id,
        "type": "query",
        "label": query_text[:200] or "Agent query",
    })

    prev_node_id = root_id

    for i, step in enumerate(trace):
        step_node_id = f"step_{i}"

        if isinstance(step, dict):
            step_type = step.get("step", f"unknown_{i}")
            details = step.get("details", "")
            action = step.get("action", "")

            node_type = "observation"
            label = f"{step_type}"

            if "llm" in step_type.lower():
                node_type = "llm_call"
                label = f"LLM: {step_type}"
            elif "tool" in step_type.lower():
                node_type = "tool_call"
                label = f"Tool: {step_type}"
                if isinstance(details, list):
                    label = f"Tools: {', '.join(details)}"
            elif "rag" in step_type.lower():
                node_type = "knowledge"
                label = "RAG retrieval"
            elif "react" in step_type.lower():
                node_type = "react"
                label = f"ReAct: {step.get('total_iterations', '?')} iterations"
            elif "moderation" in step_type.lower():
                node_type = "guard"
                label = "Moderation check"
            elif "hallucination" in step_type.lower():
                node_type = "guard"
                label = "Hallucination check"
            elif "cache" in step_type.lower():
                node_type = "cache"
                label = f"Cache: {details if details else 'hit'}"
            elif "fallback" in step_type.lower():
                node_type = "fallback"
                label = f"Fallback: {details}"
            elif "error" in step_type.lower() or "fail" in step_type.lower():
                node_type = "error"
                label = f"Error: {step.get('error', 'unknown')[:100]}"

            if action == "return_reply":
                node_type = "output"
                label = "Final reply"

            nodes.append({
                "id": step_node_id,
                "type": node_type,
                "label": label[:200],
                "metadata": {k: str(v)[:200] for k, v in step.items() if k not in ("step", "action", "details")},
            })

            edges.append({
                "from": prev_node_id,
                "to": step_node_id,
                "label": "next",
            })
            prev_node_id = step_node_id

    return {
        "run_id": agent_run_id,
        "tree": {
            "nodes": nodes,
            "edges": edges,
            "root_id": root_id,
        }
    }
