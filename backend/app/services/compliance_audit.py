import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.legal import ComplianceAudit, Contract, DSARTicket
from app.models.finance import TimeLog
from app.models.training import CourseEnrollment

logger = logging.getLogger("successcore.compliance_audit")

async def run_compliance_check(db: AsyncSession, audit_id: str) -> Dict[str, Any]:
    """
    Executes automated compliance checks for a scheduled audit and updates its status and findings.
    """
    result = await db.execute(select(ComplianceAudit).where(ComplianceAudit.id == audit_id))
    audit = result.scalar_one_or_none()
    if not audit:
        raise ValueError("Compliance audit not found")
        
    audit.status = "in_progress"
    await db.commit()
    
    findings = []
    has_issues = False
    
    # ── 1. Contract Review ──
    if audit.audit_type in ["contract_review", "ALL"]:
        cutoff = datetime.now(timezone.utc) + timedelta(days=30)
        contract_res = await db.execute(
            select(Contract)
            .where(
                Contract.status == "active",
                Contract.valid_until.isnot(None),
                Contract.valid_until <= cutoff,
                Contract.valid_until > func.now(),
            )
            .order_by(Contract.valid_until.asc())
        )
        expiring = contract_res.scalars().all()
        if expiring:
            findings.append({
                "check": "Expiring Contracts",
                "status": "warning",
                "detail": f"Found {len(expiring)} active contract(s) expiring within 30 days.",
                "items": [{"id": c.id, "title": c.title, "party_name": c.party_name, "valid_until": c.valid_until.isoformat()} for c in expiring]
            })
        else:
            findings.append({
                "check": "Expiring Contracts",
                "status": "passed",
                "detail": "No active contracts expiring within 30 days."
            })
            
    # ── 2. GDPR DSAR Checks ──
    if audit.audit_type in ["GDPR", "ALL"]:
        limit_date = datetime.now(timezone.utc) - timedelta(days=30)
        dsar_res = await db.execute(
            select(DSARTicket).where(
                DSARTicket.status == "pending",
                DSARTicket.created_at < limit_date
            )
        )
        delayed_dsar = dsar_res.scalars().all()
        if delayed_dsar:
            has_issues = True
            findings.append({
                "check": "GDPR DSAR SLA",
                "status": "failed",
                "detail": f"Found {len(delayed_dsar)} pending DSAR ticket(s) exceeding 30-day processing limit.",
                "items": [{"id": t.id, "employee_name": t.employee_name, "request_type": t.request_type, "created_at": t.created_at.isoformat()} for t in delayed_dsar]
            })
        else:
            findings.append({
                "check": "GDPR DSAR SLA",
                "status": "passed",
                "detail": "All pending DSAR tickets are within the 30-day resolution window."
            })
            
    # ── 3. Labor Law Working Hours Check ──
    if audit.audit_type in ["labor_law", "ALL"]:
        # Spain/EU daily work hour limits: flag if employee clocked >10 hours in a day
        limit_date = datetime.now(timezone.utc) - timedelta(days=30)
        logs_res = await db.execute(
            select(TimeLog)
            .where(
                TimeLog.clock_in >= limit_date,
                TimeLog.clock_out.isnot(None)
            )
            .options(selectinload(TimeLog.user))
        )
        logs = logs_res.scalars().all()
        violations = []
        for log in logs:
            dt_in = log.clock_in
            dt_out = log.clock_out
            if dt_in.tzinfo != dt_out.tzinfo:
                dt_in = dt_in.replace(tzinfo=None)
                dt_out = dt_out.replace(tzinfo=None)
            hours = (dt_out - dt_in).total_seconds() / 3600.0
            if hours > 10.0:
                violations.append({
                    "log_id": log.id,
                    "user_id": log.user_id,
                    "employee_name": log.user.full_name if log.user else "Unknown",
                    "date": log.clock_in.date().isoformat(),
                    "hours_worked": round(hours, 2)
                })
        if violations:
            findings.append({
                "check": "Labor Law: Daily Hours Limit",
                "status": "warning",
                "detail": f"Detected {len(violations)} day(s) where employees clocked >10 hours.",
                "items": violations[:10]
            })
        else:
            findings.append({
                "check": "Labor Law: Daily Hours Limit",
                "status": "passed",
                "detail": "No daily working hours limit violations (>10h) detected in the last 30 days."
            })
            
    # ── 4. FUNDAE Training Audit ──
    if audit.audit_type in ["FUNDAE", "ALL"]:
        fundae_res = await db.execute(
            select(CourseEnrollment)
            .where(
                CourseEnrollment.status == "completed",
                CourseEnrollment.score.is_(None)
            )
            .options(selectinload(CourseEnrollment.user), selectinload(CourseEnrollment.course))
        )
        invalid_enrollments = fundae_res.scalars().all()
        if invalid_enrollments:
            findings.append({
                "check": "FUNDAE: Missing Assessment Scores",
                "status": "warning",
                "detail": f"Found {len(invalid_enrollments)} completed courses missing score values required for state funding subsidies.",
                "items": [{"id": e.id, "employee_name": e.user.full_name if e.user else "Unknown", "course_title": e.course.title if e.course else "Unknown"} for e in invalid_enrollments]
            })
        else:
            findings.append({
                "check": "FUNDAE: Missing Assessment Scores",
                "status": "passed",
                "detail": "All completed courses contain scores for FUNDAE validations."
            })
            
    # Determine overall audit result status
    audit.status = "failed" if has_issues else "completed"
    audit_summary = {
        "audit_id": audit.id,
        "title": audit.title,
        "type": audit.audit_type,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "summary": "Completed with warnings/failures" if has_issues else "Completed successfully",
        "findings": findings
    }
    audit.report_summary = json.dumps(audit_summary, default=str)
    
    await db.commit()
    await db.refresh(audit)
    
    return audit_summary
