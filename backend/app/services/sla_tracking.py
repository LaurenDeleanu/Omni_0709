"""
sla_tracking.py — IT ticket SLA monitoring, breach detection, and alerting.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.sla")

SLA_POLICIES = {
    "critical": {"response_minutes": 15, "resolution_hours": 4, "business_hours_only": False},
    "high": {"response_minutes": 60, "resolution_hours": 24, "business_hours_only": False},
    "medium": {"response_minutes": 240, "resolution_hours": 72, "business_hours_only": True},
    "low": {"response_minutes": 480, "resolution_hours": 168, "business_hours_only": True},
}


async def get_ticket_sla_status(
    db: AsyncSession,
    tenant_id: str,
    ticket_id: Optional[str] = None,
) -> dict:
    """Get SLA status for IT tickets — response time and resolution time breaches."""
    from app.models.it import ITTicket

    query = select(ITTicket)
    if ticket_id:
        query = query.where(ITTicket.id == ticket_id)

    result = await db.execute(query.order_by(ITTicket.created_at.desc()).limit(200))
    tickets = result.scalars().all()

    now = datetime.now(timezone.utc)
    statuses = []
    breaches = []
    summary = {"total": 0, "on_track": 0, "response_breached": 0, "resolution_breached": 0, "resolved": 0}

    for t in tickets:
        summary["total"] += 1
        priority = getattr(t, "priority", "medium") or "medium"
        policy = SLA_POLICIES.get(priority.lower(), SLA_POLICIES["medium"])

        created = t.created_at.replace(tzinfo=timezone.utc) if t.created_at else now
        first_response = getattr(t, "first_response_at", None)
        resolved_at = getattr(t, "resolved_at", None)
        status = getattr(t, "status", "open") or "open"

        response_deadline = created + timedelta(minutes=policy["response_minutes"])
        resolution_deadline = created + timedelta(hours=policy["resolution_hours"])

        response_breach = first_response and first_response.replace(tzinfo=timezone.utc) > response_deadline
        resolution_breach = resolved_at and resolved_at.replace(tzinfo=timezone.utc) > resolution_deadline

        if status in ("resolved", "closed"):
            summary["resolved"] += 1
            if response_breach:
                summary["response_breached"] += 1
            if resolution_breach:
                summary["resolution_breached"] += 1
            continue

        response_due = not first_response and now > response_deadline
        resolution_due = not resolved_at and now > resolution_deadline

        if response_due or resolution_due:
            summary["response_breached" if response_due else "resolution_breached"] += 1

        on_track = not response_due and not resolution_due
        if on_track:
            summary["on_track"] += 1

        statuses.append({
            "id": t.id,
            "title": getattr(t, "title", "") or getattr(t, "subject", ""),
            "priority": priority,
            "status": status,
            "created_at": created.isoformat(),
            "response_deadline": response_deadline.isoformat(),
            "resolution_deadline": resolution_deadline.isoformat(),
            "response_due": response_due,
            "resolution_due": resolution_due,
            "response_time_minutes": round((first_response.replace(tzinfo=timezone.utc) - created).total_seconds() / 60, 1) if first_response else None,
        })

    summary["compliance_rate"] = round(
        (summary["total"] - summary["response_breached"] - summary["resolution_breached"]) / summary["total"] * 100, 1
    ) if summary["total"] else 100

    return {
        "summary": summary,
        "tickets": statuses,
        "policies": SLA_POLICIES,
        "generated_at": now.isoformat(),
    }


async def get_sla_dashboard(db: AsyncSession, tenant_id: str) -> dict:
    """Get SLA dashboard — aggregated metrics for IT management."""
    status = await get_ticket_sla_status(db, tenant_id)

    return {
        "compliance_rate": status["summary"]["compliance_rate"],
        "total_tickets": status["summary"]["total"],
        "open_tickets": status["summary"]["total"] - status["summary"]["resolved"],
        "breached_tickets": status["summary"]["response_breached"] + status["summary"]["resolution_breached"],
        "avg_response_minutes": round(
            sum(t.get("response_time_minutes", 0) or 0 for t in status["tickets"]) / max(len(status["tickets"]), 1), 1
        ),
        "policies": SLA_POLICIES,
        "recent_breaches": [
            t for t in status["tickets"] if t.get("response_due") or t.get("resolution_due")
        ][:10],
        "generated_at": status["generated_at"],
    }
