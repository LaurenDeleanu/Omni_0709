import asyncio
import logging
from typing import Dict, List
from datetime import datetime, timezone

logger = logging.getLogger("successcore.cron_triggers")

_scheduled_triggers: List[dict] = []
_lock = asyncio.Lock()


def schedule_agent_trigger(agent_id: str, cron_expression: str, description: str = "") -> dict:
    entry = {
        "id": str(abs(hash(f"{agent_id}:{cron_expression}")) % 100000),
        "agent_id": agent_id,
        "cron": cron_expression,
        "description": description,
        "enabled": True,
        "last_run": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _scheduled_triggers.append(entry)
    return entry


def list_scheduled_triggers(agent_id: str = "") -> List[dict]:
    if agent_id:
        return [t for t in _scheduled_triggers if t["agent_id"] == agent_id]
    return _scheduled_triggers


def remove_scheduled_trigger(trigger_id: str) -> bool:
    global _scheduled_triggers
    before = len(_scheduled_triggers)
    _scheduled_triggers = [t for t in _scheduled_triggers if t["id"] != trigger_id]
    return len(_scheduled_triggers) < before


async def check_and_execute_triggers(db=None) -> int:
    now = datetime.now(timezone.utc)
    week_key = f"{now.year}-W{now.isocalendar().week:02d}-{now.isocalendar().weekday}"

    executed = 0
    for trigger in list(_scheduled_triggers):
        if not trigger["enabled"]:
            continue
        if trigger.get("_last_week_key") == week_key:
            continue

        try:
            if db:
                from app.services.agent_runtime import execute_agent_run
                await execute_agent_run(
                    db, trigger["agent_id"],
                    input_payload={"message": f"Scheduled trigger: {trigger['description']}", "user_id": "system"},
                    trigger_source="cron",
                )
            trigger["last_run"] = now.isoformat()
            trigger["_last_week_key"] = week_key
            executed += 1
            logger.info(f"Cron trigger executed: {trigger['agent_id']} ({trigger['description']})")
        except Exception as e:
            logger.error(f"Cron trigger failed: {trigger['agent_id']}: {e}")

    return executed
