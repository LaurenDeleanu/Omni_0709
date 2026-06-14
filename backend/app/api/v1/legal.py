from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.legal import WhistleblowerReport, DSARTicket, Contract
from app.services.contract_lifecycle import (
    renew_contract,
    get_contract_timeline,
    get_contract_stats,
)

router = APIRouter()

class ReportCreate(BaseModel):
    title: str
    description: str
    category: str
    is_anonymous: bool = True

class ReportUpdateStatus(BaseModel):
    status: str # open, investigating, resolved
    resolution_message: Optional[str] = None

class DSARCreate(BaseModel):
    request_type: str # download_data, delete_data
    details: Optional[str] = None

@router.post("/whistleblower", status_code=status.HTTP_201_CREATED)
async def create_whistleblower_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    # This endpoint is accessible to any authenticated employee
    new_report = WhistleblowerReport(
        id=uuid.uuid4().hex,
        title=report_in.title,
        description=report_in.description,
        category=report_in.category,
        is_anonymous=report_in.is_anonymous
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    
    return {
        "message": "Report submitted securely.",
        "tracking_code": new_report.tracking_code
    }

@router.get("/whistleblower")
async def get_whistleblower_reports(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    result = await db.execute(select(WhistleblowerReport).order_by(WhistleblowerReport.created_at.desc()))
    reports = result.scalars().all()
    return reports

@router.put("/whistleblower/{report_id}/status")
async def update_report_status(
    report_id: str,
    status_in: ReportUpdateStatus,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    result = await db.execute(select(WhistleblowerReport).where(WhistleblowerReport.id == report_id))
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if status_in.status not in ["open", "investigating", "resolved"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    report.status = status_in.status
    if status_in.resolution_message is not None:
        report.resolution_message = status_in.resolution_message
    await db.commit()
    
    return {"message": "Status updated"}

@router.get("/whistleblower/track/{tracking_code}")
async def track_whistleblower_report(
    tracking_code: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    # This endpoint is accessible to any user with the tracking code
    result = await db.execute(select(WhistleblowerReport).where(WhistleblowerReport.tracking_code == tracking_code))
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="No report found with this tracking code")
        
    return report

@router.post("/dsar", status_code=status.HTTP_201_CREATED)
async def create_dsar_ticket(
    request_in: DSARCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    if request_in.request_type not in ["download_data", "delete_data"]:
        raise HTTPException(status_code=400, detail="Invalid request type")
        
    employee_id = current_user.get("sub", current_user.get("user_id", "unknown"))
    employee_name = current_user.get("email", current_user.get("name", "Unknown"))
    
    new_ticket = DSARTicket(
        id=uuid.uuid4().hex,
        employee_id=employee_id,
        employee_name=employee_name,
        request_type=request_in.request_type,
        details=request_in.details
    )
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)
    return {"message": "Data request submitted successfully", "ticket_id": new_ticket.id}

@router.get("/dsar")
async def get_dsar_tickets(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    result = await db.execute(select(DSARTicket).order_by(DSARTicket.created_at.desc()))
    return result.scalars().all()

@router.put("/dsar/{ticket_id}/status")
async def update_dsar_status(
    ticket_id: str,
    status_in: ReportUpdateStatus, # We can reuse this model since it just needs 'status'
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    result = await db.execute(select(DSARTicket).where(DSARTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket.status = status_in.status
    await db.commit()
    return {"message": "DSAR status updated"}

class RenewContractRequest(BaseModel):
    new_end_date: str

@router.post("/contracts/{contract_id}/renew")
async def renew_contract_endpoint(
    contract_id: str,
    body: RenewContractRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    try:
        result = await renew_contract(contract_id, body.new_end_date, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result

@router.get("/contracts/{contract_id}/timeline")
async def contract_timeline(
    contract_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager", "employee"]))
):
    timeline = await get_contract_timeline(contract_id, db)
    return {"contract_id": contract_id, "events": timeline}

@router.get("/contracts/stats")
async def contract_stats_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    stats = await get_contract_stats("default", db)
    return stats

@router.get("/contracts/expiring")
async def expiring_contracts(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    result = await db.execute(
        select(Contract)
        .where(
            Contract.status == "active",
            Contract.valid_until.isnot(None),
            Contract.valid_until <= cutoff,
            Contract.valid_until > func.now(),
        )
        .order_by(Contract.valid_until.asc())
    )
    contracts = result.scalars().all()
    return contracts


@router.post("/contracts/trigger-alerts")
async def trigger_contract_alerts(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    """
    Manually trigger the contract expiry check and send alert notifications/emails.
    """
    from app.services.contract_lifecycle import send_expiry_alerts
    result = await send_expiry_alerts(db)
    return result


class ComplianceAuditCreate(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    frequency: str = "once"
    audit_type: str # GDPR, labor_law, contract_review, FUNDAE, ALL


class ComplianceAuditResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    scheduled_at: datetime
    frequency: str
    status: str
    audit_type: str
    report_summary: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/compliance-audits", response_model=ComplianceAuditResponse, status_code=201)
async def schedule_compliance_audit(
    payload: ComplianceAuditCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    """
    Schedule an automated compliance audit.
    """
    audit = ComplianceAudit(
        id=uuid.uuid4().hex,
        title=payload.title,
        description=payload.description,
        scheduled_at=payload.scheduled_at,
        frequency=payload.frequency,
        audit_type=payload.audit_type,
        status="scheduled"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit


@router.get("/compliance-audits", response_model=List[ComplianceAuditResponse])
async def list_compliance_audits(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    """
    List all scheduled and completed compliance audits.
    """
    result = await db.execute(select(ComplianceAudit).order_by(ComplianceAudit.created_at.desc()))
    return result.scalars().all()


@router.get("/compliance-audits/{audit_id}", response_model=ComplianceAuditResponse)
async def get_compliance_audit(
    audit_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    """
    Get details and report findings of a specific compliance audit.
    """
    result = await db.execute(select(ComplianceAudit).where(ComplianceAudit.id == audit_id))
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Compliance audit not found")
    return audit


@router.post("/compliance-audits/{audit_id}/execute")
async def execute_compliance_audit(
    audit_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin", "legal_manager"]))
):
    """
    Manually execute a compliance audit immediately and run automated checks.
    """
    from app.services.compliance_audit import run_compliance_check
    try:
        findings = await run_compliance_check(db, audit_id)
        return findings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

