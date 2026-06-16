import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.approval import Approval
from app.models.notification import Notification

router = APIRouter()

class ApprovalResolveIn(BaseModel):
    action: str # "APPROVED" or "REJECTED"
    resolution_notes: Optional[str] = None
    approver_id: Optional[str] = None

class ApprovalCreateIn(BaseModel):
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: str
    requested_by: str
    context_data: dict = {}
    timeout_hours: Optional[int] = 24

def _extract_user_id(current_user: dict) -> str:
    user_email = current_user.get("email") or ""
    return user_email or current_user.get("sub", "").split("|")[-1]

@router.get("/pending")
async def list_pending_approvals(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user.get("tenant_id", "default")
    result = await db.execute(
        select(Approval)
        .where(Approval.status == "PENDING", Approval.tenant_id == tenant_id)
        .order_by(Approval.created_at.desc())
        .limit(50)
    )
    approvals = result.scalars().all()
    return {"success": True, "total": len(approvals), "approvals": [a.to_dict() for a in approvals]}

@router.get("/history")
async def approval_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "manager", "hr_admin", "sys_admin"]))
):
    tenant_id = current_user.get("tenant_id", "default")
    result = await db.execute(
        select(Approval)
        .where(Approval.tenant_id == tenant_id)
        .order_by(Approval.created_at.desc())
        .limit(limit)
    )
    approvals = result.scalars().all()
    return {"success": True, "total": len(approvals), "approvals": [a.to_dict() for a in approvals]}

@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "manager", "hr_admin", "sys_admin"]))
):
    tenant_id = current_user.get("tenant_id", "default")
    result = await db.execute(select(Approval).where(Approval.id == approval_id, Approval.tenant_id == tenant_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval.to_dict()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_approval(
    body: ApprovalCreateIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["system", "hr_admin", "sys_admin"]))
):
    from datetime import timedelta
    tenant_id = current_user.get("tenant_id", "default")
    
    approval = Approval(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        workflow_id=body.workflow_id,
        agent_id=body.agent_id,
        run_id=body.run_id,
        requested_by=body.requested_by,
        context_data=body.context_data,
        status="PENDING"
    )
    if body.timeout_hours:
        approval.timeout_at = datetime.now(timezone.utc) + timedelta(hours=body.timeout_hours)
        
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    try:
        from app.services.email_service import send_email
        admin_email = "admin@example.com" # TODO: Real routing
        subject = f"Action Required: Approval Request {approval.id[:8]}"
        content = f"A new workflow/agent action requires your approval.\n\nContext:\n{body.context_data}"
        await send_email(admin_email, subject, content)
        
        widget_notif = Notification(
            id=uuid.uuid4().hex,
            tenant_id=tenant_id,
            user_id="SYSTEM",
            title="Pending Approval",
            message=subject,
            type="APPROVAL_REQUIRED",
            reference_id=approval.id,
            reference_type="approval",
            is_read=False
        )
        db.add(widget_notif)
        await db.commit()
    except Exception as e:
        pass

    return approval.to_dict()

@router.post("/{approval_id}/resolve")
async def resolve_approval(
    approval_id: str,
    body: ApprovalResolveIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["manager", "hr_admin", "sys_admin"]))
):
    tenant_id = current_user.get("tenant_id", "default")
    result = await db.execute(select(Approval).where(Approval.id == approval_id, Approval.tenant_id == tenant_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    if approval.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Approval is already resolved: {approval.status}")
        
    if body.action not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    approval.status = body.action
    approval.resolution_notes = body.resolution_notes
    approval.approved_by = body.approver_id or _extract_user_id(current_user)
    approval.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(approval)
    return {"success": True, "approval": approval.to_dict()}
