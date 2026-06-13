import logging
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.agent_runtime import execute_agent_run

logger = logging.getLogger(__name__)

SPECIALIST_AGENT_TYPES = [
    "hr_assistant",
    "payroll_specialist",
    "it_helpdesk",
    "recruiter",
    "sales_coach",
    "performance_coach",
    "onboarding_buddy",
    "compliance_officer",
    "data_analyst",
    "finance_manager",
]


@dataclass
class HandoffResult:
    from_agent: str
    to_agent: str
    new_run_id: str
    session_id: str
    handoff_context: dict
    status: str
    error: Optional[str] = None


class AgentHandoffProtocol:

    HANDOFF_SYSTEM_PROMPT_TEMPLATE = """You are {agent_type} for SuccessCore. You have received a handoff from {from_agent}.

CONTEXT FROM PREVIOUS AGENT:
{context_summary}

USER INFORMATION:
User ID: {user_id}

TASK TO HANDLE:
{task_description}

IMPORTANT: You are taking over this conversation. Use the context provided above to understand what has been done. 
Focus on completing the remaining open items. Be concise and direct."""

    @classmethod
    async def handoff(
        cls,
        from_agent_id: str,
        to_agent_type: str,
        user_id: str,
        task: str,
        context: dict,
        db: AsyncSession,
    ) -> HandoffResult:
        handoff_package = {
            "from_agent": from_agent_id,
            "to_agent_type": to_agent_type,
            "user_id": user_id,
            "task_description": task,
            "context_snapshot": context,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }

        try:
            from_agent_result = await db.execute(select(Agent).where(Agent.id == from_agent_id))
            from_agent = from_agent_result.scalar_one_or_none()
            from_agent_name = from_agent.name if from_agent else from_agent_id
        except Exception:
            from_agent_name = from_agent_id

        target_agent_result = await db.execute(
            select(Agent).where(
                Agent.agent_type == to_agent_type.upper(),
                Agent.is_active == True,
            ).limit(1)
        )
        target_agent = target_agent_result.scalar_one_or_none()

        if not target_agent:
            available_result = await db.execute(
                select(Agent.agent_type).where(Agent.is_active == True).distinct()
            )
            available_types = [row[0] for row in available_result.all()]
            return HandoffResult(
                from_agent=from_agent_id,
                to_agent="",
                new_run_id="",
                session_id="",
                handoff_context=handoff_package,
                status="error",
                error=f"No active agent found for type '{to_agent_type}'. Available: {', '.join(available_types)}",
            )

        session_id = uuid.uuid4().hex

        context_summary = context.get("summary", "No prior context available.")
        decisions = context.get("decisions", [])
        open_items = context.get("open_items", [])

        decisions_text = "\n".join(f"- {d}" for d in decisions) if decisions else "(none)"
        open_items_text = "\n".join(f"- {o}" for o in open_items) if open_items else "(none)"

        handoff_context_text = (
            f"I've completed the following tasks: {context_summary}\n"
            f"Key findings: {decisions_text}\n"
            f"The user still needs: {open_items_text}"
        )

        input_payload = {
            "message": task,
            "user_id": user_id,
            "handoff_context": {
                "from_agent": from_agent_name,
                "from_agent_id": from_agent_id,
                "context_summary": context_summary,
                "decisions": decisions,
                "open_items": open_items,
                "session_id": session_id,
            },
        }

        try:
            result = await execute_agent_run(
                db=db,
                agent_id=target_agent.id,
                input_payload=input_payload,
                trigger_source="handoff",
            )

            new_run_id = result.get("run_id", "")
            if not new_run_id:
                run_result = await db.execute(
                    select(AgentExecutionRun)
                    .where(AgentExecutionRun.agent_id == target_agent.id)
                    .order_by(AgentExecutionRun.created_at.desc())
                    .limit(1)
                )
                run_log = run_result.scalar_one_or_none()
                new_run_id = run_log.id if run_log else ""

            return HandoffResult(
                from_agent=from_agent_id,
                to_agent=target_agent.id,
                new_run_id=new_run_id,
                session_id=session_id,
                handoff_context=handoff_package,
                status="completed",
            )
        except Exception as e:
            logger.error(f"Handoff execution failed: {e}")
            return HandoffResult(
                from_agent=from_agent_id,
                to_agent=target_agent.id,
                new_run_id="",
                session_id=session_id,
                handoff_context=handoff_package,
                status="failed",
                error=str(e),
            )

    @classmethod
    async def build_handoff_context(
        cls,
        from_agent_id: str,
        user_id: str,
        session_id: str,
        db: AsyncSession,
    ) -> dict:
        try:
            from app.models.agent import AgentSession
            session_result = await db.execute(
                select(AgentSession).where(AgentSession.id == session_id)
            )
            session = session_result.scalar_one_or_none()
            conversation_history = session.conversation_history if session else {}
        except Exception:
            conversation_history = {}

        try:
            runs_result = await db.execute(
                select(AgentExecutionRun)
                .where(
                    AgentExecutionRun.agent_id == from_agent_id,
                )
                .order_by(AgentExecutionRun.created_at.desc())
                .limit(10)
            )
            recent_runs = runs_result.scalars().all()

            tool_calls_made = []
            decisions_reached = []
            for run in recent_runs:
                if run.status == "failed":
                    continue
                try:
                    trace = json.loads(run.execution_trace) if run.execution_trace else []
                    for step in trace:
                        if isinstance(step, dict) and step.get("step") == "tool_call":
                            tool_calls_made.append({
                                "tool": step.get("tool", ""),
                                "args": step.get("args", {}),
                            })
                except (json.JSONDecodeError, TypeError):
                    pass
                try:
                    output = run.output_result or {}
                    if isinstance(output, str):
                        output = json.loads(output)
                    if isinstance(output, dict) and output.get("reply"):
                        decisions_reached.append(output["reply"][:300])
                except (json.JSONDecodeError, TypeError):
                    pass
        except Exception:
            tool_calls_made = []
            decisions_reached = []

        try:
            from app.models.agent import EpisodicMemory
            memory_result = await db.execute(
                select(EpisodicMemory)
                .where(
                    EpisodicMemory.agent_id == from_agent_id,
                    EpisodicMemory.user_id == user_id,
                )
                .order_by(EpisodicMemory.occurred_at.desc())
                .limit(5)
            )
            memories = memory_result.scalars().all()
            memory_texts = [m.content[:200] for m in memories if m.content]
        except Exception:
            memory_texts = []

        summary_parts = []
        if tool_calls_made:
            tools_list = [tc["tool"] for tc in tool_calls_made[:5]]
            summary_parts.append(f"used tools: {', '.join(tools_list)}")
        if memory_texts:
            summary_parts.append(f"recent interactions: {'; '.join(memory_texts[:3])}")

        summary = "; ".join(summary_parts) if summary_parts else "no significant actions taken"

        open_items = []
        if not any(tc["tool"] for tc in tool_calls_made if tc["tool"] in ("approve_vacation", "request_vacation", "create_it_ticket", "move_candidate_stage")):
            open_items.append("User request may still be pending resolution")

        return {
            "agent_id": from_agent_id,
            "summary": summary,
            "tool_calls": tool_calls_made,
            "decisions": decisions_reached[-3:],
            "open_items": open_items,
            "session_id": session_id,
            "user_id": user_id,
        }
