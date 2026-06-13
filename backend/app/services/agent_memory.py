import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models.agent import AgentExecutionRun

logger = logging.getLogger("successcore.memory")

MAX_MEMORY_TURNS = 20
MEMORY_WINDOW_HOURS = 2


async def load_conversation_memory(
    db: AsyncSession,
    agent_id: str,
    user_id: str,
    max_turns: int = MAX_MEMORY_TURNS,
) -> List[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MEMORY_WINDOW_HOURS)
    result = await db.execute(
        select(AgentExecutionRun)
        .where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.status == "success",
            AgentExecutionRun.created_at >= cutoff,
            AgentExecutionRun.input_payload["user_id"].as_string() == str(user_id),
        )
        .order_by(AgentExecutionRun.created_at.desc())
        .limit(max_turns)
    )
    runs = list(result.scalars().all())

    memory = []
    for r in reversed(runs):
        user_msg = r.input_payload.get("message", "") if r.input_payload else ""
        reply = r.output_result.get("reply", "") if r.output_result else ""
        if user_msg and reply:
            memory.append({"role": "user", "content": user_msg})
            memory.append({"role": "assistant", "content": reply})
    return memory


async def save_conversation_turn(
    db: AsyncSession,
    agent_id: str,
    user_id: str,
    user_message: str,
    assistant_reply: str,
) -> None:
    from app.models.agent import AgentExecutionRun
    import uuid

    run = AgentExecutionRun(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        trigger_source="conversation",
        status="success",
        input_payload={"message": user_message, "user_id": user_id},
        output_result={"reply": assistant_reply},
        loop_count=1,
        token_usage=0,
        cost_usd=0.0,
        latency_ms=0,
        execution_trace="",
    )
    db.add(run)
    await db.flush()
