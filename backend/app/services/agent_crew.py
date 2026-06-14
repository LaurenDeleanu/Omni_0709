import time
import json
import logging
import asyncio
import uuid
from typing import Any, Optional, Callable, Awaitable
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentOrchestrationRun
from app.services.agent_runtime import execute_agent_run
from app.services.llm_router import get_llm_client

logger = logging.getLogger("successcore.agent_crew")


class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    description: str
    assigned_agent_type: str = ""
    depends_on: list[str] = Field(default_factory=list)
    priority: int = 1
    assigned_agent_id: str = ""


class SubTaskResult(BaseModel):
    subtask_id: str
    agent_id: str
    output: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    status: str = "success"


class CrewExecutionResult(BaseModel):
    orchestration_id: str
    subtask_results: list[SubTaskResult]
    final_output: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0


class CrewOrchestrator:

    def __init__(self, max_parallel: int = 3, worker_timeout: int = 120):
        self.max_parallel = max_parallel
        self.worker_timeout = worker_timeout

    async def decompose(
        self,
        task: str,
        available_agents: list[dict],
        db: AsyncSession,
    ) -> list[SubTask]:

        agent_registry_text = "\n".join(
            f"- {a['name']} (type: {a['agent_type']}): {a.get('description', a.get('short_description', ''))}"
            for a in available_agents
        )

        decompose_prompt = f"""You are a task decomposition engine. Break the following complex task into subtasks that specialized agents can execute.

AVAILABLE AGENTS:
{agent_registry_text}

USER TASK:
{task}

Return a JSON array of subtasks. Each subtask must have:
- "description": a clear, self-contained instruction for the agent
- "assigned_agent_type": the agent type that should handle this subtask (use one from AVAILABLE AGENTS)
- "depends_on": list of subtask indices (0-based) that must complete before this one
- "priority": 1 (high) to 3 (low)

Rules:
- Create the minimum number of subtasks needed (prefer 1-5)
- Only create subtasks that match available agent types
- Mark dependencies where one subtask's output is needed by another
- Be specific in descriptions so agents can execute without ambiguity
- Return ONLY valid JSON array, no other text

Subtasks:"""

        try:
            client, model = await get_llm_client("gpt-4o-mini", None, db)
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": decompose_prompt}],
                temperature=0.2,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or "[]"
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            raw_tasks = json.loads(content)
        except Exception as e:
            logger.warning(f"LLM decomposition failed, using fallback single-subtask: {e}")
            raw_tasks = [{
                "description": task,
                "assigned_agent_type": available_agents[0]["agent_type"] if available_agents else "conversational",
                "depends_on": [],
                "priority": 1,
            }]

        subtasks = []
        for i, raw in enumerate(raw_tasks):
            agent_type = raw.get("assigned_agent_type", "").upper()
            matching = [a for a in available_agents if a["agent_type"].upper() == agent_type]
            agent_id = matching[0]["id"] if matching else ""
            if not agent_id and available_agents:
                agent_id = available_agents[0]["id"]
                agent_type = available_agents[0]["agent_type"]

            dependencies = []
            for dep_idx in raw.get("depends_on", []):
                if isinstance(dep_idx, int) and 0 <= dep_idx < i:
                    dependencies.append(subtasks[dep_idx].id)

            subtasks.append(SubTask(
                id=uuid.uuid4().hex,
                description=raw.get("description", task),
                assigned_agent_type=agent_type,
                depends_on=dependencies,
                priority=raw.get("priority", 1),
                assigned_agent_id=agent_id,
            ))

        return subtasks

    async def execute(
        self,
        subtasks: list[SubTask],
        agents: dict[str, dict],
        db: AsyncSession,
        user_id: str = "",
        tenant_id: str = "default",
        progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None,
    ) -> dict:
        start_time = time.monotonic()

        orchestration_id = uuid.uuid4().hex
        run_log = AgentOrchestrationRun(
            id=orchestration_id,
            mode="crew",
            agent_ids=json.dumps([st.assigned_agent_id for st in subtasks]),
            input_message=json.dumps([st.description for st in subtasks]),
            status="running",
        )
        db.add(run_log)
        await db.flush()

        completed: dict[str, SubTaskResult] = {}
        pending = {st.id: st for st in subtasks}
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_one(st: SubTask) -> SubTaskResult:
            async with semaphore:
                if progress_callback:
                    await progress_callback("subtask_start", {
                        "subtask_id": st.id,
                        "description": st.description,
                        "agent_id": st.assigned_agent_id,
                    })

                try:
                    previous_outputs = "\n".join(
                        f"[{rid}]: {completed[rid].output[:500]}"
                        for rid in st.depends_on if rid in completed
                    )
                    message = st.description
                    if previous_outputs:
                        message = f"Context from previous subtasks:\n{previous_outputs}\n\nYour task:\n{st.description}"

                    result = await asyncio.wait_for(
                        execute_agent_run(
                            db=db,
                            agent_id=st.assigned_agent_id,
                            input_payload={
                                "message": message,
                                "user_id": user_id,
                                "tenant_id": tenant_id,
                            },
                            trigger_source="crew",
                        ),
                        timeout=self.worker_timeout,
                    )

                    sr = SubTaskResult(
                        subtask_id=st.id,
                        agent_id=st.assigned_agent_id,
                        output=result.get("reply", ""),
                        tokens_used=result.get("token_usage", 0),
                        cost_usd=result.get("cost_usd", 0.0),
                        latency_ms=result.get("latency_ms", 0),
                        status="success" if result.get("status") == "success" else "failed",
                    )
                except asyncio.TimeoutError:
                    sr = SubTaskResult(
                        subtask_id=st.id,
                        agent_id=st.assigned_agent_id,
                        output="Subtask timed out.",
                        status="timeout",
                    )
                except Exception as e:
                    logger.error(f"Subtask {st.id} failed: {e}")
                    sr = SubTaskResult(
                        subtask_id=st.id,
                        agent_id=st.assigned_agent_id,
                        output=f"Error: {str(e)}",
                        status="failed",
                    )

                if progress_callback:
                    await progress_callback("subtask_complete", sr.model_dump())

                return sr

        def ready(st: SubTask) -> bool:
            return all(dep in completed for dep in st.depends_on)

        while pending:
            ready_tasks = [st for st in pending.values() if ready(st)]
            if not ready_tasks:
                logger.error(f"Deadlock detected in crew orchestration {orchestration_id}: remaining tasks have unmet dependencies")
                for st in list(pending.values()):
                    completed[st.id] = SubTaskResult(
                        subtask_id=st.id,
                        agent_id=st.assigned_agent_id,
                        output="Deadlock: dependency not met.",
                        status="failed",
                    )
                    del pending[st.id]
                break

            results = await asyncio.gather(*[execute_one(st) for st in ready_tasks])
            for st, sr in zip(ready_tasks, results):
                completed[st.id] = sr
                del pending[st.id]

        total_latency = int((time.monotonic() - start_time) * 1000)
        all_results = list(completed.values())
        total_tokens = sum(r.tokens_used for r in all_results)
        total_cost = sum(r.cost_usd for r in all_results)

        run_log.status = "success" if all(r.status == "success" for r in all_results) else "partial"
        run_log.execution_trace = json.dumps([r.model_dump() for r in all_results])
        run_log.token_usage = total_tokens
        run_log.total_cost_usd = total_cost
        run_log.total_latency_ms = total_latency
        await db.commit()

        return {
            "orchestration_id": orchestration_id,
            "subtask_results": [r.model_dump() for r in all_results],
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "total_latency_ms": total_latency,
        }

    async def synthesize(
        self,
        subtask_results: list[SubTaskResult],
        original_task: str,
        db: AsyncSession,
    ) -> str:

        results_text = "\n\n---\n\n".join(
            f"Agent [{r.agent_id}] result (status: {r.status}):\n{r.output[:2000]}"
            for r in subtask_results
        )

        synthesize_prompt = f"""You are a task synthesis engine. Combine the following agent outputs into a single, coherent final response for the user.

ORIGINAL TASK: {original_task}

AGENT OUTPUTS:
{results_text}

Synthesize these results into a clear, well-structured response. Address the original task completely. If any agent failed or timed out, note that clearly. Do NOT mention internal orchestration details — present the answer as if a single assistant produced it."""

        try:
            client, model = await get_llm_client("gpt-4o-mini", None, db)
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": synthesize_prompt}],
                temperature=0.3,
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return "\n\n".join(r.output for r in subtask_results if r.status == "success")


async def execute_crew_task(
    task: str,
    agent_ids: Optional[list[str]],
    max_parallel: int,
    worker_timeout: int,
    db: AsyncSession,
    user_id: str = "",
    tenant_id: str = "default",
    progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None,
) -> CrewExecutionResult:
    orchestrator = CrewOrchestrator(max_parallel=max_parallel, worker_timeout=worker_timeout)

    if agent_ids:
        agents = await _resolve_agents_by_ids(agent_ids, db)
    else:
        agents = await _discover_active_agents(db)

    available = [
        {
            "id": a["id"],
            "name": a["name"],
            "agent_type": a["agent_type"],
            "description": a.get("description", a.get("short_description", "")),
        }
        for a in agents
    ]

    subtasks = await orchestrator.decompose(task, available, db)

    agents_map = {a["id"]: a for a in agents}

    exec_result = await orchestrator.execute(
        subtasks=subtasks,
        agents=agents_map,
        db=db,
        user_id=user_id,
        tenant_id=tenant_id,
        progress_callback=progress_callback,
    )

    subtask_results = [
        SubTaskResult(**r) for r in exec_result["subtask_results"]
    ]

    final_output = await orchestrator.synthesize(subtask_results, task, db)

    return CrewExecutionResult(
        orchestration_id=exec_result["orchestration_id"],
        subtask_results=subtask_results,
        final_output=final_output,
        total_tokens=exec_result["total_tokens"],
        total_cost_usd=exec_result["total_cost_usd"],
        total_latency_ms=exec_result["total_latency_ms"],
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
        "description": settings.get("short_description", ""),
        "is_active": a.is_active,
    }
