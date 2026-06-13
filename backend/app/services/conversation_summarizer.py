"""
Conversation Summarizer (Phase 1 — P0)
=======================================
Compresses conversation history every N turns into a 200-token summary.
Stores summaries in the conversation_epochs table with pgvector embeddings
for semantic memory retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import AsyncSessionGlobal

logger = logging.getLogger(__name__)

# Summarize every N turns
DEFAULT_SUMMARIZE_EVERY = 20

# Maximum summary length in tokens (target ~200)
MAX_SUMMARY_TOKENS = 200

SUMMARIZE_SYSTEM_PROMPT = (
    "Eres un compresor de conversaciones. Resume la siguiente conversación "
    "entre un usuario y un asistente de RRHH en 2-3 frases concisas en español. "
    "Preserva: decisiones tomadas, datos mencionados (nombres, fechas, cifras), "
    "preguntas importantes y acciones pendientes. No incluyas saludos ni despedidas."
)


async def summarize_conversation_epoch(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    db: Optional[AsyncSession] = None,
    max_tokens: int = MAX_SUMMARY_TOKENS,
) -> str:
    """Summarize a batch of conversation messages into a compact summary."""
    if not messages:
        return ""

    try:
        from app.services.llm_router import get_llm_client

        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')[:500]}"
            for m in messages
        )

        # Truncate if too long for the summarizer model
        if len(conversation_text) > 12000:
            conversation_text = conversation_text[:12000]

        client, _ = await get_llm_client(model, None, db)
        response = await client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
        )

        summary = response.choices[0].message.content or ""
        return summary.strip()
    except Exception as e:
        logger.warning(f"Summarization failed: {e}")
        # Fallback: simple truncation-based summary
        first_msg = messages[0].get("content", "")[:100] if messages else ""
        last_msg = messages[-1].get("content", "")[:100] if messages else ""
        return f"Conversación de {len(messages)} mensajes. Inicio: {first_msg}... Fin: {last_msg}..."


async def check_and_summarize(
    session_id: str,
    messages: List[Dict[str, str]],
    epoch_number: int,
    db: AsyncSession,
    agent_id: str = "",
    user_id: str = "",
    summarize_every: int = DEFAULT_SUMMARIZE_EVERY,
) -> Optional[str]:
    """
    Check if we should summarize (every N turns) and return the summary.
    Returns None if no summarization needed yet.
    """
    message_count = len(messages)

    if message_count < summarize_every:
        return None

    if message_count % summarize_every != 0:
        return None

    # Summarize the last N messages
    messages_to_summarize = messages[-summarize_every:]

    logger.info(
        f"Summarizing epoch {epoch_number} for session {session_id} "
        f"({summarize_every} messages)"
    )

    summary_text = await summarize_conversation_epoch(messages_to_summarize, db=db)

    # Store in conversation_epochs table if available
    try:
        from app.models.agent import ConversationEpoch

        turn_start = datetime.now(timezone.utc)
        turn_end = datetime.now(timezone.utc)

        # Try to generate embedding
        embedding = None
        try:
            from app.services.rag_service import generate_embedding
            embedding = await generate_embedding(summary_text)
        except Exception:
            pass

        epoch = ConversationEpoch(
            agent_id=agent_id,
            user_id=user_id,
            epoch_number=epoch_number,
            summary_text=summary_text,
            summary_embedding=embedding,
            turn_start=turn_start,
            turn_end=turn_end,
            message_count=summarize_every,
        )
        db.add(epoch)
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to persist conversation epoch: {e}")
        await db.rollback()

    return summary_text


async def get_recent_epoch_summaries(
    agent_id: str,
    user_id: str,
    limit: int = 3,
    db: Optional[AsyncSession] = None,
) -> List[str]:
    """Retrieve the most recent conversation epoch summaries."""
    try:
        from app.models.agent import ConversationEpoch

        if db is None:
            async with AsyncSessionGlobal() as session:
                result = await session.execute(
                    select(ConversationEpoch.summary_text)
                    .where(
                        ConversationEpoch.agent_id == agent_id,
                        ConversationEpoch.user_id == user_id,
                    )
                    .order_by(ConversationEpoch.epoch_number.desc())
                    .limit(limit)
                )
                return [row[0] for row in result.fetchall()]
        else:
            result = await db.execute(
                select(ConversationEpoch.summary_text)
                .where(
                    ConversationEpoch.agent_id == agent_id,
                    ConversationEpoch.user_id == user_id,
                )
                .order_by(ConversationEpoch.epoch_number.desc())
                .limit(limit)
            )
            return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to retrieve epoch summaries: {e}")
        return []


async def build_summary_context(
    agent_id: str,
    user_id: str,
    max_epochs: int = 3,
    db: Optional[AsyncSession] = None,
) -> str:
    """Build a context string from recent conversation epoch summaries."""
    summaries = await get_recent_epoch_summaries(agent_id, user_id, max_epochs, db)
    if not summaries:
        return ""

    context_parts = []
    for i, summary in enumerate(reversed(summaries)):
        context_parts.append(f"[Época anterior {i + 1}]: {summary}")

    return "\n".join(context_parts)
