import asyncio
import logging
from datetime import datetime, timezone, time

logger = logging.getLogger("successcore.digest_scheduler")

DIGEST_HOUR = 8
DIGEST_MINUTE = 0
_task = None


async def _run_digest_loop():
    while True:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=DIGEST_HOUR, minute=DIGEST_MINUTE, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run.replace(day=next_run.day + 1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        try:
            from app.core.database import AsyncSessionGlobal
            async with AsyncSessionGlobal() as db:
                from app.services.email_digest_sender import send_daily_digest
                result = await send_daily_digest(db, "admin@successcore.com")
                logger.info(f"Daily digest sent: {result}")
        except Exception as e:
            logger.error(f"Daily digest failed: {e}")


def start_digest_scheduler():
    global _task
    _task = asyncio.create_task(_run_digest_loop())
    logger.info(f"Daily digest scheduler started (daily at {DIGEST_HOUR:02d}:{DIGEST_MINUTE:02d} UTC)")


def stop_digest_scheduler():
    global _task
    if _task and not _task.done():
        _task.cancel()
