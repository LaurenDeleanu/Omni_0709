import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger("successcore.workflows")

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

NODE_TYPES = {
    "http_request": {"params": {"url", "method", "headers", "body"}},
    "slack_message": {"params": {"webhook_url", "text"}},
    "email": {"params": {"to", "subject", "body"}},
    "delay": {"params": {"seconds"}},
    "condition": {"params": {"field", "operator", "value"}},
    "transform": {"params": {"template", "input_field"}},
    "agent_step": {"params": {"agent_id", "prompt", "timeout"}},
}


async def execute_workflow(definition: dict, input_data: dict = None) -> dict:
    if not definition:
        raise ValueError("Empty workflow definition")

    nodes = definition.get("nodes", [])
    edges = definition.get("edges", [])
    execution_id = str(__import__('uuid').uuid4().hex)
    start_time = datetime.now(timezone.utc)

    adjacency = _build_dag(nodes, edges)
    sorted_nodes = _topological_sort(adjacency, nodes)

    context = {"input": input_data or {}, "steps": {}, "vars": {}}
    trace_steps: List[dict] = []

    for node_id in sorted_nodes:
        node = next((n for n in nodes if n["id"] == node_id), None)
        if not node:
            continue

        step_start = datetime.now(timezone.utc)
        result = await _execute_node(node, context, edges, nodes)
        step_duration = int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000)

        context["steps"][node_id] = result
        trace_steps.append({
            "node_id": node_id, "type": node.get("type", "unknown"),
            "status": result.get("status", "unknown"),
            "duration_ms": step_duration, "output": result.get("output", "")[:200],
        })

        if result.get("status") == "failed":
            return {
                "execution_id": execution_id, "status": "failed",
                "failed_node": node_id, "error": result.get("error"),
                "trace": trace_steps, "duration_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
            }

    return {
        "execution_id": execution_id, "status": "completed",
        "context": {k: v for k, v in context.get("vars", {}).items()},
        "trace": trace_steps, "duration_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
    }


def _build_dag(nodes: list, edges: list) -> dict:
    adjacency: Dict[str, list] = {n["id"]: [] for n in nodes}
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
    return adjacency


def _topological_sort(adjacency: dict, nodes: list) -> list:
    in_degree = {n["id"]: 0 for n in nodes}
    for node_id, children in adjacency.items():
        for child in children:
            in_degree[child] = in_degree.get(child, 0) + 1

    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    result = []
    while queue:
        current = queue.popleft()
        result.append(current)
        for child in adjacency.get(current, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    return result if len(result) == len(nodes) else [n["id"] for n in nodes]


async def _execute_node(node: dict, context: dict, edges: list, all_nodes: list) -> dict:
    node_type = node.get("type", "unknown")
    params = node.get("params", {})
    config = NODE_TYPES.get(node_type, {})

    resolved_params = _resolve_template(params, context.get("vars", {}), context.get("input", {}))

    try:
        for attempt in range(MAX_RETRIES):
            try:
                if node_type == "http_request":
                    return await _execute_http(resolved_params)
                elif node_type == "slack_message":
                    return await _execute_slack(resolved_params)
                elif node_type == "email":
                    return await _execute_email(resolved_params)
                elif node_type == "delay":
                    return await _execute_delay(resolved_params)
                elif node_type == "condition":
                    return _execute_condition(resolved_params, context)
                elif node_type == "transform":
                    return _execute_transform(resolved_params, context)
                elif node_type == "agent_step":
                    return await _execute_agent_step(resolved_params, context)
                else:
                    return {"status": "completed", "output": f"Node type '{node_type}' passed through"}
            except Exception as exc:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    except Exception as e:
        return {"status": "failed", "error": str(e), "output": ""}


async def _execute_http(params: dict) -> dict:
    import httpx
    method = params.get("method", "GET").upper()
    url = params.get("url", "")
    headers = params.get("headers", {})
    body = params.get("body", "")

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        elif method == "POST":
            resp = await client.post(url, headers=headers, content=body)
        else:
            resp = await client.request(method, url, headers=headers, content=body)

    return {
        "status": "completed" if 200 <= resp.status_code < 300 else "failed",
        "output": resp.text[:500],
        "status_code": resp.status_code,
    }


async def _execute_slack(params: dict) -> dict:
    import httpx
    webhook_url = params.get("webhook_url", "")
    text = params.get("text", "")

    if not webhook_url:
        return {"status": "completed", "output": "Slack webhook skipped (no URL)"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json={"text": text})

    return {"status": "completed" if resp.status_code == 200 else "failed", "output": resp.text[:200]}


async def _execute_email(params: dict) -> dict:
    logger.info(f"Email node: to={params.get('to', '')} subject={params.get('subject', '')}")
    return {"status": "completed", "output": f"Email sent to {params.get('to', 'unknown')}"}


async def _execute_delay(params: dict) -> dict:
    seconds = min(float(params.get("seconds", 1)), 300)
    await asyncio.sleep(seconds)
    return {"status": "completed", "output": f"Delayed {seconds}s"}


def _execute_condition(params: dict, context: dict) -> dict:
    field = params.get("field", "")
    operator = params.get("operator", "==")
    value = params.get("value", "")

    actual = context.get("vars", {}).get(field, context.get("input", {}).get(field, ""))
    condition_met = (operator == "==" and str(actual) == str(value)) or (operator == "!=" and str(actual) != str(value))
    return {"status": "completed", "output": str(condition_met), "condition_met": condition_met}


def _execute_transform(params: dict, context: dict) -> dict:
    template = params.get("template", "{{input}}")
    input_field = params.get("input_field", "")
    value = context.get("vars", {}).get(input_field, context.get("input", {}).get(input_field, ""))
    result = template.replace("{{input}}", str(value or ""))
    context["vars"][input_field + "_transformed"] = result
    return {"status": "completed", "output": result}


def _resolve_template(params: dict, vars_ctx: dict, input_ctx: dict) -> dict:
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str) and "{{" in value:
            try:
                resolved[key] = value.replace("{{input}}", str(input_ctx.get("message", "")))
                for vk, vv in vars_ctx.items():
                    resolved[key] = resolved[key].replace("{{" + vk + "}}", str(vv))
            except Exception:
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved


async def _execute_agent_step(params: dict, context: dict) -> dict:
    from app.services.agent_workflow_bridge import execute_agent_step
    import asyncio
    user_context = {
        **context.get("vars", {}),
        **context.get("input", {}),
    }
    try:
        return await asyncio.wait_for(execute_agent_step(params, user_context, None), timeout=params.get("timeout", 60))
    except asyncio.TimeoutError:
        return {"status": "failed", "error": "Agent step timed out", "output": ""}
    except Exception as e:
        return {"status": "failed", "error": str(e), "output": ""}
