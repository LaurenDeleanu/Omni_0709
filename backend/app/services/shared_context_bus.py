import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.agent import SharedContextEntry

logger = logging.getLogger(__name__)


async def publish_context(
    orchestration_id: str,
    agent_id: str,
    topic: str,
    data: dict,
    db: AsyncSession,
    ttl_seconds: int = 300,
    tenant_id: str = "default",
) -> str:
    entry_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    entry = SharedContextEntry(
        id=entry_id,
        orchestration_id=orchestration_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        topic=topic,
        data=data,
        ttl_seconds=ttl_seconds,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    db.add(entry)
    await db.commit()

    redis_channel = f"context:{tenant_id}:{topic}"
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        payload = json.dumps({
            "orchestration_id": orchestration_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "topic": topic,
            "data": data,
            "entry_id": entry_id,
        }, default=str)
        await r.publish(redis_channel, payload)
    except Exception as e:
        logger.debug(f"Redis pub/sub unavailable for context '{tenant_id}:{topic}': {e}")

    logger.info(f"Published context: {tenant_id}/{topic} from agent {agent_id}")
    return entry_id


async def subscribe_context(
    tenant_id: str,
    agent_id: str,
    topics: list[str],
    db: AsyncSession,
) -> dict:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(SharedContextEntry).where(
            and_(
                SharedContextEntry.tenant_id == tenant_id,
                SharedContextEntry.topic.in_(topics),
                SharedContextEntry.created_at <= now,
                or_(
                    SharedContextEntry.expires_at.is_(None),
                    SharedContextEntry.expires_at >= now,
                ),
            )
        ).order_by(SharedContextEntry.created_at.desc())
    )
    entries = result.scalars().all()

    aggregated: dict = {}
    for entry in entries:
        if entry.topic not in aggregated:
            aggregated[entry.topic] = []
        aggregated[entry.topic].append({
            "agent_id": entry.agent_id,
            "data": entry.data,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })

    logger.info(
        f"Subscribed context for tenant {tenant_id}: "
        f"{len(entries)} entries across {len(aggregated)} topics"
    )
    return {
        "tenant_id": tenant_id,
        "subscriber_agent": agent_id,
        "topics": topics,
        "entry_count": len(entries),
        "aggregated": aggregated,
    }


async def find_reusable_context(
    tenant_id: str,
    query: str,
    db: AsyncSession,
    limit: int = 5,
) -> dict:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(SharedContextEntry).where(
            and_(
                SharedContextEntry.tenant_id == tenant_id,
                SharedContextEntry.created_at <= now,
                or_(
                    SharedContextEntry.expires_at.is_(None),
                    SharedContextEntry.expires_at >= now,
                ),
            )
        ).order_by(SharedContextEntry.created_at.desc()).limit(limit * 2)
    )
    entries = result.scalars().all()

    if not entries:
        return {
            "tenant_id": tenant_id,
            "query": query,
            "matches": [],
            "match_count": 0,
        }

    matches = []
    query_lower = query.lower()
    for entry in entries:
        try:
            data_text = json.dumps(entry.data).lower()
        except (TypeError, ValueError):
            data_text = str(entry.data).lower()

        topic_lower = (entry.topic or "").lower()
        score = 0

        if query_lower in topic_lower:
            score += 3
        if query_lower in data_text:
            score += 2

        keywords = query_lower.split()
        for kw in keywords:
            if kw in topic_lower:
                score += 1
            if kw in data_text:
                score += 1

        if score > 0:
            matches.append({
                "entry_id": entry.id,
                "agent_id": entry.agent_id,
                "topic": entry.topic,
                "data": entry.data,
                "relevance_score": score,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            })

    matches.sort(key=lambda m: m["relevance_score"], reverse=True)
    matches = matches[:limit]

    return {
        "tenant_id": tenant_id,
        "query": query,
        "matches": matches,
        "match_count": len(matches),
    }
