import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

logger = logging.getLogger("successcore.retention")

DEFAULT_RETENTION_RULES = {
    "audit_logs": {"retention_days": 365, "description": "Audit trail entries"},
    "vacation_requests": {"retention_days": 730, "description": "Vacation request history"},
    "agent_execution_runs": {"retention_days": 90, "description": "AI agent execution logs"},
    "notifications": {"retention_days": 60, "description": "User notifications"},
    "expense_claims": {"retention_days": 2555, "description": "Financial records (7 years)"},
    "chat_messages": {"retention_days": 90, "description": "Chat messages"},
    "kudos": {"retention_days": 730, "description": "Peer recognition"},
}

_retention_rules = dict(DEFAULT_RETENTION_RULES)


def configure_retention(table_name: str, days: int):
    _retention_rules[table_name] = {"retention_days": days, "description": f"Custom: {days} days"}


async def enforce_retention(db: AsyncSession, table_overrides: dict = None) -> dict:
    results = {}
    rules = table_overrides or _retention_rules

    for table_name, config in rules.items():
        days = config["retention_days"]
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            from sqlalchemy import text
            result = await db.execute(
                text(f"SELECT COUNT(*) FROM {table_name} WHERE created_at < :cutoff"),
                {"cutoff": cutoff}
            )
            count = result.scalar() or 0

            if count > 0:
                await db.execute(
                    text(f"DELETE FROM {table_name} WHERE created_at < :cutoff"),
                    {"cutoff": cutoff}
                )
                logger.info(f"Retention purge: {table_name} — deleted {count} records older than {days} days")

            results[table_name] = {"deleted": count, "retention_days": days}
        except Exception as e:
            results[table_name] = {"error": str(e)}

    await db.commit()
    return {
        "purged_at": datetime.now(timezone.utc).isoformat(),
        "rules_applied": len(rules),
        "results": results,
    }
