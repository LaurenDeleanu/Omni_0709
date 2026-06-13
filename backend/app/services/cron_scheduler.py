import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.cron_scheduler")

CHECK_INTERVAL = 60
_scheduler_task = None

CRON_FIELDS = {"minute", "hour", "day", "month", "weekday"}

_contract_expiry_last_run_date = None
_pipeline_scoring_last_run_date = None
_discovery_last_run_date = None


async def _run_contract_expiry_check(db_getter):
    global _contract_expiry_last_run_date
    from datetime import date

    today = date.today()
    if _contract_expiry_last_run_date == today:
        return

    _contract_expiry_last_run_date = today
    try:
        from app.services.contract_lifecycle import check_expiring_contracts, send_expiry_alerts

        async with db_getter() as db:
            result = await send_expiry_alerts(db)
            if result["sent"]:
                logger.info(f"Contract expiry alerts sent for {result['sent']} contracts")
    except Exception as e:
        logger.error(f"Contract expiry check failed: {e}")


async def _run_pipeline_scoring(db_getter):
    global _pipeline_scoring_last_run_date
    from datetime import date

    today = date.today()
    if _pipeline_scoring_last_run_date == today:
        return

    _pipeline_scoring_last_run_date = today
    try:
        from app.services.lead_scorer import batch_score_pipeline
        from app.core.redis import get_redis

        async with db_getter() as db:
            result = await batch_score_pipeline(db)
            pipeline_data = {
                "total_leads": result["pipeline_overview"]["total_leads"],
                "hot_leads": result["pipeline_overview"]["hot_leads"],
                "warm_leads": result["pipeline_overview"]["warm_leads"],
                "cold_leads": result["pipeline_overview"]["cold_leads"],
                "weighted_pipeline_value": result["forecasts"]["weighted_pipeline_value"],
                "expected_closures": result["forecasts"]["expected_closures_this_month"],
                "at_risk_deals": result["forecasts"]["at_risk_deals"],
                "scored_at": result["pipeline_overview"]["scored_at"],
            }
            try:
                import json
                r = await get_redis()
                await r.set("crm:pipeline:scoreboard", json.dumps(pipeline_data, default=str), ex=86400)
                await r.set("crm:pipeline:last_scored", result["pipeline_overview"]["scored_at"], ex=86400)
            except Exception as redis_err:
                logger.warning(f"Redis store for pipeline scoring failed (non-critical): {redis_err}")

            logger.info(
                f"Pipeline scoring complete: {pipeline_data['total_leads']} leads, "
                f"{pipeline_data['hot_leads']} hot, {pipeline_data['warm_leads']} warm, "
                f"{pipeline_data['cold_leads']} cold | Weighted value: ${pipeline_data['weighted_pipeline_value']:,.2f}"
            )
    except Exception as e:
        logger.error(f"Pipeline scoring job failed: {e}")


async def _run_weekly_discovery(db_getter):
    global _discovery_last_run_date
    from datetime import date

    today = date.today()
    if _discovery_last_run_date == today:
        return

    _discovery_last_run_date = today
    try:
        from app.services.skill_discovery import SkillDiscovery

        async with db_getter() as db:
            sd = SkillDiscovery()
            report = await sd.generate_discovery_report(db)
            task_count = len(report.tasks)
            suggestion_count = len(report.suggestions)
            summary = "No new automation opportunities found this week."
            if task_count or suggestion_count:
                summary = (
                    f"Skill Discovery found {task_count} new automation opportunities"
                    f" and {suggestion_count} suggested tools."
                )
            logger.info(
                f"Weekly skill discovery complete: {summary}"
            )
    except Exception as e:
        logger.error(f"Weekly skill discovery job failed: {e}")


_audit_archive_last_run_date = None

async def _run_audit_archive(db_getter):
    global _audit_archive_last_run_date
    from datetime import date
    
    today = date.today()
    if _audit_archive_last_run_date == today:
        return
        
    _audit_archive_last_run_date = today
    try:
        from app.services.audit_archive import archive_old_audit_logs
        
        async with db_getter() as db:
            result = await archive_old_audit_logs(db, retention_days=90)
            if result.get("archived", 0) > 0:
                logger.info(f"Audit log archive complete: {result['archived']} records removed")
    except Exception as e:
        logger.error(f"Audit log archive job failed: {e}")


def _cron_matches(cron_config: dict, now: datetime) -> bool:
    if not cron_config:
        return False
    try:
        minute = cron_config.get("minute", "*")
        hour = cron_config.get("hour", "*")
        day = cron_config.get("day", "*")
        month = cron_config.get("month", "*")
        weekday = cron_config.get("weekday", "*")

        def matches(field: str, current: int) -> bool:
            if field == "*" or not field:
                return True
            for part in str(field).split(","):
                part = part.strip()
                if part == str(current):
                    return True
                if "-" in part:
                    lo, hi = part.split("-", 1)
                    if int(lo) <= current <= int(hi):
                        return True
            return False

        return all([
            matches(minute, now.minute),
            matches(hour, now.hour),
            matches(day, now.day),
            matches(month, now.month),
            matches(weekday, now.weekday()),
        ])
    except Exception:
        return False


async def _execute_cron_triggers(db_getter):
    from app.models.workflow_trigger import WorkflowTrigger
    from app.services.workflow_runtime import execute_workflow_run

    async with db_getter() as db:
        result = await db.execute(
            select(WorkflowTrigger).where(
                WorkflowTrigger.type == "CRON",
                WorkflowTrigger.enabled == True,
            )
        )
        triggers = result.scalars().all()
        if not triggers:
            return 0

        now = datetime.now(timezone.utc)
        executed = 0
        for trigger in triggers:
            import json
            try:
                config = json.loads(trigger.config) if trigger.config else {}
            except json.JSONDecodeError:
                continue

            if not _cron_matches(config, now):
                continue

            try:
                await execute_workflow_run(db, trigger.bot_id, "cron_trigger")
                trigger.last_triggered_at = now
                executed += 1
            except Exception as e:
                logger.error(f"Cron trigger {trigger.id} failed: {e}")

        if executed:
            await db.commit()
        return executed


async def start_cron_scheduler(db_getter):
    global _scheduler_task
    async def _loop():
        while True:
            await asyncio.sleep(CHECK_INTERVAL)
            try:
                count = await _execute_cron_triggers(db_getter)
                if count:
                    logger.info(f"Cron scheduler executed {count} triggers")

                now = datetime.now(timezone.utc)
                if now.hour == 2 and now.minute < 1:
                    await _run_audit_archive(db_getter)
                if now.hour == 9 and now.minute < 1:
                    await _run_contract_expiry_check(db_getter)
                if now.hour == 8 and now.minute < 1:
                    await _run_pipeline_scoring(db_getter)
                if now.weekday() == 0 and now.hour == 3 and now.minute < 1:
                    await _run_weekly_discovery(db_getter)
            except Exception as e:
                logger.error(f"Cron scheduler error: {e}")

    _scheduler_task = asyncio.create_task(_loop())
    logger.info("Cron scheduler started (60s interval)")


def stop_cron_scheduler():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
