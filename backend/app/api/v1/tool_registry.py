from fastapi import APIRouter, Depends
from typing import Optional
from app.services.tool_binding_registry import TOOL_BINDINGS, get_safe_employee_tools

router = APIRouter()


@router.get("/tools/registry")
async def get_tool_registry():
    modules = {}
    categories = {}
    role_requirements = {}

    for name, binding in TOOL_BINDINGS.items():
        module = binding.get("module", "unknown")
        category = binding.get("category", "unknown")
        role = binding.get("requires_role", "employee")

        if module not in modules:
            modules[module] = []
        modules[module].append({
            "name": name,
            "category": category,
            "role_required": role,
        })

        if category not in categories:
            categories[category] = 0
        categories[category] += 1

        if role not in role_requirements:
            role_requirements[role] = 0
        role_requirements[role] += 1

    return {
        "total_tools": len(TOOL_BINDINGS),
        "modules": [
            {"name": mod, "count": len(tools), "tools": tools}
            for mod, tools in sorted(modules.items())
        ],
        "categories": categories,
        "role_requirements": role_requirements,
    }


@router.get("/tools/agent-tools/{agent_id}")
async def get_agent_tools(agent_id: str):
    safe_tools = get_safe_employee_tools()

    return {
        "agent_id": agent_id,
        "available_tools": len(safe_tools),
        "tools": sorted(safe_tools),
    }
