import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import AgentSchedule
from app.core.database import AsyncSessionGlobal

logger = logging.getLogger("successcore.agent_scheduler")

CHECK_INTERVAL = 60
_scheduler_task = None


def _parse_cron_expression(cron_expr: str) -> list:
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        parts = ["*"] * 5
    return parts


def _next_run_from_cron(cron_expr: str, from_dt: datetime = None) -> datetime:
    if from_dt is None:
        from_dt = datetime.now(timezone.utc)
    parts = _parse_cron_expression(cron_expr)
    minute, hour, dom, month, dow = parts

    def _match(value: str, current: int) -> bool:
        if value == "*":
            return True
        for part in value.split(","):
            part = part.strip()
            if part == str(current):
                return True
            if "/" in part:
                base, step = part.split("/")
                base = int(base) if base != "*" else 0
                if (current - base) % int(step) == 0:
                    return True
            if "-" in part:
                lo, hi = part.split("-")
                if int(lo) <= current <= int(hi):
                    return True
        return False

    current = from_dt.replace(second=0, microsecond=0)
    max_iterations = 366 * 24 * 60

    for _ in range(max_iterations):
        current = current + timedelta(minutes=1)
        if _match(minute, current.minute) and _match(hour, current.hour) and _match(dom, current.day) and _match(month, current.month) and _match(dow, current.isoweekday() % 7):
            return current

    return from_dt + timedelta(minutes=1)


def _resolve_variables(template: str, variables: dict) -> str:
    if not variables:
        return template
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


async def check_due_schedules(db: AsyncSession):
    now = datetime.now(timezone.utc)
    try:
        result = await db.execute(
            select(AgentSchedule).where(
                AgentSchedule.is_active == True,
                AgentSchedule.next_run_at <= now,
            )
        )
        schedules = result.scalars().all()
    except Exception as e:
        logger.debug(f"Scheduler check skipped (table not available): {e}")
        return 0

    if not schedules:
        return 0

    from app.services.agent_runtime import execute_agent_run

    executed = 0
    for sched in schedules:
        try:
            prompt = _resolve_variables(sched.input_template, sched.input_variables or {})
            result = await execute_agent_run(
                db=db,
                agent_id=sched.agent_id,
                input_payload={"message": prompt, "user_id": "system"},
                trigger_source="cron",
            )

            sched.last_run_at = now
            sched.last_run_status = result.get("status", "success")
            sched.next_run_at = _next_run_from_cron(sched.cron_expression, now)

            executed += 1
            logger.info(f"Schedule '{sched.name}' executed for agent {sched.agent_id}")

        except Exception as e:
            sched.last_run_status = "failed"
            logger.error(f"Schedule '{sched.name}' failed: {e}")

    if executed:
        await db.commit()

    return executed


async def _scheduler_loop(db_getter):
    while True:
        try:
            async with db_getter() as db:
                await check_due_schedules(db)
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


async def start_scheduler(db_getter=None):
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        return
    if db_getter is None:
        db_getter = lambda: AsyncSessionGlobal()
    _scheduler_task = asyncio.create_task(_scheduler_loop(db_getter))
    logger.info("Agent scheduler started")


async def stop_scheduler():
    global _scheduler_task
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("Agent scheduler stopped")
