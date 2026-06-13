import logging
import re
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.agent import AgentTriggerConfig, AgentTriggerQueue

logger = logging.getLogger("successcore.event_trigger")


def _resolve_template(template: str, event_data: dict) -> str:
    if not template:
        return ""
    pattern = re.compile(r"\{(\w+(?:\.\w+)*)\}")
    def replacer(match):
        key = match.group(1)
        keys = key.split(".")
        val = event_data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return match.group(0)
        return str(val)
    return pattern.sub(replacer, template)


def _matches_filter(filter_condition: dict, event_data: dict) -> bool:
    if not filter_condition:
        return True
    for key, expected in filter_condition.items():
        actual = event_data.get(key)
        if actual != expected:
            return False
    return True


async def handle_event(event_type: str, event_data: dict, db: AsyncSession):
    try:
        result = await db.execute(
            select(AgentTriggerConfig).where(
                AgentTriggerConfig.event_type == event_type,
                AgentTriggerConfig.is_active == True,
            )
        )
        triggers = result.scalars().all()

        if not triggers:
            return

        for trigger in triggers:
            if not _matches_filter(trigger.filter_condition or {}, event_data):
                logger.debug(f"Trigger {trigger.id} filter mismatch for event {event_type}")
                continue

            prompt = _resolve_template(trigger.input_template or "", event_data)
            if not prompt:
                prompt = f"Procesa el evento {event_type}: {event_data}"

            logger.info(
                f"Trigger {trigger.id} activated for event {event_type} -> agent {trigger.agent_id} "
                f"(auto_approve={trigger.auto_approve})"
            )

            if trigger.auto_approve:
                from app.services.agent_runtime import execute_agent_run
                try:
                    result = await execute_agent_run(
                        db=db,
                        agent_id=trigger.agent_id,
                        input_payload={"message": prompt, "user_id": "system"},
                        trigger_source="event",
                    )
                    queue_entry = AgentTriggerQueue(
                        trigger_id=trigger.id,
                        agent_id=trigger.agent_id,
                        event_data=event_data,
                        generated_prompt=prompt,
                        status="executed",
                        execution_run_id=result.get("run_id"),
                        reviewed_at=datetime.now(timezone.utc),
                        reviewed_by="system",
                    )
                    db.add(queue_entry)
                    await db.flush()
                except Exception as exc:
                    logger.error(f"Trigger {trigger.id} auto-execution failed: {exc}")
            else:
                queue_entry = AgentTriggerQueue(
                    trigger_id=trigger.id,
                    agent_id=trigger.agent_id,
                    event_data=event_data,
                    generated_prompt=prompt,
                    status="pending",
                )
                db.add(queue_entry)
                await db.flush()

    except Exception as e:
        logger.error(f"Error in handle_event for {event_type}: {e}")


async def get_trigger_queue(db: AsyncSession, status: str = "pending") -> list:
    result = await db.execute(
        select(AgentTriggerQueue).where(
            AgentTriggerQueue.status == status
        ).order_by(AgentTriggerQueue.created_at.desc()).limit(100)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "trigger_id": e.trigger_id,
            "agent_id": e.agent_id,
            "event_data": e.event_data,
            "generated_prompt": e.generated_prompt,
            "status": e.status,
            "execution_run_id": e.execution_run_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
            "reviewed_by": e.reviewed_by,
        }
        for e in entries
    ]


async def approve_trigger(queue_id: str, db: AsyncSession):
    entry_res = await db.execute(
        select(AgentTriggerQueue).where(AgentTriggerQueue.id == queue_id)
    )
    entry = entry_res.scalar_one_or_none()
    if not entry:
        raise ValueError(f"Queue entry {queue_id} not found")
    if entry.status != "pending":
        raise ValueError(f"Queue entry {queue_id} is not pending (status={entry.status})")

    from app.services.agent_runtime import execute_agent_run
    try:
        result = await execute_agent_run(
            db=db,
            agent_id=entry.agent_id,
            input_payload={"message": entry.generated_prompt, "user_id": "system"},
            trigger_source="event",
        )
        entry.status = "executed"
        entry.execution_run_id = result.get("run_id")
        entry.reviewed_at = datetime.now(timezone.utc)
        entry.reviewed_by = "manual_approval"
        await db.flush()
        return entry
    except Exception as exc:
        logger.error(f"Approve trigger execution failed: {exc}")
        raise


async def reject_trigger(queue_id: str, db: AsyncSession):
    entry_res = await db.execute(
        select(AgentTriggerQueue).where(AgentTriggerQueue.id == queue_id)
    )
    entry = entry_res.scalar_one_or_none()
    if not entry:
        raise ValueError(f"Queue entry {queue_id} not found")
    entry.status = "rejected"
    entry.reviewed_at = datetime.now(timezone.utc)
    entry.reviewed_by = "manual_rejection"
    await db.flush()
    return entry
