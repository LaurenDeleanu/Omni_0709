import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("successcore.tool_adapter")

TEXT_TOOL_PREFIX = "[TOOL_CALL]"
TEXT_TOOL_SUFFIX = "[/TOOL_CALL]"
TEXT_TOOL_RESULT_PREFIX = "[TOOL_RESULT]"
TEXT_TOOL_RESULT_SUFFIX = "[/TOOL_RESULT]"


def tools_to_text_prompt(tools: List[Dict[str, Any]]) -> str:
    if not tools:
        return ""

    lines = [
        "\n\n[AVAILABLE TOOLS]\n",
        "You have access to the following tools. To use a tool, respond with:\n",
        f"{TEXT_TOOL_PREFIX}\n",
        '{{"name": "tool_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}\n',
        f"{TEXT_TOOL_SUFFIX}\n\n",
        "Available tools:\n",
    ]

    for tool in tools:
        func = tool.get("function", tool) if isinstance(tool, dict) else {}
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})
        required = func.get("parameters", {}).get("required", [])

        param_strs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "string")
            pdesc = pinfo.get("description", "")
            req = " (required)" if pname in required else ""
            param_strs.append(f"    - {pname}: {ptype}{req} — {pdesc}")

        param_text = "\n".join(param_strs) if param_strs else "    (no parameters)"
        lines.append(f"- {name}: {desc}\n  Parameters:\n{param_text}")

    return "\n".join(lines) + "\n[/AVAILABLE TOOLS]\n"


def parse_text_tool_call(response_text: str) -> Optional[Dict[str, Any]]:
    pattern = re.compile(
        rf"{re.escape(TEXT_TOOL_PREFIX)}\s*(.*?)\s*{re.escape(TEXT_TOOL_SUFFIX)}",
        re.DOTALL
    )
    match = pattern.search(response_text)
    if not match:
        return None

    json_str = match.group(1).strip()
    if json_str.startswith("```"):
        json_str = json_str[json_str.find("\n"):json_str.rfind("```")].strip()

    try:
        data = json.loads(json_str)
        name = data.get("name", data.get("tool", ""))
        args = data.get("arguments", data.get("args", data.get("parameters", {})))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"input": args}
        return {"name": name, "arguments": args}
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse text tool call JSON: {json_str[:200]}")
        return None


def format_tool_result_for_text(result: str, tool_name: str) -> str:
    return (
        f"\n{TEXT_TOOL_RESULT_PREFIX}\n"
        f"Tool: {tool_name}\n"
        f"Result: {result[:2000]}\n"
        f"{TEXT_TOOL_RESULT_SUFFIX}\n"
    )


def is_text_only_response(content: str) -> bool:
    return not content.strip() or "\u200b" in content or not any(
        c in content for c in ['{', '[', '{']
    )


def convert_tools_for_provider(tools: List[Dict[str, Any]], provider: str) -> Optional[List[Dict[str, Any]]]:
    if provider in ("anthropic", "claude"):
        anthropic_tools = []
        for tool in tools:
            func = tool.get("function", {})
            anthro_tool = {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}, "required": []}),
            }
            anthropic_tools.append(anthro_tool)
        return anthropic_tools

    if provider == "gemini":
        gemini_tools = []
        for tool in tools:
            func = tool.get("function", {})
            params = func.get("parameters", {})
            gemini_tool = {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        k: {"type": v.get("type", "STRING").upper(), "description": v.get("description", "")}
                        for k, v in params.get("properties", {}).items()
                    },
                    "required": params.get("required", []),
                },
            }
            gemini_tools.append(gemini_tool)
        return gemini_tools

    return tools


def parse_gemini_tool_call(response) -> Optional[List[Dict[str, Any]]]:
    try:
        parts = getattr(response, "parts", []) if hasattr(response, "parts") else []
        if not parts and hasattr(response, "candidates"):
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    parts.append(part)

        tool_calls = []
        for part in parts:
            if hasattr(part, "function_call"):
                fc = part.function_call
                tool_calls.append({
                    "name": fc.name,
                    "arguments": dict(fc.args) if fc.args else {},
                })
        return tool_calls if tool_calls else None
    except Exception as e:
        logger.debug(f"Gemini tool call parse: {e}")
        return None


def supports_tool_calling(model_id: str) -> bool:
    try:
        from app.services.model_catalog import MODEL_CATALOG
        spec = MODEL_CATALOG.get(model_id)
        if spec:
            return spec.supports_tools
    except Exception:
        pass
    return False


def get_model_provider(model_id: str) -> str:
    try:
        from app.services.model_catalog import MODEL_CATALOG
        spec = MODEL_CATALOG.get(model_id)
        if spec:
            return spec.provider
    except Exception:
        pass
    return "openai"


def make_mock_tool_call(name: str, arguments: Dict[str, Any]):
    class FunctionCall:
        def __init__(self, n, a):
            self.name = n
            self.arguments = json.dumps(a) if isinstance(a, dict) else str(a)
    class ToolCall:
        def __init__(self, fc):
            self.id = f"call_{name[:8]}"
            self.type = "function"
            self.function = fc
    class Message:
        def __init__(self, tc):
            self.role = "assistant"
            self.content = None
            self.tool_calls = [tc]
    return Message(ToolCall(FunctionCall(name, arguments)))
