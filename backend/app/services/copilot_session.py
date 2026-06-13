import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.agent import Agent, AgentSession, EpisodicMemory

logger = logging.getLogger(__name__)

SESSION_MAX_AGE_HOURS = 24


async def get_or_create_session(
    user_id: str,
    agent_id: str,
    db: AsyncSession,
) -> AgentSession:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_MAX_AGE_HOURS)

    result = await db.execute(
        select(AgentSession)
        .where(
            AgentSession.user_id == user_id,
            AgentSession.agent_id == agent_id,
            AgentSession.status == "active",
            AgentSession.last_active_at >= cutoff,
        )
        .order_by(desc(AgentSession.last_active_at))
        .limit(1)
    )
    session = result.scalar_one_or_none()

    if session:
        session.last_active_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)
        return session

    session = AgentSession(
        id=uuid.uuid4().hex,
        user_id=user_id,
        agent_id=agent_id,
        conversation_history=[],
        status="active",
        total_turns=0,
        total_cost_usd=0.0,
        started_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def save_conversation_turn(
    session_id: str,
    role: str,
    content: str,
    db: AsyncSession,
) -> None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        logger.warning(f"Session {session_id} not found for turn save")
        return

    history = session.conversation_history or []
    turn = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    history.append(turn)

    session.conversation_history = history
    session.total_turns = (session.total_turns or 0) + 1
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()

    # Check if we should summarize this epoch (every 20 turns)
    try:
        from app.services.conversation_summarizer import check_and_summarize
        messages_to_check = [{"role": t.get("role"), "content": t.get("content")} for t in history]
        epoch_num = (session.total_turns or 0) // 20
        if epoch_num > 0 and session.total_turns % 20 == 0:
            await check_and_summarize(
                session_id=session.id,
                messages=messages_to_check,
                epoch_number=epoch_num,
                db=db,
                agent_id=session.agent_id,
                user_id=session.user_id,
                summarize_every=20
            )
    except Exception as e:
        logger.warning(f"Epoch summarization failed in save_conversation_turn: {e}")



async def get_session_history(
    session_id: str,
    max_turns: int = 50,
    db: AsyncSession = None,
) -> list:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return []

    history = session.conversation_history or []
    recent = history[-max_turns:]
    recent.reverse()
    return recent


async def end_session(
    session_id: str,
    db: AsyncSession,
) -> Optional[dict]:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return None

    session.status = "completed"
    await db.commit()
    await db.refresh(session)

    history = session.conversation_history or []
    if history and len(history) >= 2:
        try:
            last_user_msgs = []
            last_assistant_msgs = []
            reversed_history = list(reversed(history))
            for turn in reversed_history:
                if turn.get("role") == "user" and len(last_user_msgs) < 3:
                    last_user_msgs.insert(0, turn.get("content", "")[:500])
                if turn.get("role") == "assistant" and len(last_assistant_msgs) < 3:
                    last_assistant_msgs.insert(0, turn.get("content", "")[:500])

            user_text = " | ".join(last_user_msgs)
            assistant_text = " | ".join(last_assistant_msgs)

            if user_text and assistant_text:
                memory = EpisodicMemory(
                    id=uuid.uuid4().hex,
                    agent_id=session.agent_id,
                    user_id=session.user_id,
                    memory_type="conversation",
                    content=(
                        f"User asked: {user_text[:1000]}\n"
                        f"Assistant responded: {assistant_text[:1000]}"
                    ),
                    occurred_at=datetime.now(timezone.utc),
                    importance_score=0.5,
                )
                db.add(memory)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to create episodic memory for session {session_id}: {e}")

    # Trigger memory consolidation and temporal decay
    try:
        from app.services.semantic_memory import consolidate_memories, apply_memory_decay
        await consolidate_memories(user_id=session.user_id, db=db, agent_id=session.agent_id)
        await apply_memory_decay(user_id=session.user_id, db=db, agent_id=session.agent_id)
    except Exception as e:
        logger.warning(f"Failed to run consolidation or decay in end_session: {e}")

    return {
        "session_id": session.id,
        "status": session.status,
        "total_turns": session.total_turns,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "last_active_at": session.last_active_at.isoformat() if session.last_active_at else None,
    }


async def list_user_sessions(
    user_id: str,
    db: AsyncSession,
) -> list:
    result = await db.execute(
        select(
            AgentSession,
            Agent.name.label("agent_name"),
        )
        .join(Agent, AgentSession.agent_id == Agent.id, isouter=True)
        .where(AgentSession.user_id == user_id)
        .order_by(desc(AgentSession.last_active_at))
    )
    rows = result.all()

    sessions = []
    for row in rows:
        session = row[0] if isinstance(row, tuple) else row
        agent_name = row[1] if isinstance(row, tuple) and len(row) > 1 else ""
        sessions.append({
            "session_id": session.id,
            "agent_id": session.agent_id,
            "agent_name": agent_name,
            "status": session.status,
            "total_turns": session.total_turns,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "last_active_at": session.last_active_at.isoformat() if session.last_active_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        })

    return sessions


async def load_session_as_messages(
    session_id: str,
    max_turns: int = 20,
    db: AsyncSession = None,
) -> list:
    history = await get_session_history(session_id, max_turns, db)
    history_reversed = list(reversed(history))
    return [
        {"role": t.get("role", "user"), "content": t.get("content", "")}
        for t in history_reversed
    ]
