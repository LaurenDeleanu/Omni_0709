import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("successcore.backup_scheduler")

BACKUP_INTERVAL_HOURS = 24
BACKUP_KEEP_COUNT = 7
_scheduler_task: asyncio.Task | None = None


async def _run_scheduled_backup():
    while True:
        await asyncio.sleep(BACKUP_INTERVAL_HOURS * 3600)
        try:
            from app.services.db_backup import backup_database, list_backups, DEFAULT_BACKUP_DIR
            import os

            backup_path = backup_database()
            logger.info(f"Scheduled backup created: {backup_path}")

            backups = list_backups()
            if len(backups) > BACKUP_KEEP_COUNT:
                for old in backups[BACKUP_KEEP_COUNT:]:
                    os.remove(old["path"])
                    logger.info(f"Rotated old backup: {old['filename']}")
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")


def start_backup_scheduler():
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_run_scheduled_backup())
        logger.info(f"Backup scheduler started (every {BACKUP_INTERVAL_HOURS}h, keep {BACKUP_KEEP_COUNT})")


def stop_backup_scheduler():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Backup scheduler stopped")
