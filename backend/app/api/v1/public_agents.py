import hashlib
import secrets
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db
from app.models.agent import Agent, AgentApiKey
from app.services.agent_runtime import execute_agent_run
from app.services.agent_directory import standardize_agent_output

logger = logging.getLogger("successcore.public_agents")

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class PublicAgentRunRequest(BaseModel):
    message: str
    user_context: Optional[dict] = None


async def _get_db_and_validate_key(api_key: str) -> tuple:
    if not api_key or not api_key.startswith("sk-"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    from app.core.database import AsyncSessionGlobal
    async with AsyncSessionGlobal() as db:
        result = await db.execute(
            select(AgentApiKey).where(
                AgentApiKey.key_hash == key_hash,
                AgentApiKey.is_active == True,
            )
        )
        key_record = result.scalar_one_or_none()

        if not key_record:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")

        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="API key has expired")

        key_record.last_used_at = datetime.now(timezone.utc)
        await db.commit()

    return key_record


async def _get_tenant_db_session(tenant_id: str) -> AsyncSession:
    from app.core.database import engine
    from sqlalchemy.ext.asyncio import AsyncSession as AS, async_sessionmaker

    if "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.SQLALCHEMY_DATABASE_URI:
        factory = async_sessionmaker(bind=engine, class_=AS, expire_on_commit=False)
    else:
        tenant_schema = f"tenant_{tenant_id}"
        tenant_engine = engine.execution_options(schema_translate_map={None: tenant_schema})
        factory = async_sessionmaker(bind=tenant_engine, class_=AS, expire_on_commit=False)

    return factory()


@router.post("/agents/{agent_id}/run")
@limiter.limit("10/minute")
async def public_run_agent(
    agent_id: str,
    body: PublicAgentRunRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    key_record = await _get_db_and_validate_key(x_api_key)

    if key_record.allowed_agents and isinstance(key_record.allowed_agents, list) and len(key_record.allowed_agents) > 0:
        if agent_id not in key_record.allowed_agents:
            raise HTTPException(status_code=403, detail="API key not authorized for this agent")

    try:
        rate_info = await _check_rate_limit(key_record)
        if not rate_info["allowed"]:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({key_record.rate_limit_per_minute}/min). Retry after {rate_info['retry_after']}s")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")

    db = await _get_tenant_db_session(key_record.tenant_id)
    try:
        agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found in this tenant")
        if not agent.is_active:
            raise HTTPException(status_code=400, detail="Agent is not active")

        input_payload = {
            "message": body.message,
            "user_id": key_record.created_by,
        }
        if body.user_context:
            input_payload["user_context"] = body.user_context

        result = await execute_agent_run(db, agent.id, input_payload, trigger_source="api_key")

        tool_calls = result.get("tool_calls", [])
        tools_used = list(set(tc.get("function", {}).get("name", "") for tc in tool_calls if tc.get("function", {}).get("name")))

        standard_output = await standardize_agent_output(
            agent_id=agent.id,
            raw_result=result.get("reply", ""),
            metadata={
                "tool_calls_made": len(tool_calls),
                "tools_used": tools_used,
                "tokens_used": result.get("tokens_used", {"input": result.get("input_tokens", 0), "output": result.get("output_tokens", 0)}),
                "cost": {"total_usd": result.get("cost_usd", 0.0)},
                "latency": {"total_ms": result.get("latency_ms", 0)},
                "model_used": agent.ai_model,
                "provider": "openai",
                "trace": result.get("trace", []),
                "warnings": result.get("warnings", []),
                "suggestions": result.get("suggestions", []),
                "status": result.get("status", "completed"),
                "confidence": result.get("confidence", 0.9),
                "task_description": body.message,
            },
            db=db,
        )
        return {"success": True, **standard_output}
    finally:
        await db.close()


@router.get("/agents")
async def list_public_agents(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    key_record = await _get_db_and_validate_key(x_api_key)

    db = await _get_tenant_db_session(key_record.tenant_id)
    try:
        result = await db.execute(select(Agent).where(Agent.is_active == True))
        agents = list(result.scalars().all())

        agent_list = []
        for agent in agents:
            if key_record.allowed_agents and isinstance(key_record.allowed_agents, list) and len(key_record.allowed_agents) > 0:
                if agent.id not in key_record.allowed_agents:
                    continue

            settings = agent.agent_settings or {}
            tools = settings.get("available_tools", settings.get("ai_tools", []))
            if isinstance(tools, str):
                try:
                    tools = json.loads(tools)
                except Exception:
                    tools = []

            agent_list.append({
                "agent_id": agent.id,
                "name": agent.name,
                "agent_type": agent.agent_type,
                "model": agent.ai_model,
                "tools": tools if isinstance(tools, list) else [],
                "description": settings.get("short_description", settings.get("description", "")),
            })

        return {"success": True, "total": len(agent_list), "agents": agent_list}
    finally:
        await db.close()


@router.get("/sdk/typescript")
async def generate_typescript_sdk(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    from fastapi.responses import Response
    key_record = await _get_db_and_validate_key(x_api_key)

    sdk_code = [
        "// SuccessCore Agent SDK for TypeScript",
        "// Auto-generated — use with your tenant API key",
        "",
        'const BASE_URL = process.env.SUCCESSCORE_API_URL || "http://localhost:8080/api/v1/public";',
        "",
        "export class SuccessCoreAgentClient {",
        "  private apiKey: string;",
        "",
        "  constructor(apiKey: string) {",
        "    this.apiKey = apiKey;",
        "  }",
        "",
        "  private async request(path: string, options: RequestInit = {}): Promise<any> {",
        "    const res = await fetch(BASE_URL + path, {",
        "      ...options,",
        "      headers: {",
        '        "Content-Type": "application/json",',
        '        "X-API-Key": this.apiKey,',
        "        ...options.headers,",
        "      },",
        "    });",
        "    if (!res.ok) {",
        "      const err = await res.json().catch(() => ({}));",
        '      throw new Error(err.detail || `API Error ${res.status}`);',
        "    }",
        "    return res.json();",
        "  }",
        "",
        "  async listAgents() {",
        '    return this.request("/agents");',
        "  }",
        "",
        "  async runAgent(agentId: string, message: string, userContext?: Record<string, any>) {",
        '    return this.request(`/agents/${agentId}/run`, {',
        "      method: 'POST',",
        '      body: JSON.stringify({ message, user_context: userContext }),',
        "    });",
        "  }",
        "}",
        "",
        "export default SuccessCoreAgentClient;",
    ]

    return Response(
        content="\n".join(sdk_code),
        media_type="text/typescript",
        headers={"Content-Disposition": "attachment; filename=successcore-agent-sdk.ts"},
    )


@router.get("/sdk/python")
async def generate_python_sdk(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    from fastapi.responses import Response
    key_record = await _get_db_and_validate_key(x_api_key)

    sdk_code = [
        "# SuccessCore Agent SDK for Python",
        "# Auto-generated — use with your tenant API key",
        "",
        "import os",
        "import requests",
        "from typing import Optional, Dict, Any, List",
        "",
        "",
        "class SuccessCoreAgentClient:",
        '    """Client for the SuccessCore Agent public API."""',
        "",
        "    def __init__(self, api_key: Optional[str] = None):",
        "        self.api_key = api_key or os.environ.get('SUCCESSCORE_API_KEY', '')",
        "        self.base_url = os.environ.get(",
        '            "SUCCESSCORE_API_URL",',
        '            "http://localhost:8080/api/v1/public",',
        "        )",
        "        if not self.api_key:",
        '            raise ValueError("API key required. Set SUCCESSCORE_API_KEY or pass api_key parameter.")',
        "",
        "    def _headers(self) -> Dict[str, str]:",
        "        return {",
        '            "Content-Type": "application/json",',
        '            "X-API-Key": self.api_key,',
        "        }",
        "",
        "    def list_agents(self) -> Dict[str, Any]:",
        '        """List available agents for this API key."""',
        '        resp = requests.get(f"{self.base_url}/agents", headers=self._headers())',
        "        resp.raise_for_status()",
        "        return resp.json()",
        "",
        "    def run_agent(",
        "        self,",
        "        agent_id: str,",
        "        message: str,",
        "        user_context: Optional[Dict[str, Any]] = None,",
        "    ) -> Dict[str, Any]:",
        '        """Execute an agent with the given message."""',
        "        payload = {'message': message}",
        "        if user_context:",
        "            payload['user_context'] = user_context",
        '        resp = requests.post(',
        '            f"{self.base_url}/agents/{agent_id}/run",',
        "            json=payload,",
        "            headers=self._headers(),",
        "        )",
        "        resp.raise_for_status()",
        "        return resp.json()",
    ]

    return Response(
        content="\n".join(sdk_code),
        media_type="text/x-python",
        headers={"Content-Disposition": "attachment; filename=successcore_agent_sdk.py"},
    )


_rate_limit_store: dict = {}


async def _check_rate_limit(key_record) -> dict:
    key_hash = key_record.key_hash
    now = datetime.now(timezone.utc)
    limit = key_record.rate_limit_per_minute

    if key_hash not in _rate_limit_store:
        _rate_limit_store[key_hash] = {"count": 0, "window_start": now}

    window = _rate_limit_store[key_hash]
    elapsed = (now - window["window_start"]).total_seconds()

    if elapsed > 60:
        window["count"] = 0
        window["window_start"] = now

    if window["count"] >= limit:
        return {"allowed": False, "retry_after": int(60 - elapsed)}

    window["count"] += 1
    return {"allowed": True, "remaining": limit - window["count"]}
