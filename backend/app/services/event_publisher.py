# app/services/event_publisher.py — Domain event publisher for cross-module notifications
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.event_catalog import (
    EXPENSE_APPROVED, EXPENSE_REJECTED,
    VACATION_APPROVED, VACATION_REJECTED, VACATION_REQUESTED,
    COURSE_COMPLETED, TRAINING_ENROLLED,
    KUDOS_RECEIVED, AGENT_RUN_COMPLETED, AGENT_CREATED,
    EMPLOYEE_ARCHIVED, CANDIDATE_HIRED,
)

logger = logging.getLogger("successcore.event_publisher")


def _publish(event_type: str, payload: dict, tenant_id: str = "acme_corp"):
    from app.services.event_sourcing import publish_event
    try:
        publish_event(event_type, payload, tenant_id=tenant_id)
    except Exception as e:
        logger.warning(f"Event publish failed ({event_type}): {e}")


# ── Expense Events ──────────────────────────────────────────────────────────────
async def publish_expense_event(db: AsyncSession, claim_id: str, user_id: str, amount: float, category: str, status: str, tenant_id: str = "acme_corp"):
    if status not in ("approved", "rejected"):
        return
    _publish(
        EXPENSE_APPROVED if status == "approved" else EXPENSE_REJECTED,
        {"claim_id": claim_id, "user_id": user_id, "amount": amount, "category": category},
        tenant_id=tenant_id
    )


# ── Vacation Events ─────────────────────────────────────────────────────────────
async def publish_vacation_requested(db: AsyncSession, request_id: str, user_id: str, start_date, end_date, tenant_id: str = "acme_corp"):
    _publish(
        VACATION_REQUESTED,
        {"request_id": request_id, "user_id": user_id, "start_date": str(start_date), "end_date": str(end_date)},
        tenant_id=tenant_id
    )


async def publish_vacation_event(db: AsyncSession, request_id: str, user_id: str, start_date, end_date, status: str, tenant_id: str = "acme_corp"):
    if status not in ("approved", "rejected"):
        return
    _publish(
        VACATION_APPROVED if status == "approved" else VACATION_REJECTED,
        {"request_id": request_id, "user_id": user_id, "start_date": str(start_date), "end_date": str(end_date)},
        tenant_id=tenant_id
    )


# ── Training Events ─────────────────────────────────────────────────────────────
async def publish_training_event(db: AsyncSession, enrollment_id: str, user_id: str, course_id: str, status: str, tenant_id: str = "acme_corp"):
    if status == "completed":
        _publish(COURSE_COMPLETED, {"enrollment_id": enrollment_id, "user_id": user_id, "course_id": course_id}, tenant_id=tenant_id)
    elif status == "enrolled":
        _publish(TRAINING_ENROLLED, {"enrollment_id": enrollment_id, "user_id": user_id, "course_id": course_id}, tenant_id=tenant_id)


# ── Kudos Events ────────────────────────────────────────────────────────────────
async def publish_kudos_event(db: AsyncSession, kudos_id: str, sender_id: str, receiver_id: str, badge: str, message: str, tenant_id: str = "acme_corp"):
    _publish(KUDOS_RECEIVED, {"kudos_id": kudos_id, "sender_id": sender_id, "receiver_id": receiver_id, "badge": badge, "message": message}, tenant_id=tenant_id)


# ── Agent Events ────────────────────────────────────────────────────────────────
async def publish_agent_run_event(db: AsyncSession, run_id: str, agent_id: str, status: str, cost_usd: float, latency_ms: int, tenant_id: str = "acme_corp"):
    _publish(AGENT_RUN_COMPLETED, {"run_id": run_id, "agent_id": agent_id, "status": status, "cost_usd": cost_usd, "latency_ms": latency_ms}, tenant_id=tenant_id)


# ── Employee Lifecycle Events ────────────────────────────────────────────────────
def publish_employee_archived(user_id: str, email: str, tenant_id: str = "acme_corp"):
    _publish(EMPLOYEE_ARCHIVED, {"user_id": user_id, "email": email}, tenant_id=tenant_id)


def publish_candidate_hired(candidate_id: str, job_id: str, user_id: str, tenant_id: str = "acme_corp"):
    _publish(CANDIDATE_HIRED, {"candidate_id": candidate_id, "job_id": job_id, "user_id": user_id}, tenant_id=tenant_id)


def publish_onboarding_completed(employee_id: str, workflow_id: str, plan_summary: str, tenant_id: str = "acme_corp"):
    _publish("onboarding.completed", {"employee_id": employee_id, "workflow_id": workflow_id, "plan_summary": plan_summary}, tenant_id=tenant_id)
