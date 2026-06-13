from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.agent import HumanApprovalRequest

router = APIRouter()


class ApproveRequest(BaseModel):
    approver_id: Optional[str] = None


class RejectRequest(BaseModel):
    approver_id: Optional[str] = None
    reason: str = ""


def _extract_user_id(current_user: dict) -> str:
    user_email = current_user.get("email") or ""
    return user_email or current_user.get("sub", "").split("|")[-1]


@router.get("/pending")
async def list_pending_approvals(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _extract_user_id(current_user)

    result = await db.execute(
        select(HumanApprovalRequest)
        .where(HumanApprovalRequest.status == "pending")
        .order_by(HumanApprovalRequest.created_at.desc())
        .limit(50)
    )
    approvals = list(result.scalars().all())

    return {
        "success": True,
        "total": len(approvals),
        "approvals": [
            {
                "id": a.id,
                "agent_id": a.agent_id,
                "run_id": a.run_id,
                "user_id": a.user_id,
                "action_description": a.action_description,
                "action_type": a.action_type,
                "tool_name": a.tool_name,
                "tool_args": a.tool_args,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
            for a in approvals
        ],
    }


@router.post("/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    body: ApproveRequest = ApproveRequest(),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"])),
):
    from app.services.human_approval import approve_action

    approver_id = body.approver_id or _extract_user_id(current_user)

    try:
        result = await approve_action(approval_id, approver_id, db)
        await db.commit()
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/reject")
async def reject_approval(
    approval_id: str,
    body: RejectRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"])),
):
    from app.services.human_approval import reject_action

    approver_id = body.approver_id or _extract_user_id(current_user)

    try:
        result = await reject_action(approval_id, approver_id, body.reason, db)
        await db.commit()
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
async def approval_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
):
    result = await db.execute(
        select(HumanApprovalRequest)
        .order_by(HumanApprovalRequest.created_at.desc())
        .limit(limit)
    )
    approvals = list(result.scalars().all())

    return {
        "success": True,
        "total": len(approvals),
        "approvals": [
            {
                "id": a.id,
                "agent_id": a.agent_id,
                "run_id": a.run_id,
                "user_id": a.user_id,
                "action_description": a.action_description,
                "action_type": a.action_type,
                "tool_name": a.tool_name,
                "status": a.status,
                "approver_id": a.approver_id,
                "approved_at": a.approved_at.isoformat() if a.approved_at else None,
                "rejection_reason": a.rejection_reason,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in approvals
        ],
    }
