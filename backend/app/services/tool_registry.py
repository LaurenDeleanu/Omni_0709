import json
import logging
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger("successcore.tools")


TOOL_REGISTRY: Dict[str, dict] = {}

# ── Canonical Tool Name Aliases ──────────────────────────────────────────────
# Maps alternative/legacy tool names to their canonical registered name.
# When agent_fleet.py references "get_employee_profile" but the tool is
# registered as "get_employee_profile_full", this alias ensures resolution.
TOOL_NAME_ALIASES: Dict[str, str] = {
    # HR tools
    "get_employee_profile": "get_employee_profile_full",
    "get_pto_balance": "get_pto_balance",
    "search_employees": "search_employees_advanced",
    "get_expense_summary": "get_expense_summary_agg",
    # Legacy/alternative names
    "list_department_members": "get_department_members",
    "get_vacation_balance": "get_pto_balance",
    "get_upcoming_vacations": "get_upcoming_vacations",
    "get_org_chart": "get_org_chart",
}


def register_tool(name: str, schema: dict, handler_func: Callable):
    """Register a tool with its schema and handler function."""
    TOOL_REGISTRY[name] = {"schema": schema, "handler": handler_func}


def resolve_tool_name(name: str) -> str:
    """Resolve a tool name through aliases to its canonical name.
    
    If the name exists directly in the registry, return it.
    If it's an alias, return the canonical name.
    Otherwise return the original name (caller will handle not-found).
    """
    if name in TOOL_REGISTRY:
        return name
    canonical = TOOL_NAME_ALIASES.get(name)
    if canonical and canonical in TOOL_REGISTRY:
        return canonical
    return name


def get_all_tool_schemas() -> list:
    """Return all registered tool schemas."""
    return [t["schema"] for t in TOOL_REGISTRY.values()]


def get_tool_handler(name: str) -> Optional[Callable]:
    """Get a tool's handler function by name, resolving aliases."""
    resolved = resolve_tool_name(name)
    entry = TOOL_REGISTRY.get(resolved)
    if entry:
        return entry.get("handler")
    return None


def get_tool_schema_by_name(name: str) -> Optional[dict]:
    """Get a single tool schema by name, resolving aliases."""
    resolved = resolve_tool_name(name)
    entry = TOOL_REGISTRY.get(resolved)
    if entry:
        return entry.get("schema")
    return None


def get_tools_for_agent(tool_names: List[str]) -> List[dict]:
    """Given a list of tool names (possibly with aliases), return their schemas.
    
    This is the primary function used by agent_context_builder to resolve
    an agent's configured tool list into actual OpenAI-format tool schemas.
    Logs warnings for unresolvable tool names.
    """
    schemas = []
    seen = set()
    for name in tool_names:
        resolved = resolve_tool_name(name)
        if resolved in TOOL_REGISTRY and resolved not in seen:
            schemas.append(TOOL_REGISTRY[resolved]["schema"])
            seen.add(resolved)
        elif name not in seen:
            # Try the legacy AVAILABLE_TOOLS_SCHEMA as final fallback
            from app.services.tool_executor import AVAILABLE_TOOLS_SCHEMA
            for s in AVAILABLE_TOOLS_SCHEMA:
                sname = s.get("function", {}).get("name", "")
                if sname == name and sname not in seen:
                    schemas.append(s)
                    seen.add(sname)
                    break
            else:
                logger.warning(
                    f"Tool '{name}' (resolved: '{resolved}') not found in "
                    f"registry or schema list — agent will not have this tool"
                )
    return schemas


def list_all_tool_names() -> List[str]:
    """List all canonical tool names in the registry."""
    return list(TOOL_REGISTRY.keys())


def generate_tool_scaffold(agent_request: str) -> dict:
    return {
        "status": "scaffold_generated",
        "tool_name": f"custom_tool_{hash(agent_request) % 10000:04d}",
        "request": agent_request,
        "template": {
            "type": "function",
            "function": {
                "name": f"custom_tool_{hash(agent_request) % 10000:04d}",
                "description": agent_request[:200],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search or action parameter"}
                    },
                    "required": ["query"]
                }
            }
        },
        "handler_code": f'''async def handler(db, arguments):
    import json
    try:
        result = {{"status": "ok", "query": arguments.get("query", "")}}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({{"error": str(e)}})'''
    }

