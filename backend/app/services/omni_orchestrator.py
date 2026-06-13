import json
import time
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.llm_router import get_llm_client
from app.services.prompt_composer import PromptComponentLibrary
from app.services.agent_runtime import execute_agent_run
from app.services.shared_context_bus import subscribe_context, publish_context, find_reusable_context

logger = logging.getLogger(__name__)

AGENT_TYPES = [
    "HR_ASSISTANT",
    "PAYROLL_SPECIALIST",
    "IT_HELPDESK",
    "RECRUITER",
    "SALES_COACH",
    "PERFORMANCE_COACH",
    "ONBOARDING_BUDDY",
    "COMPLIANCE_OFFICER",
    "DATA_ANALYST",
    "FINANCE_MANAGER",
]


AVAILABLE_TOOLS_NAMES = [
    "search_employees_advanced", "get_employee_profile_full", "get_org_chart", "get_span_of_control",
    "get_department_members", "get_pto_balance", "get_team_calendar", "get_recent_hires",
    "get_kudos_received", "get_company_announcements", "get_upcoming_vacations",
    "get_department_stats", "get_employee_attendance", "get_employee_documents",
    "get_review_feedback", "generate_career_path", "create_payroll_cycle", "process_payroll", 
    "get_payslip", "get_tax_rules", "update_compensation", "create_bonus", "get_financial_ledger",
    "get_expense_summary", "get_expense_summary_agg", "get_time_logs", "create_it_ticket", "assign_it_ticket", 
    "resolve_it_ticket", "get_it_assets", "search_it_knowledge_base", "suggest_it_solution", 
    "auto_tag_it_ticket", "get_ticket_stats", "search_employees", "create_job_posting", "add_candidate", 
    "move_candidate_stage", "schedule_interview", "get_job_applications", "get_pipeline_stats", 
    "promote_to_employee", "parse_resume", "screen_resume", "create_client", "get_client_details", 
    "search_clients", "get_pipeline_overview", "get_deal_stats", "create_task_for_lead", 
    "log_lead_activity", "create_task", "create_okr", "update_key_result", "create_review", "get_team_okrs", 
    "generate_onboarding_plan", "assign_onboarding_buddy", "create_employee", "enroll_in_course", 
    "create_project_task", "get_course_catalog", "validate_fundae", "get_compliance_status", 
    "get_contracts", "submit_whistleblower", "get_kudos_leaderboard"
]


@dataclass
class SubTask:
    id: str
    agent_type: str
    description: str
    tools_needed: list[str]
    depends_on: list[str]
    priority: int
    estimated_duration_seconds: int


@dataclass
class TaskPlan:
    original_request: str
    sub_tasks: list[SubTask]
    execution_order: list[list[str]]
    total_estimated_duration: int


@dataclass
class SubAgentResult:
    sub_task_id: str
    agent_type: str
    result: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    status: str
    error: Optional[str] = None


@dataclass
class OmniOrchestrationResult:
    final_answer: str
    sub_results: list[SubAgentResult]
    total_tokens_used: int
    total_cost_usd: float
    total_latency_ms: int
    orchestration_trace: dict
    status: str


DECOMPOSITION_PROMPT = """You are an orchestration engine. Given a complex user request, decompose it into independent sub-tasks that can be executed by specialized agents.

For each sub-task, identify:
- The agent type needed (choose from the available types below)
- A clear task description
- Required tools (from available platform tools below — only include tools actually needed)
- Dependencies on other sub-tasks (list of sub-task IDs this depends on)
- A priority score (1-10, where 10 is highest)

Available agent types:
{agent_types}

Available tools:
{tools}

Few-Shot Examples:

Example 1: "Show me Alice's vacation balance and IT asset inventory."
Response:
{{
  "sub_tasks": [
    {{
      "id": "task_1",
      "agent_type": "HR_ASSISTANT",
      "description": "Retrieve PTO balance for employee Alice",
      "tools_needed": ["tool_get_pto_balance"],
      "depends_on": [],
      "priority": 8,
      "estimated_duration_seconds": 15
    }},
    {{
      "id": "task_2",
      "agent_type": "IT_HELPDESK",
      "description": "Retrieve IT assets assigned to Alice",
      "tools_needed": ["tool_get_it_assets"],
      "depends_on": [],
      "priority": 8,
      "estimated_duration_seconds": 15
    }}
  ]
}}

Example 2: "Process payroll for the HR department members and get payslips."
Response:
{{
  "sub_tasks": [
    {{
      "id": "task_1",
      "agent_type": "HR_ASSISTANT",
      "description": "List all members of the HR department",
      "tools_needed": ["tool_get_department_members"],
      "depends_on": [],
      "priority": 9,
      "estimated_duration_seconds": 20
    }},
    {{
      "id": "task_2",
      "agent_type": "PAYROLL_SPECIALIST",
      "description": "Process payroll and generate payslips for the HR department members retrieved in task_1",
      "tools_needed": ["tool_process_payroll", "tool_get_payslip"],
      "depends_on": ["task_1"],
      "priority": 9,
      "estimated_duration_seconds": 40
    }}
  ]
}}

Example 3: "Review expense summary for last month and update marketing department's OKR."
Response:
{{
  "sub_tasks": [
    {{
      "id": "task_1",
      "agent_type": "FINANCE_MANAGER",
      "description": "Retrieve expense summary for last month",
      "tools_needed": ["tool_get_expense_summary"],
      "depends_on": [],
      "priority": 8,
      "estimated_duration_seconds": 25
    }},
    {{
      "id": "task_2",
      "agent_type": "PERFORMANCE_COACH",
      "description": "Update marketing department's OKR / key results based on last month's expenses",
      "tools_needed": ["tool_update_key_result"],
      "depends_on": ["task_1"],
      "priority": 7,
      "estimated_duration_seconds": 30
    }}
  ]
}}

Example 4: "I need to screen candidate John Doe for the software engineer position and schedule an interview."
Response:
{{
  "sub_tasks": [
    {{
      "id": "task_1",
      "agent_type": "RECRUITER",
      "description": "Screen candidate John Doe for software engineer position",
      "tools_needed": ["tool_add_candidate"],
      "depends_on": [],
      "priority": 8,
      "estimated_duration_seconds": 20
    }},
    {{
      "id": "task_2",
      "agent_type": "RECRUITER",
      "description": "Schedule interview for candidate John Doe",
      "tools_needed": ["tool_schedule_interview"],
      "depends_on": ["task_1"],
      "priority": 8,
      "estimated_duration_seconds": 20
    }}
  ]
}}

Example 5: "Who are the new hires this month and have they been assigned buddies?"
Response:
{{
  "sub_tasks": [
    {{
      "id": "task_1",
      "agent_type": "HR_ASSISTANT",
      "description": "List recent hires in the last 30 days",
      "tools_needed": ["tool_get_recent_hires"],
      "depends_on": [],
      "priority": 8,
      "estimated_duration_seconds": 15
    }},
    {{
      "id": "task_2",
      "agent_type": "ONBOARDING_BUDDY",
      "description": "Check and assign onboarding buddies to the new hires found in task_1",
      "tools_needed": ["assign_onboarding_buddy"],
      "depends_on": ["task_1"],
      "priority": 7,
      "estimated_duration_seconds": 25
    }}
  ]
}}

Return a JSON TaskPlan with this exact structure:
{{
  "sub_tasks": [
    {{
      "id": "task_1",
      "agent_type": "HR_ASSISTANT",
      "description": "Task description here",
      "tools_needed": ["tool_name_1", "tool_name_2"],
      "depends_on": [],
      "priority": 8,
      "estimated_duration_seconds": 30
    }}
  ]
}}

Rules:
1. Each sub-task must have unique ID (task_1, task_2, etc.)
2. Dependencies must reference valid sub-task IDs
3. Maximum 5 sub-tasks total
4. Minimize dependencies — prefer parallel execution
5. Agent type MUST be one of the available types listed above
6. Tools names MUST be from the available tools list above
7. Tools should be scoped to only what the sub-task actually needs
8. If the request is simple and can be handled by a single agent, return ONE sub-task"""


SYNTHESIS_PROMPT = """Here are the results from {num_agents} specialized sub-agents, each handling a part of the user's original request.

Original user request: {original_request}

Sub-agent results:
{sub_results}

Synthesize these into a coherent, comprehensive response that directly answers the user's original question. 
Integrate all findings seamlessly — do not simply list each sub-agent's response.
Maintain professional HR tone. Use markdown formatting for clarity where appropriate.

Synthesized response:"""


NEGOTIATION_MODE = "negotiation"


class OmniOrchestrator:

    def __init__(self, db: AsyncSession, omni_agent: Agent, user_message: str, user_id: str, mode: str = "hierarchical"):
        self.db = db
        self.omni_agent = omni_agent
        self.user_message = user_message
        self.user_id = user_id
        self.mode = mode
        self.dag: Dict[str, list[str]] = {}
        self.spawned_agent_ids: list[str] = []
        self.start_time = 0.0

    async def run_orchestration(self, max_sub_agents: int = 5) -> OmniOrchestrationResult:
        from app.services.telemetry import tracer, OTEL_AVAILABLE
        from opentelemetry import trace as otel_trace
        
        telemetry_span = None
        telemetry_token = None
        if OTEL_AVAILABLE and tracer:
            try:
                telemetry_span = tracer.start_span("run_orchestration", attributes={
                    "agent.id": self.omni_agent.id,
                    "mode": self.mode
                })
                context = otel_trace.set_span_in_context(telemetry_span)
                telemetry_token = otel_trace.attach(context)
            except Exception as otel_err:
                logger.warning(f"Failed to start telemetry span: {otel_err}")

        try:
            result = await self._run_orchestration_inner(max_sub_agents)
            if telemetry_span and hasattr(result, "status"):
                telemetry_span.set_attribute("status", result.status)
                telemetry_span.set_status(otel_trace.StatusCode.OK)
            return result
        except Exception as e:
            if telemetry_span:
                telemetry_span.record_exception(e)
                telemetry_span.set_status(otel_trace.StatusCode.ERROR, str(e))
            raise
        finally:
            if telemetry_token:
                otel_trace.detach(telemetry_token)
            if telemetry_span:
                telemetry_span.end()

    async def _run_orchestration_inner(self, max_sub_agents: int = 5) -> OmniOrchestrationResult:
        self.start_time = time.monotonic()
        orchestration_trace = {"steps": []}

        if self.mode == NEGOTIATION_MODE:
            return await self._run_negotiation_mode(orchestration_trace)

        task_plan = await self._decompose_task()
        orchestration_trace["steps"].append({
            "step": "decompose",
            "sub_tasks": len(task_plan.sub_tasks),
            "execution_order": task_plan.execution_order,
        })

        if len(task_plan.sub_tasks) == 1:
            agent_type = task_plan.sub_tasks[0].agent_type
            agent_res = await self.db.execute(
                select(Agent).where(
                    Agent.agent_type == agent_type.upper(),
                    Agent.is_active == True,
                )
            )
            agent = agent_res.scalars().first()
            if not agent:
                agent_res = await self.db.execute(select(Agent).where(Agent.agent_type == agent_type.upper()))
                agent = agent_res.scalar_one_or_none()

            if agent:
                logger.info(f"Smart single-agent routing to: {agent.name} (type={agent_type})")
                step_start = time.monotonic()
                input_payload = {
                    "message": task_plan.sub_tasks[0].description,
                    "user_id": self.user_id,
                }
                run_result = await execute_agent_run(
                    db=self.db,
                    agent_id=agent.id,
                    input_payload=input_payload,
                    trigger_source="orchestration_direct",
                )
                latency = int((time.monotonic() - step_start) * 1000)
                reply = run_result.get("reply", "")

                try:
                    run_res = await self.db.execute(
                        select(AgentExecutionRun)
                        .where(AgentExecutionRun.agent_id == agent.id)
                        .order_by(AgentExecutionRun.created_at.desc())
                        .limit(1)
                    )
                    run_log = run_res.scalar_one_or_none()
                    tokens = run_log.token_usage if run_log else 0
                    cost = run_log.cost_usd if run_log else 0.0
                except Exception:
                    tokens = 500
                    cost = 0.001

                sub_result = SubAgentResult(
                    sub_task_id=task_plan.sub_tasks[0].id,
                    agent_type=task_plan.sub_tasks[0].agent_type,
                    result=reply,
                    tokens_used=tokens,
                    cost_usd=cost,
                    latency_ms=latency,
                    status="completed",
                )

                orchestration_trace["steps"].append({
                    "step": "single_agent_direct_route",
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                })

                await self._record_orchestration_run(task_plan, {task_plan.sub_tasks[0].id: sub_result}, orchestration_trace)

                return OmniOrchestrationResult(
                    final_answer=reply,
                    sub_results=[sub_result],
                    total_tokens_used=tokens,
                    total_cost_usd=cost,
                    total_latency_ms=latency,
                    orchestration_trace=orchestration_trace,
                    status="completed",
                )

        sub_agents = await self._spawn_sub_agents(task_plan.sub_tasks, max_sub_agents)
        orchestration_trace["steps"].append({
            "step": "spawn",
            "agents_created": len(sub_agents),
            "agent_ids": [sa["agent"].id for sa in sub_agents],
        })

        results = await self._execute_parallel(sub_agents, task_plan)
        orchestration_trace["steps"].append({
            "step": "execute",
            "completed": sum(1 for r in results.values() if r.status == "completed"),
            "failed": sum(1 for r in results.values() if r.status == "failed"),
        })

        final_answer = await self._synthesize_results(results, task_plan)
        orchestration_trace["steps"].append({"step": "synthesize"})

        await self._record_orchestration_run(task_plan, results, orchestration_trace)

        sub_results = list(results.values())
        total_tokens = sum(r.tokens_used for r in sub_results)
        total_cost = sum(r.cost_usd for r in sub_results)
        total_latency = int((time.monotonic() - self.start_time) * 1000)
        all_completed = all(r.status == "completed" for r in sub_results)
        any_completed = any(r.status == "completed" for r in sub_results)

        if all_completed:
            status = "completed"
        elif any_completed:
            status = "partial_failure"
        else:
            status = "failed"

        await self._cleanup_spawned_agents()

        return OmniOrchestrationResult(
            final_answer=final_answer,
            sub_results=sub_results,
            total_tokens_used=total_tokens,
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
            orchestration_trace=orchestration_trace,
            status=status,
        )

    async def _decompose_task(self) -> TaskPlan:
        agent_types_str = "\n".join(f"- {t}" for t in AGENT_TYPES)
        
        # Tool-aware decomposition: extract tool descriptions from AVAILABLE_TOOLS_SCHEMA
        from app.services.tool_executor import AVAILABLE_TOOLS_SCHEMA
        tool_descriptions = []
        for t in AVAILABLE_TOOLS_SCHEMA:
            name = t.get("function", {}).get("name")
            desc = t.get("function", {}).get("description", "")
            if name in AVAILABLE_TOOLS_NAMES:
                tool_descriptions.append(f"- {name}: {desc}")
        tools_str = "\n".join(tool_descriptions)

        prompt = DECOMPOSITION_PROMPT.format(
            agent_types=agent_types_str,
            tools=tools_str,
        )

        try:
            client, _ = await get_llm_client(self.omni_agent.ai_model, self.omni_agent, self.db)
            response = await client.chat.completions.create(
                model=self.omni_agent.ai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Decompose this user request into sub-tasks:\n\n{self.user_message}"},
                ],
            )

            raw = response.choices[0].message.content or "{}"
            raw = raw.strip()

            data = self._parse_json(raw)
            sub_tasks_raw = data.get("sub_tasks", [])

            if not sub_tasks_raw or not isinstance(sub_tasks_raw, list):
                sub_tasks_raw = [{
                    "id": "task_1",
                    "agent_type": "HR_ASSISTANT",
                    "description": self.user_message,
                    "tools_needed": [],
                    "depends_on": [],
                    "priority": 10,
                    "estimated_duration_seconds": 30,
                }]

            sub_tasks: list[SubTask] = []
            for st in sub_tasks_raw:
                agent_type = str(st.get("agent_type", "HR_ASSISTANT")).upper()
                if agent_type not in AGENT_TYPES:
                    found = False
                    for possible_type in AGENT_TYPES:
                        if possible_type.upper() == agent_type:
                            agent_type = possible_type
                            found = True
                            break
                    if not found:
                        agent_type = "HR_ASSISTANT"

                tools = st.get("tools_needed", [])
                if not isinstance(tools, list):
                    tools = []
                tools = [t for t in tools if t in AVAILABLE_TOOLS_NAMES]

                depends = st.get("depends_on", [])
                if not isinstance(depends, list):
                    depends = []

                sub_tasks.append(SubTask(
                    id=str(st.get("id", f"task_{len(sub_tasks) + 1}")),
                    agent_type=agent_type,
                    description=str(st.get("description", "")),
                    tools_needed=tools,
                    depends_on=depends,
                    priority=int(st.get("priority", 5)),
                    estimated_duration_seconds=int(st.get("estimated_duration_seconds", 30)),
                ))

            execution_order = self._build_execution_order(sub_tasks)
            total_duration = sum(st.estimated_duration_seconds for st in sub_tasks)

            return TaskPlan(
                original_request=self.user_message,
                sub_tasks=sub_tasks,
                execution_order=execution_order,
                total_estimated_duration=total_duration,
            )

        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            fallback = SubTask(
                id="task_1",
                agent_type="hr_assistant",
                description=self.user_message,
                tools_needed=[],
                depends_on=[],
                priority=10,
                estimated_duration_seconds=30,
            )
            return TaskPlan(
                original_request=self.user_message,
                sub_tasks=[fallback],
                execution_order=[["task_1"]],
                total_estimated_duration=30,
            )

    def _parse_json(self, raw: str) -> dict:
        for attempt in range(3):
            try:
                if attempt == 0:
                    clean = raw[raw.find("{"):raw.rfind("}") + 1]
                    return json.loads(clean)
                elif attempt == 1:
                    lines = raw.replace("\r\n", "\n").split("\n")
                    for line in reversed(lines):
                        line = line.strip()
                        if line.startswith("{") and line.endswith("}"):
                            try:
                                parsed = json.loads(line)
                                if "sub_tasks" in parsed:
                                    return parsed
                            except Exception:
                                continue
                else:
                    import re
                    matches = re.findall(r'\{[^{}]*\}', raw)
                    for m in reversed(matches):
                        try:
                            candidate = json.loads(m)
                            if "sub_tasks" in candidate:
                                return candidate
                        except Exception:
                            continue
            except Exception:
                continue
        return {}

    def _build_execution_order(self, sub_tasks: list[SubTask]) -> list[list[str]]:
        self.dag = {st.id: list(st.depends_on) for st in sub_tasks}
        task_ids = set(st.id for st in sub_tasks)

        in_degree: Dict[str, int] = {tid: 0 for tid in task_ids}
        for st in sub_tasks:
            for dep in st.depends_on:
                if dep in in_degree:
                    in_degree[st.id] += 1

        levels: list[list[str]] = []
        remaining = set(task_ids)
        while remaining:
            level = sorted(tid for tid in remaining if in_degree[tid] == 0)
            if not level:
                remaining_ids = list(remaining)
                levels.append(remaining_ids)
                break
            levels.append(level)
            for tid in level:
                remaining.remove(tid)
                for st in sub_tasks:
                    if tid in st.depends_on and st.id in in_degree:
                        in_degree[st.id] = max(0, in_degree[st.id] - 1)

        return levels

    async def _spawn_sub_agents(self, sub_tasks: list[SubTask], max_sub_agents: int) -> list[Dict[str, Any]]:
        spawned = []
        tasks_to_spawn = sub_tasks[:max_sub_agents]

        for st in tasks_to_spawn:
            try:
                agent_res = await self.db.execute(select(Agent).where(Agent.agent_type == st.agent_type.upper()))
                real_agent = agent_res.scalars().first()
                
                if real_agent:
                    ai_model = real_agent.ai_model
                    ai_temperature = real_agent.ai_temperature
                    ai_tone = real_agent.ai_tone
                    system_prompt = f"{real_agent.ai_system_prompt}\n\n[YOUR ORCHESTRATED TASK]\nYou are working as a sub-agent. Focus ONLY on this task: {st.description}"
                else:
                    ai_model = "meta-llama/llama-3.3-70b-instruct:free"
                    ai_temperature = 0.2
                    ai_tone = "Profesional"
                    system_prompt = self._compose_system_prompt(st.agent_type)

                agent_db_id = uuid.uuid4().hex

                agent = Agent(
                    id=agent_db_id,
                    name=f"OrchWorker-{st.agent_type}-{st.id}",
                    avatar="",
                    agent_type=st.agent_type.upper(),
                    ai_model=ai_model,
                    ai_system_prompt=system_prompt,
                    ai_temperature=ai_temperature,
                    ai_tone=ai_tone,
                    agent_settings={"ai_tools": json.dumps(st.tools_needed) if st.tools_needed else json.dumps([]), "ephemeral": True},
                )
                self.db.add(agent)
                await self.db.flush()

                config = AgentConfig(
                    id=uuid.uuid4().hex,
                    agent_id=agent_db_id,
                    max_loops=5,
                    max_tokens_per_run=100000,
                )
                self.db.add(config)
                await self.db.flush()
                self.spawned_agent_ids.append(agent_db_id)

                spawned.append({
                    "agent": agent,
                    "sub_task": st,
                })
                logger.info(f"Spawned sub-agent {agent_db_id} for task {st.id} ({st.agent_type})")
            except Exception as e:
                logger.error(f"Failed to spawn sub-agent for task {st.id}: {e}")

        await self.db.commit()
        return spawned

    def _compose_system_prompt(self, agent_type: str) -> str:
        try:
            role_prompt = PromptComponentLibrary.get_component("roles", agent_type)
        except KeyError:
            role_prompt = f"You are a {agent_type.replace('_', ' ')} for SuccessCore. Help users effectively and professionally."

        prompt = f"""{role_prompt}

You are working as a specialized sub-agent in an orchestrated workflow. 
Focus ONLY on your assigned task. Do not try to handle unrelated topics.
Respond concisely and accurately. Use the tools provided to you as needed.

IMPORTANT: Your response will be synthesized with other sub-agent responses by the orchestrator.
Provide clear, structured information that can be easily integrated into a comprehensive answer.

HANDOFF: If you cannot handle a request because it falls outside your domain, use the handoff_to_specialist tool to transfer the conversation to the appropriate specialist: Payroll Specialist for payroll, Recruiter Pro for hiring, IT Helpdesk for IT support, Sales Coach for CRM, Performance Coach for OKRs/reviews, Onboarding Buddy for onboarding, Compliance Officer for compliance, Data Analyst for analytics, Finance Manager for finance."""

        return prompt

    async def _execute_parallel(
        self,
        sub_agents: list[Dict[str, Any]],
        task_plan: TaskPlan,
    ) -> Dict[str, SubAgentResult]:
        results: Dict[str, SubAgentResult] = {}
        completed_events = {st.id: asyncio.Event() for st in task_plan.sub_tasks}
        semaphore = asyncio.Semaphore(5)  # Enforce max 5 parallel subagents limit

        agent_map: Dict[str, Dict[str, Any]] = {}
        for sa in sub_agents:
            agent_map[sa["sub_task"].id] = sa

        async def execute_task_with_deps(st: SubTask):
            # Wait for all parent dependencies to finish
            if st.depends_on:
                logger.info(f"Subtask {st.id} waiting for dependencies: {st.depends_on}")
                await asyncio.gather(
                    *[completed_events[parent_id].wait() for parent_id in st.depends_on if parent_id in completed_events]
                )
                # Check if any parent failed or was skipped
                for parent_id in st.depends_on:
                    parent_res = results.get(parent_id)
                    if not parent_res or parent_res.status != "completed":
                        logger.warning(f"Skipping subtask {st.id} because dependency {parent_id} failed or was skipped")
                        results[st.id] = SubAgentResult(
                            sub_task_id=st.id,
                            agent_type=st.agent_type,
                            result="Skipped: parent dependency failed",
                            tokens_used=0,
                            cost_usd=0.0,
                            latency_ms=0,
                            status="failed",
                            error=f"Dependency {parent_id} failed",
                        )
                        completed_events[st.id].set()
                        return

            # Acquire semaphore slot to limit concurrency
            async with semaphore:
                logger.info(f"Subtask {st.id} ({st.agent_type}) acquired slot and starting execution")
                agent_info = agent_map.get(st.id)
                if agent_info:
                    try:
                        parent_results = {}
                        for parent_id in st.depends_on:
                            if parent_id in results and results[parent_id].status == "completed":
                                parent_results[parent_id] = results[parent_id].result
                        res = await self._execute_single_agent(agent_info["agent"], st, parent_results=parent_results)
                        results[st.id] = res
                    except Exception as e:
                        logger.error(f"Sub-agent for task {st.id} failed: {e}")
                        results[st.id] = SubAgentResult(
                            sub_task_id=st.id,
                            agent_type=st.agent_type,
                            result="",
                            tokens_used=0,
                            cost_usd=0.0,
                            latency_ms=0,
                            status="failed",
                            error=str(e),
                        )
                else:
                    results[st.id] = SubAgentResult(
                        sub_task_id=st.id,
                        agent_type=st.agent_type,
                        result="No agent spawned",
                        tokens_used=0,
                        cost_usd=0.0,
                        latency_ms=0,
                        status="failed",
                        error="No agent spawned",
                    )
                completed_events[st.id].set()

        # Execute all tasks concurrently respecting the DAG structure
        await asyncio.gather(*[execute_task_with_deps(st) for st in task_plan.sub_tasks])

        # Fill in any missing results
        for st in task_plan.sub_tasks:
            if st.id not in results:
                results[st.id] = SubAgentResult(
                    sub_task_id=st.id,
                    agent_type=st.agent_type,
                    result="Task was not executed",
                    tokens_used=0,
                    cost_usd=0.0,
                    latency_ms=0,
                    status="failed",
                    error="Not executed due to scheduling omission",
                )

        return results

    async def _execute_single_agent(
        self,
        agent: Agent,
        sub_task: SubTask,
        parent_results: Optional[Dict[str, str]] = None,
    ) -> SubAgentResult:
        step_start = time.monotonic()

        relevant_topics = [sub_task.agent_type, sub_task.id]
        for tool_name in sub_task.tools_needed[:3]:
            relevant_topics.append(f"tool:{tool_name}")

        try:
            shared_ctx = await subscribe_context(
                orchestration_id=self.omni_agent.id,
                agent_id=agent.id,
                topics=relevant_topics,
                db=self.db,
            )
            pre_existing_data = shared_ctx.get("aggregated", {})
            if pre_existing_data:
                logger.debug(f"Sub-agent {sub_task.id} found {shared_ctx['entry_count']} shared context entries")
        except Exception as e:
            logger.debug(f"Shared context lookup skipped for {sub_task.id}: {e}")
            pre_existing_data = {}

        try:
            context_note = ""
            if parent_results:
                context_note += "\n\n[RESULTS FROM DEPENDENT SUB-TASKS]"
                for dep_id, dep_res in parent_results.items():
                    context_note += f"\n- Sub-task {dep_id} Result: {dep_res}"

            if pre_existing_data:
                context_note += "\n\n[SHARED CONTEXT FROM OTHER AGENTS]\n"
                for topic, entries in pre_existing_data.items():
                    for entry in entries[:1]:
                        try:
                            context_note += f"{topic}: {json.dumps(entry.get('data', {}), default=str)[:500]}\n"
                        except Exception:
                            context_note += f"{topic}: {str(entry.get('data', ''))[:500]}\n"

            input_payload = {
                "message": sub_task.description + context_note,
                "user_id": self.user_id,
            }

            run_result = await execute_agent_run(
                db=self.db,
                agent_id=agent.id,
                input_payload=input_payload,
                trigger_source="orchestration",
            )

            latency = int((time.monotonic() - step_start) * 1000)
            reply = run_result.get("reply", "")
            if run_result.get("status") == "throttled":
                raise Exception("Agent throttled")

            try:
                run_res = await self.db.execute(
                    select(AgentExecutionRun)
                    .where(AgentExecutionRun.agent_id == agent.id)
                    .order_by(AgentExecutionRun.created_at.desc())
                    .limit(1)
                )
                run_log = run_res.scalar_one_or_none()
                tokens = run_log.token_usage if run_log else 0
                cost = run_log.cost_usd if run_log else 0.0
            except Exception:
                tokens = 500
                cost = 0.001

            try:
                await publish_context(
                    orchestration_id=self.omni_agent.id,
                    agent_id=agent.id,
                    topic=sub_task.agent_type,
                    data={
                        "task_id": sub_task.id,
                        "description": sub_task.description,
                        "result_summary": reply[:500] if reply else "(empty)",
                        "tokens_used": tokens,
                        "tools_used": sub_task.tools_needed,
                    },
                    db=self.db,
                )
            except Exception as e:
                logger.debug(f"Shared context publish failed for {sub_task.id}: {e}")

            return SubAgentResult(
                sub_task_id=sub_task.id,
                agent_type=sub_task.agent_type,
                result=reply,
                tokens_used=tokens,
                cost_usd=cost,
                latency_ms=latency,
                status="completed",
            )

        except Exception as e:
            latency = int((time.monotonic() - step_start) * 1000)
            logger.warning(f"Sub-agent {sub_task.id} failed, retrying once: {e}")

            try:
                await asyncio.sleep(0.5)
                retry_start = time.monotonic()

                input_payload = {
                    "message": f"RETRY: {sub_task.description}",
                    "user_id": self.user_id,
                }

                run_result = await execute_agent_run(
                    db=self.db,
                    agent_id=agent.id,
                    input_payload=input_payload,
                    trigger_source="orchestration_retry",
                )

                latency = int((time.monotonic() - step_start) * 1000)
                reply = run_result.get("reply", "")

                try:
                    run_res = await self.db.execute(
                        select(AgentExecutionRun)
                        .where(AgentExecutionRun.agent_id == agent.id)
                        .order_by(AgentExecutionRun.created_at.desc())
                        .limit(1)
                    )
                    run_log = run_res.scalar_one_or_none()
                    tokens = run_log.token_usage if run_log else 0
                    cost = run_log.cost_usd if run_log else 0.0
                except Exception:
                    tokens = 800
                    cost = 0.002

                return SubAgentResult(
                    sub_task_id=sub_task.id,
                    agent_type=sub_task.agent_type,
                    result=reply,
                    tokens_used=tokens,
                    cost_usd=cost,
                    latency_ms=latency,
                    status="completed",
                )
            except Exception as retry_err:
                return SubAgentResult(
                    sub_task_id=sub_task.id,
                    agent_type=sub_task.agent_type,
                    result="",
                    tokens_used=0,
                    cost_usd=0.0,
                    latency_ms=latency,
                    status="failed",
                    error=str(retry_err),
                )

    async def _synthesize_results(
        self,
        results: Dict[str, SubAgentResult],
        task_plan: TaskPlan,
    ) -> str:
        sub_results_text_parts = []
        sub_results_list = []
        for st in task_plan.sub_tasks:
            r = results.get(st.id)
            if r:
                status_label = "[COMPLETED]" if r.status == "completed" else f"[FAILED: {r.error}]" if r.error else "[FAILED]"
                sub_results_text_parts.append(
                    f"### Sub-task: {st.description}\n"
                    f"**Agent**: {st.agent_type} | **Status**: {r.status}\n\n"
                    f"{r.result or '(no result)'}\n"
                )
                sub_results_list.append({
                    "agent_type": st.agent_type,
                    "agent_id": st.id,
                    "result": r.result or "",
                    "status": r.status,
                })

        conflict_report = ""
        try:
            from app.services.conflict_resolver import ConflictResolver
            resolver = ConflictResolver()
            completed_results = [sr for sr in sub_results_list if sr.get("status") == "completed" and sr.get("result")]
            if len(completed_results) >= 2:
                conflicts = await resolver.detect_conflicts(completed_results)
                if conflicts:
                    logger.info(f"Detected {len(conflicts)} conflicts among sub-agent results")
                    resolution = await resolver.auto_resolve(conflicts, self.db)
                    resolution_report = await resolver.generate_resolution_report(
                        conflicts,
                        resolution.resolved + resolution.unresolved if resolution else [],
                        self.db,
                    )
                    conflict_report = (
                        f"\n\n[CONFLICT RESOLUTION REPORT]\n{resolution_report}\n\n"
                        f"Resolved: {len(resolution.resolved)}, Unresolved: {len(resolution.unresolved)}, "
                        f"Human review needed: {resolution.human_review_needed}\n"
                    )
                    if resolution.resolved:
                        conflict_report += "Resolved points:\n"
                        for rp in resolution.resolved:
                            conflict_report += (
                                f"- [{rp.get('method', 'unknown')}] {rp.get('type', 'conflict')}: "
                                f"{rp.get('resolution', 'No detail')[:200]}\n"
                            )
                    if resolution.unresolved:
                        conflict_report += "Unresolved points (escalated):\n"
                        for up in resolution.unresolved:
                            conflict_report += (
                                f"- [{up.get('method', 'escalated')}] {up.get('type', 'conflict')}: "
                                f"{up.get('description', 'No detail')[:200]}\n"
                            )
        except Exception as e:
            logger.debug(f"Conflict resolution in synthesis skipped: {e}")

        cross_agent_insights = ""
        try:
            shared_ctx = await subscribe_context(
                orchestration_id=self.omni_agent.id,
                agent_id=self.omni_agent.id,
                topics=[st.agent_type for st in task_plan.sub_tasks],
                db=self.db,
            )
            aggregated = shared_ctx.get("aggregated", {})
            if aggregated:
                cross_agent_insights = "\n[CROSS-AGENT SHARED CONTEXT]\n"
                for topic, entries in aggregated.items():
                    cross_agent_insights += f"\n**{topic}** discovered by other agents:\n"
                    for entry in entries:
                        try:
                            cross_agent_insights += f"- {json.dumps(entry.get('data', {}), default=str)[:300]}\n"
                        except Exception:
                            pass
                if len(aggregated) >= 2:
                    cross_agent_insights += "\nNOTE: Multiple agents found data relevant to the same topic — synthesize these findings together.\n"
        except Exception as e:
            logger.debug(f"Cross-agent context lookup failed during synthesis: {e}")

        sub_results_text = "\n---\n".join(sub_results_text_parts)
        prompt = SYNTHESIS_PROMPT.format(
            num_agents=len(task_plan.sub_tasks),
            original_request=task_plan.original_request,
            sub_results=sub_results_text + cross_agent_insights + conflict_report,
        )

        try:
            client, _ = await get_llm_client(self.omni_agent.ai_model, self.omni_agent, self.db)
            response = await client.chat.completions.create(
                model=self.omni_agent.ai_model,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or "Synthesis completed but no text was generated."
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return f"Orchestration synthesis failed: {str(e)}\n\nRaw sub-agent results:\n{sub_results_text}"

    async def _run_negotiation_mode(self, orchestration_trace: dict) -> OmniOrchestrationResult:
        from app.services.agent_negotiation import AgentNegotiationProtocol

        orchestration_trace["steps"].append({
            "step": "negotiation_init",
            "mode": "negotiation",
        })

        agent_configs = []
        for agent_type in AGENT_TYPES[:4]:
            agent_configs.append({
                "id": f"negotiator_{agent_type}",
                "role": agent_type.replace("_", " ").title(),
                "agent_type": agent_type,
            })

        protocol = AgentNegotiationProtocol()
        result = await protocol.negotiate(
            topic=self.user_message,
            agent_configs=agent_configs,
            user_id=self.user_id,
            db=self.db,
            max_rounds=5,
            timeout_seconds=120,
        )

        orchestration_trace["steps"].append({
            "step": "negotiation_complete",
            "consensus_reached": result.consensus_reached,
            "rounds_run": result.rounds_run,
            "deadlock_points": result.deadlock_points,
        })

        agreement_text = json.dumps(result.final_agreement, indent=2, default=str)
        preamble = result.final_agreement.get("preamble", "")
        agreed_points = result.final_agreement.get("agreed_points", [])
        unresolved = result.final_agreement.get("unresolved_items", [])

        final_answer_parts = []
        if result.consensus_reached:
            final_answer_parts.append(f"**Consensus reached** after {result.rounds_run} rounds of negotiation.")
        else:
            final_answer_parts.append(f"**No consensus reached** after {result.rounds_run} rounds.")
            if result.deadlock_points:
                final_answer_parts.append(f"Deadlock points: {', '.join(result.deadlock_points[:5])}")
            if result.suggested_mediator:
                final_answer_parts.append(f"Suggested mediator: {result.suggested_mediator}")

        if preamble:
            final_answer_parts.append(f"\n**Agreement Preamble**: {preamble}")

        if agreed_points:
            final_answer_parts.append("\n**Agreed Points**:")
            for pt in agreed_points:
                point_text = pt.get("point", str(pt))
                parties = pt.get("responsible_parties", [])
                timeline = pt.get("timeline", "")
                final_answer_parts.append(f"- {point_text}")
                if parties:
                    final_answer_parts.append(f"  Responsible: {', '.join(parties)}")
                if timeline:
                    final_answer_parts.append(f"  Timeline: {timeline}")

        if unresolved:
            final_answer_parts.append("\n**Unresolved Items**:")
            for item in unresolved:
                final_answer_parts.append(f"- {item}")

        next_steps = result.final_agreement.get("next_steps", [])
        if next_steps:
            final_answer_parts.append("\n**Next Steps**:")
            for step in next_steps:
                final_answer_parts.append(f"- {step}")

        final_answer = "\n".join(final_answer_parts)

        sub_results = []
        for round_data in result.agent_positions:
            r = round_data.get("round", 0)
            for pos in round_data.get("positions", []):
                sub_results.append(SubAgentResult(
                    sub_task_id=f"round_{r}_{pos.get('agent_role', 'unknown')}",
                    agent_type=pos.get("agent_role", "negotiator"),
                    result=json.dumps(pos, default=str),
                    tokens_used=result.total_tokens // max(len(round_data.get("positions", [])), 1),
                    cost_usd=result.total_cost_usd / max(len(round_data.get("positions", [])), 1),
                    latency_ms=0,
                    status="completed",
                ))

        await self._record_negotiation_run(result, orchestration_trace)

        return OmniOrchestrationResult(
            final_answer=final_answer,
            sub_results=sub_results,
            total_tokens_used=result.total_tokens,
            total_cost_usd=result.total_cost_usd,
            total_latency_ms=int((time.monotonic() - self.start_time) * 1000),
            orchestration_trace=orchestration_trace,
            status="completed" if result.consensus_reached else "partial_consensus",
        )

    async def _record_negotiation_run(
        self,
        result: Any,
        orchestration_trace: dict,
    ):
        try:
            from app.models.agent import AgentOrchestrationRun

            run = AgentOrchestrationRun(
                id=uuid.uuid4().hex,
                mode="negotiation",
                agent_ids=json.dumps([self.omni_agent.id]),
                input_message=self.user_message,
                output_result=json.dumps({
                    "final_agreement": result.final_agreement,
                    "consensus_reached": result.consensus_reached,
                    "rounds_run": result.rounds_run,
                    "deadlock_points": result.deadlock_points,
                    "suggested_mediator": result.suggested_mediator,
                }),
                execution_trace=json.dumps(orchestration_trace),
                token_usage=result.total_tokens,
                total_cost_usd=result.total_cost_usd,
                total_latency_ms=int((time.monotonic() - self.start_time) * 1000),
                status="completed" if result.consensus_reached else "partial_consensus",
            )
            self.db.add(run)
            await self.db.commit()
            logger.info(f"Recorded negotiation run {run.id}")
        except Exception as e:
            logger.error(f"Failed to record negotiation run: {e}")

    async def _record_orchestration_run(
        self,
        task_plan: TaskPlan,
        results: Dict[str, SubAgentResult],
        orchestration_trace: dict,
    ):
        try:
            from app.models.agent import AgentOrchestrationRun

            agent_ids = [self.omni_agent.id]
            sub_results_list = []
            total_tokens = 0
            total_cost = 0.0
            total_latency = int((time.monotonic() - self.start_time) * 1000)

            for r in results.values():
                total_tokens += r.tokens_used
                total_cost += r.cost_usd
                sub_results_list.append({
                    "sub_task_id": r.sub_task_id,
                    "agent_type": r.agent_type,
                    "status": r.status,
                    "tokens_used": r.tokens_used,
                    "cost_usd": r.cost_usd,
                    "latency_ms": r.latency_ms,
                    "error": r.error,
                })

            run = AgentOrchestrationRun(
                id=uuid.uuid4().hex,
                mode="hierarchical",
                agent_ids=json.dumps(agent_ids + self.spawned_agent_ids),
                input_message=self.user_message,
                output_result=json.dumps({
                    "task_plan": {
                        "original_request": task_plan.original_request,
                        "sub_task_ids": [st.id for st in task_plan.sub_tasks],
                        "execution_order": task_plan.execution_order,
                    },
                    "sub_results": sub_results_list,
                    "orchestration_trace": orchestration_trace,
                }),
                execution_trace=json.dumps(orchestration_trace),
                token_usage=total_tokens,
                total_cost_usd=total_cost,
                total_latency_ms=total_latency,
                status="completed" if all(r.status == "completed" for r in results.values()) else "partial_failure",
            )
            self.db.add(run)
            await self.db.commit()
            logger.info(f"Recorded orchestration run {run.id}")
        except Exception as e:
            logger.error(f"Failed to record orchestration run: {e}")

    async def _cleanup_spawned_agents(self):
        try:
            from app.models.agent import AgentReputationScore, SharedContextEntry
            for agent_id in self.spawned_agent_ids:
                try:
                    # Cleanup SharedContextEntry
                    ctx_res = await self.db.execute(
                        select(SharedContextEntry).where(SharedContextEntry.agent_id == agent_id)
                    )
                    for ctx in ctx_res.scalars().all():
                        await self.db.delete(ctx)

                    # Cleanup AgentReputationScore
                    score_res = await self.db.execute(
                        select(AgentReputationScore).where(AgentReputationScore.agent_id == agent_id).limit(1)
                    )
                    score = score_res.scalars().first()
                    if score:
                        await self.db.delete(score)

                    # Cleanup AgentConfig
                    config_res = await self.db.execute(
                        select(AgentConfig).where(AgentConfig.agent_id == agent_id).limit(1)
                    )
                    config = config_res.scalars().first()
                    if config:
                        await self.db.delete(config)

                    # Cleanup Agent
                    agent_res = await self.db.execute(
                        select(Agent).where(Agent.id == agent_id)
                    )
                    agent = agent_res.scalar_one_or_none()
                    if agent:
                        await self.db.delete(agent)
                except Exception as e:
                    logger.warning(f"Failed to cleanup spawned agent {agent_id}: {e}")

            await self.db.commit()
            self.spawned_agent_ids.clear()
        except Exception as e:
            logger.warning(f"Failed during cleanup of spawned agents: {e}")
