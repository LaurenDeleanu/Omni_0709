import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import uuid

from app.models.agent import HumanApprovalRequest

logger = logging.getLogger("successcore.human_approval")

APPROVAL_EXPIRY_HOURS = 4


async def request_approval(
    agent_id: str,
    run_id: str,
    action_description: str,
    action_type: str,
    tool_name: str,
    tool_args: dict,
    user_id: str,
    db: AsyncSession,
) -> str:
    request_id = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=APPROVAL_EXPIRY_HOURS)

    approval = HumanApprovalRequest(
        id=request_id,
        agent_id=agent_id,
        run_id=run_id,
        user_id=user_id,
        action_description=action_description,
        action_type=action_type,
        tool_name=tool_name,
        tool_args=tool_args,
        status="pending",
        expires_at=expires_at,
    )

    db.add(approval)
    await db.flush()

    logger.info(
        f"Approval requested: {request_id} | tool={tool_name} | "
        f"action={action_type} | user={user_id} | expires={expires_at.isoformat()}"
    )

    try:
        await _notify_approvers(approval, db)
    except Exception as e:
        logger.warning(f"Failed to notify approvers for {request_id}: {e}")

    return request_id


async def _notify_approvers(approval: HumanApprovalRequest, db: AsyncSession):
    try:
        from app.services.notification_sender import send_notification
        await send_notification(
            user_id=approval.user_id,
            title=f"Approval required: {approval.action_type}",
            body=f"{approval.action_description}\n\nRequest ID: {approval.id}",
            category="approval_required",
            metadata={"approval_request_id": approval.id},
            db=db,
        )
    except (ImportError, AttributeError):
        logger.info(f"Notification service not available — approval {approval.id} stored without push notification")


async def check_approval(request_id: str, db: AsyncSession) -> str:
    result = await db.execute(
        select(HumanApprovalRequest).where(HumanApprovalRequest.id == request_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        return "not_found"

    if approval.status != "pending":
        return approval.status

    if approval.expires_at and approval.expires_at < datetime.now(timezone.utc):
        approval.status = "expired"
        await db.flush()
        return "expired"

    return "pending"


async def approve_action(request_id: str, approver_id: str, db: AsyncSession):
    result = await db.execute(
        select(HumanApprovalRequest).where(HumanApprovalRequest.id == request_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise ValueError(f"Approval request {request_id} not found")
    if approval.status != "pending":
        raise ValueError(f"Approval request {request_id} is already {approval.status}")

    approval.status = "approved"
    approval.approver_id = approver_id
    approval.approved_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"Approval {request_id} approved by {approver_id}")
    return {
        "request_id": request_id,
        "status": "approved",
        "approved_by": approver_id,
        "approved_at": approval.approved_at.isoformat(),
    }


async def reject_action(request_id: str, approver_id: str, reason: str, db: AsyncSession):
    result = await db.execute(
        select(HumanApprovalRequest).where(HumanApprovalRequest.id == request_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise ValueError(f"Approval request {request_id} not found")
    if approval.status != "pending":
        raise ValueError(f"Approval request {request_id} is already {approval.status}")

    approval.status = "rejected"
    approval.approver_id = approver_id
    approval.rejection_reason = reason
    approval.approved_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"Approval {request_id} rejected by {approver_id}: {reason}")
    return {
        "request_id": request_id,
        "status": "rejected",
        "rejected_by": approver_id,
        "reason": reason,
    }
