import time
import json
import logging
import uuid
from typing import Any, Optional, Callable, Awaitable
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentOrchestrationRun
from app.services.agent_runtime import execute_agent_run
from app.services.llm_router import get_llm_client

logger = logging.getLogger("successcore.agent_swarm")

HANDOFF_TOOL = {
    "type": "function",
    "function": {
        "name": "handoff_to_agent",
        "description": "Hand off the current conversation to another specialized agent. Call this when you determine another agent is better suited to handle the user's request.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent_type": {
                    "type": "string",
                    "description": "The agent type to hand off to (e.g. PAYROLL_SPECIALIST, IT_HELPDESK, RECRUITER, etc.)",
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why this handoff is needed.",
                },
                "context_summary": {
                    "type": "string",
                    "description": "Summary of the conversation so far for the receiving agent.",
                },
            },
            "required": ["target_agent_type", "reason", "context_summary"],
        },
    },
}


class AgentTurn(BaseModel):
    agent_id: str
    agent_name: str
    agent_type: str
    output: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    status: str = "success"
    handoff_target: Optional[str] = None


class SwarmResult(BaseModel):
    orchestration_id: str
    turns: list[AgentTurn]
    final_output: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    handoff_chain: list[str] = Field(default_factory=list)


class SwarmOrchestrator:

    def __init__(self, max_handoffs: int = 5, turn_timeout: int = 120):
        self.max_handoffs = max_handoffs
        self.turn_timeout = turn_timeout

    async def run(
        self,
        task: str,
        starting_agent_id: str,
        agents: dict[str, dict],
        db: AsyncSession,
        user_id: str = "",
        tenant_id: str = "default",
        progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None,
    ) -> SwarmResult:
        start_time = time.monotonic()

        orchestration_id = uuid.uuid4().hex
        run_log = AgentOrchestrationRun(
            id=orchestration_id,
            mode="swarm",
            agent_ids=json.dumps([starting_agent_id]),
            input_message=task,
            status="running",
        )
        db.add(run_log)
        await db.flush()

        turns: list[AgentTurn] = []
        handoff_chain: list[str] = [starting_agent_id]
        current_agent_id = starting_agent_id
        conversation_context = f"User task: {task}"
        seen_agents: set[str] = {starting_agent_id}

        for handoff_count in range(self.max_handoffs + 1):
            if current_agent_id not in agents:
                logger.error(f"Agent {current_agent_id} not found in agents map")
                break

            if progress_callback:
                agent_info = agents[current_agent_id]
                await progress_callback("turn_start", {
                    "agent_id": current_agent_id,
                    "agent_name": agent_info.get("name", current_agent_id),
                    "handoff_count": handoff_count,
                })

            turn = await self._execute_agent_turn(
                agent_id=current_agent_id,
                context=conversation_context,
                agents=agents,
                db=db,
                user_id=user_id,
                tenant_id=tenant_id,
            )

            if turn is None:
                break

            turns.append(turn)

            if progress_callback:
                await progress_callback("turn_complete", turn.model_dump())

            if turn.handoff_target and handoff_count < self.max_handoffs:
                target = turn.handoff_target
                if target in seen_agents:
                    logger.warning(f"Circular handoff detected: {target} already visited. Breaking.")
                    break
                seen_agents.add(target)
                handoff_chain.append(target)
                current_agent_id = target
                conversation_context = (
                    f"ORIGINAL USER TASK: {task}\n\n"
                    f"HANDOFF REASON: The previous agent handed off to you.\n\n"
                    f"PREVIOUS AGENT CONTEXT:\n{turn.output[:3000]}"
                )
            else:
                break

        total_latency = int((time.monotonic() - start_time) * 1000)
        total_tokens = sum(t.tokens_used for t in turns)
        total_cost = sum(t.cost_usd for t in turns)
        final_output = turns[-1].output if turns else "No agents executed."

        run_log.status = "success" if turns and all(t.status == "success" for t in turns) else "partial"
        run_log.output_result = final_output[:10000]
        run_log.execution_trace = json.dumps([t.model_dump() for t in turns])
        run_log.token_usage = total_tokens
        run_log.total_cost_usd = total_cost
        run_log.total_latency_ms = total_latency
        run_log.agent_ids = json.dumps(handoff_chain)
        await db.commit()

        return SwarmResult(
            orchestration_id=orchestration_id,
            turns=turns,
            final_output=final_output,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
            handoff_chain=handoff_chain,
        )

    async def _execute_agent_turn(
        self,
        agent_id: str,
        context: str,
        agents: dict[str, dict],
        db: AsyncSession,
        user_id: str = "",
        tenant_id: str = "default",
    ) -> Optional[AgentTurn]:
        agent_info = agents.get(agent_id, {})
        turn_start = time.monotonic()

        turn_message = context
        if agents:
            available_list = [
                f"{a['agent_type']}: {a.get('name', aid)}"
                for aid, a in agents.items()
                if aid != agent_id and a.get("agent_type")
            ]
            if available_list:
                turn_message += (
                    f"\n\n[You can hand off to these agents if needed: {', '.join(available_list)}. "
                    f"Use the handoff_to_agent function if another agent is better suited.]"
                )

        try:
            result = await execute_agent_run(
                db=db,
                agent_id=agent_id,
                input_payload={
                    "message": turn_message,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                },
                trigger_source="swarm",
            )
            output = result.get("reply", "")
            tokens = result.get("token_usage", 0)
            cost = result.get("cost_usd", 0.0)
            latency = result.get("latency_ms", 0)
            status = result.get("status", "success")
        except Exception as e:
            logger.error(f"Swarm agent turn {agent_id} failed: {e}")
            return AgentTurn(
                agent_id=agent_id,
                agent_name=agent_info.get("name", agent_id),
                agent_type=agent_info.get("agent_type", "unknown"),
                output=f"Error: {str(e)}",
                status="failed",
            )

        handoff_target = await self._detect_handoff(output, agents)

        return AgentTurn(
            agent_id=agent_id,
            agent_name=agent_info.get("name", agent_id),
            agent_type=agent_info.get("agent_type", "unknown"),
            output=output,
            tokens_used=tokens,
            cost_usd=cost,
            latency_ms=latency,
            status=status,
            handoff_target=handoff_target,
        )

    async def _detect_handoff(
        self,
        output: str,
        agents: dict[str, dict],
    ) -> Optional[str]:

        if "handoff_to_agent" not in output and "handoff_to_specialist" not in output:
            if "HANDOFF:" in output.upper():
                lines = output.split("\n")
                for line in lines:
                    if "HANDOFF:" in line.upper():
                        for agent_id, agent_info in agents.items():
                            agent_type = agent_info.get("agent_type", "").upper()
                            agent_name = agent_info.get("name", "").upper()
                            if agent_type and agent_type in line.upper():
                                return agent_id
                            if agent_name and agent_name in line.upper():
                                return agent_id
            return None

        try:
            if "handoff_to_specialist" in output:
                import re
                match = re.search(r'to_agent_type\s*[=:]\s*["\'](\w+)["\']', output)
                if match:
                    target_type = match.group(1).upper()
                else:
                    match = re.search(r'handoff_to_specialist\s*\(\s*["\'](\w+)["\']', output)
                    target_type = match.group(1).upper() if match else None
            else:
                match = re.search(r'target_agent_type["\']?\s*:\s*["\'](\w+)["\']', output)
                target_type = match.group(1).upper() if match else None
        except Exception:
            return None

        if target_type:
            for agent_id, agent_info in agents.items():
                if agent_info.get("agent_type", "").upper() == target_type:
                    return agent_id

        return None


async def execute_swarm_run(
    task: str,
    starting_agent_id: str,
    max_handoffs: int,
    agent_ids: Optional[list[str]],
    db: AsyncSession,
    user_id: str = "",
    tenant_id: str = "default",
    progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None,
) -> SwarmResult:
    orchestrator = SwarmOrchestrator(max_handoffs=max_handoffs)

    if agent_ids:
        agents = await _resolve_agents_by_ids(agent_ids, db)
    else:
        agents = await _discover_active_agents(db)

    agents_map = {a["id"]: a for a in agents}

    if starting_agent_id not in agents_map:
        if agents:
            starting_agent_id = agents[0]["id"]
        else:
            raise ValueError("No active agents available")

    return await orchestrator.run(
        task=task,
        starting_agent_id=starting_agent_id,
        agents=agents_map,
        db=db,
        user_id=user_id,
        tenant_id=tenant_id,
        progress_callback=progress_callback,
    )


async def _resolve_agents_by_ids(agent_ids: list[str], db: AsyncSession) -> list[dict]:
    results = []
    for agent_id in agent_ids:
        res = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.is_active == True))
        agent = res.scalar_one_or_none()
        if agent:
            results.append(_agent_summary(agent))
    return results


async def _discover_active_agents(db: AsyncSession) -> list[dict]:
    res = await db.execute(
        select(Agent).where(Agent.is_active == True).order_by(Agent.name)
    )
    agents = res.scalars().all()
    return [_agent_summary(a) for a in agents]


def _agent_summary(a: Agent) -> dict:
    settings = a.agent_settings or {}
    return {
        "id": a.id,
        "name": a.name,
        "agent_type": a.agent_type.upper() if a.agent_type else "CONVERSATIONAL",
        "short_description": settings.get("short_description", ""),
        "is_active": a.is_active,
    }
