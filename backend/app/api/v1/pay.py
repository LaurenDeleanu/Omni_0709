from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio

from app.api.dependencies import get_tenant_db, require_super_admin, get_current_user, require_roles
from app.models.pay import PayrollCycle, Payslip, TaxRule, PayslipLineItem, Bonus
from app.models.finance import WorkSchedule, TimeLog, BreakLog
from app.models.user import User
from app.models.notification import Notification
from app.core.tax_seeder import seed_tax_brackets
from app.core.redis import get_redis
from app.core.logger import logger
import uuid

router = APIRouter()

# --- Schemas ---

class PayrollCycleCreate(BaseModel):
    period_name: str
    start_date: datetime
    end_date: datetime

class PayrollCycleResponse(PayrollCycleCreate):
    id: str
    status: str
    total_gross: float
    total_net: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class PayslipResponse(BaseModel):
    id: str
    cycle_id: str
    employee_id: str
    gross_salary: float
    deductions: float
    net_salary: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PayslipLineItemResponse(BaseModel):
    id: str
    description: str
    amount: float
    type: str

    class Config:
        from_attributes = True

class PayslipDetailResponse(PayslipResponse):
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    line_items: List[PayslipLineItemResponse] = []

class TaxRuleSchema(BaseModel):
    id: str
    country_code: str
    name: str
    calculation_type: str
    rate: float
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    is_deduction: bool
    is_marginal: bool

    class Config:
        from_attributes = True

class TaxRuleUpdate(BaseModel):
    name: Optional[str] = None
    rate: Optional[float] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None

class EmployeeCompensationSchema(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    department: Optional[str] = None
    base_salary: float
    country: str

    class Config:
        from_attributes = True

class EmployeeCompensationUpdate(BaseModel):
    base_salary: Optional[float] = None
    country: Optional[str] = None

class CycleStatusUpdate(BaseModel):
    status: str

class BonusSchema(BaseModel):
    id: str
    employee_id: str
    amount: float
    description: str
    type: str
    status: str
    payslip_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BonusCreate(BaseModel):
    amount: float
    description: str
    type: str # 'standard' or 'kpi'

# --- Helpers ---

def get_user_id(current_user: dict) -> str:
    sub = current_user.get("sub", "")
    return sub.split("|")[-1] if "|" in sub else sub

# --- Endpoints ---

@router.get("/my-payslips", response_model=List[PayslipResponse])
async def get_my_payslips(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener los recibos de nómina del usuario autenticado."""
    user_id = get_user_id(current_user)
    result = await db.execute(
        select(Payslip).where(
            Payslip.employee_id == user_id,
            Payslip.status == "finalized"
        ).order_by(Payslip.id.desc())
    )
    return result.scalars().all()

@router.get("/payslips/{payslip_id}/pdf")
async def get_payslip_pdf(
    payslip_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Generar y descargar el recibo de salario (payslip) en formato PDF."""
    user_id = get_user_id(current_user)
    
    # Obtener el recibo de nómina
    result = await db.execute(
        select(Payslip).where(Payslip.id == payslip_id)
    )
    payslip = result.scalar_one_or_none()
    if not payslip:
        raise HTTPException(status_code=404, detail="Recibo de nómina no encontrado")
        
    # Verificar que pertenezca al usuario o que sea HR admin
    if "hr_admin" not in current_user.get("roles", []) and payslip.employee_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver esta nómina")
        
    # Obtener detalles del empleado
    u_res = await db.execute(select(User).where(User.id == payslip.employee_id))
    user = u_res.scalar_one_or_none()
    employee_name = user.full_name if user and user.full_name else (user.email if user else "Empleado")
    
    # Obtener el ciclo para sacar el nombre del periodo
    c_res = await db.execute(select(PayrollCycle).where(PayrollCycle.id == payslip.cycle_id))
    cycle = c_res.scalar_one_or_none()
    period = cycle.period_name if cycle else "Desconocido"
    
    # Obtener el nombre del tenant para la cabecera
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_name = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "Mi Empresa"
    tenant_name = tenant_name.upper()
    
    payslip_dict = {
        "employee_id": payslip.employee_id,
        "gross_salary": payslip.gross_salary,
        "deductions": payslip.deductions,
        "net_salary": payslip.net_salary
    }
    
    from app.services.pdf_service import generate_payslip_pdf
    pdf_bytes = generate_payslip_pdf(tenant_name, employee_name, period, payslip_dict)
    
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=nominas_{period.replace(' ', '_')}_{payslip_id}.pdf"
        }
    )

@router.get("/cycles", response_model=List[PayrollCycleResponse])
async def get_cycles(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(PayrollCycle).order_by(PayrollCycle.created_at.desc()))
    return result.scalars().all()

@router.post("/cycles", response_model=PayrollCycleResponse)
async def create_cycle(
    data: PayrollCycleCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    db_cycle = PayrollCycle(**data.model_dump())
    db.add(db_cycle)
    await db.commit()
    await db.refresh(db_cycle)
    return db_cycle

@router.patch("/cycles/{cycle_id}/status")
async def update_cycle_status(
    cycle_id: str,
    payload: CycleStatusUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(PayrollCycle).where(PayrollCycle.id == cycle_id))
    cycle = result.scalars().first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    cycle.status = payload.status
    
    # Also update all payslips
    payslip_result = await db.execute(select(Payslip).where(Payslip.cycle_id == cycle_id))
    payslips = payslip_result.scalars().all()
    for payslip in payslips:
        if payload.status == "paid":
            payslip.status = "finalized"
            notification = Notification(
                id=uuid.uuid4().hex,
                user_id=payslip.employee_id,
                title="💵 Nómina disponible",
                message=f"Tu nómina correspondiente al periodo '{cycle.period_name}' ya está disponible para ver y descargar.",
                type="payroll",
                is_read=False
            )
            db.add(notification)
    
    # SAP FI integration: generate Journal Entry on payroll payment
    if payload.status == "paid" and cycle.total_gross > 0:
        from app.models.finance import JournalEntry, JournalLine
        
        ref = f"PAY-{cycle.id}"
        exist_result = await db.execute(select(JournalEntry).where(JournalEntry.reference == ref))
        existing_entry = exist_result.scalar_one_or_none()
        if not existing_entry:
            total_gross = float(cycle.total_gross)
            total_net = float(cycle.total_net)
            total_deductions = total_gross - total_net
            
            entry = JournalEntry(
                id=uuid.uuid4().hex,
                reference=ref,
                date=datetime.now().date(),
                description=f"Cierre Nómina Periodo: {cycle.period_name}"
            )
            db.add(entry)
            
            # Debit Line (640000 Sueldos y Salarios)
            db.add(JournalLine(
                id=uuid.uuid4().hex,
                entry_id=entry.id,
                account_code="640000",
                account_name="Sueldos y Salarios",
                debit=total_gross,
                credit=0.0
            ))
            
            # Credit Line (475100 Hacienda Pública Acreedora por Retenciones)
            if total_deductions > 0:
                db.add(JournalLine(
                    id=uuid.uuid4().hex,
                    entry_id=entry.id,
                    account_code="475100",
                    account_name="Hacienda Pública Acreedora por Retenciones",
                    debit=0.0,
                    credit=total_deductions
                ))
            
            # Credit Line (465000 Remuneraciones Pendientes de Pago)
            db.add(JournalLine(
                id=uuid.uuid4().hex,
                entry_id=entry.id,
                account_code="465000",
                account_name="Remuneraciones Pendientes de Pago",
                debit=0.0,
                credit=total_net
            ))

    await db.commit()
    return {"message": "Cycle status updated successfully"}

@router.get("/cycles/{cycle_id}/payslips", response_model=List[PayslipDetailResponse])
async def get_cycle_payslips(
    cycle_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(
        select(Payslip).where(Payslip.cycle_id == cycle_id)
        .options(selectinload(Payslip.employee), selectinload(Payslip.line_items))
    )
    payslips = result.scalars().all()
    
    response = []
    for p in payslips:
        resp_dict = {
            "id": p.id,
            "cycle_id": p.cycle_id,
            "employee_id": p.employee_id,
            "gross_salary": p.gross_salary,
            "deductions": p.deductions,
            "net_salary": p.net_salary,
            "status": p.status,
            "created_at": p.created_at,
            "employee_name": p.employee.full_name if p.employee and p.employee.full_name else (p.employee.email if p.employee else "Unknown"),
            "employee_email": p.employee.email if p.employee else "Unknown",
            "line_items": p.line_items
        }
        response.append(PayslipDetailResponse(**resp_dict))
    
    return response

@router.post("/cycles/seed_taxes")
async def seed_taxes(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    return await seed_tax_brackets(db)

def _extract_tenant_schema(db: AsyncSession) -> str:
    exec_opts = db.get_bind().get_execution_options()
    translate_map = exec_opts.get("schema_translate_map", {})
    return translate_map.get(None, "public")


def _rules_to_dicts(all_rules) -> List[Dict[str, Any]]:
    return [
        {
            "country_code": r.country_code,
            "name": r.name,
            "calculation_type": r.calculation_type,
            "rate": r.rate,
            "min_salary": r.min_salary,
            "max_salary": r.max_salary,
            "is_deduction": r.is_deduction,
            "is_marginal": r.is_marginal,
        }
        for r in all_rules
    ]


def _calculate_overtime_earnings(
    time_logs, cycle_start_date, cycle_end_date, annual_salary
) -> float:
    actual_hours = 0.0
    for log in time_logs:
        if log.clock_out:
            dt_in = log.clock_in
            dt_out = log.clock_out
            if dt_in.tzinfo != dt_out.tzinfo:
                dt_in = dt_in.replace(tzinfo=None)
                dt_out = dt_out.replace(tzinfo=None)
            log_hours = (dt_out - dt_in).total_seconds() / 3600.0
            actual_hours += log_hours

    expected_hours = 0.0
    curr_date = cycle_start_date.date() if isinstance(cycle_start_date, datetime) else cycle_start_date
    end_date = cycle_end_date.date() if isinstance(cycle_end_date, datetime) else cycle_end_date
    while curr_date <= end_date:
        dow = curr_date.weekday()
        if dow < 5:
            expected_hours += 8.0
        curr_date += timedelta(days=1)

    overtime_hours = max(0.0, actual_hours - expected_hours)
    if overtime_hours > 0.0 and annual_salary > 0:
        hourly_rate = (annual_salary / 12.0) / 160.0
        return overtime_hours * hourly_rate * 1.5
    return 0.0


async def _calculate_overtime_earnings_full(
    db: AsyncSession, user_id: str, cycle_start_date, cycle_end_date, annual_salary: float
) -> float:
    actual_hours = 0.0

    time_logs_res = await db.execute(
        select(TimeLog).where(
            TimeLog.user_id == user_id,
            TimeLog.clock_in >= cycle_start_date,
            TimeLog.clock_in <= cycle_end_date
        )
    )
    time_logs = time_logs_res.scalars().all()
    for log in time_logs:
        if log.clock_out:
            dt_in = log.clock_in
            dt_out = log.clock_out
            if dt_in.tzinfo != dt_out.tzinfo:
                dt_in = dt_in.replace(tzinfo=None)
                dt_out = dt_out.replace(tzinfo=None)
            log_hours = (dt_out - dt_in).total_seconds() / 3600.0

            breaks_res = await db.execute(select(BreakLog).where(BreakLog.time_log_id == log.id))
            breaks = breaks_res.scalars().all()
            break_hours = 0.0
            for b in breaks:
                if b.end_time:
                    b_start = b.start_time
                    b_end = b.end_time
                    if b_start.tzinfo != b_end.tzinfo:
                        b_start = b_start.replace(tzinfo=None)
                        b_end = b_end.replace(tzinfo=None)
                    break_hours += (b_end - b_start).total_seconds() / 3600.0
            actual_hours += max(0.0, log_hours - break_hours)

    expected_hours = 0.0
    sched_res = await db.execute(select(WorkSchedule).where(WorkSchedule.user_id == user_id))
    schedules = {s.day_of_week: s for s in sched_res.scalars().all()}

    curr_date = cycle_start_date.date() if isinstance(cycle_start_date, datetime) else cycle_start_date
    end_date = cycle_end_date.date() if isinstance(cycle_end_date, datetime) else cycle_end_date
    while curr_date <= end_date:
        dow = curr_date.weekday()
        if dow in schedules:
            s = schedules[dow]
            try:
                sh, sm = map(int, s.start_time.split(":"))
                eh, em = map(int, s.end_time.split(":"))
                daily_hours = (eh + em/60.0) - (sh + sm/60.0)
                if daily_hours > 1.0:
                    daily_hours -= 1.0
                expected_hours += max(0.0, daily_hours)
            except Exception:
                expected_hours += 8.0
        else:
            if dow < 5:
                expected_hours += 8.0
        curr_date += timedelta(days=1)

    overtime_hours = max(0.0, actual_hours - expected_hours)
    if overtime_hours > 0.0 and annual_salary > 0:
        hourly_rate = (annual_salary / 12.0) / 160.0
        return overtime_hours * hourly_rate * 1.5
    return 0.0


async def _process_single_employee(
    tenant_schema: str,
    user_id: str,
    cycle_id: str,
    cycle_start_date,
    cycle_end_date,
    rules_dicts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    sessionmaker = _get_or_create_sessionmaker(tenant_schema)
    async with sessionmaker() as local_db:
        try:
            user_res = await local_db.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            if not user:
                logger.warning(f"Employee {user_id} not found in tenant schema, skipping")
                return {"user_id": user_id, "gross": 0.0, "net": 0.0, "failed": True, "error": "User not found"}

            annual_salary = user.base_salary if hasattr(user, 'base_salary') and user.base_salary else 50000.0
            country = user.country if hasattr(user, 'country') and user.country else "ES"
            monthly_gross = annual_salary / 12.0

            bonuses_result = await local_db.execute(
                select(Bonus).where(Bonus.employee_id == user.id, Bonus.status == "pending")
            )
            user_bonuses = bonuses_result.scalars().all()
            total_bonus_amount = sum(b.amount for b in user_bonuses)
            monthly_gross += total_bonus_amount

            overtime_earnings = await _calculate_overtime_earnings_full(
                local_db, user_id, cycle_start_date, cycle_end_date, annual_salary
            )
            if overtime_earnings > 0:
                monthly_gross += overtime_earnings

            country_rules = [r for r in rules_dicts if r["country_code"] == country]
            if not country_rules:
                country_rules = [r for r in rules_dicts if r["country_code"] == "ES"]

            line_items = []
            line_items.append(PayslipLineItem(
                id=uuid.uuid4().hex,
                description="Salario Base",
                amount=annual_salary / 12.0,
                type="earning"
            ))

            if overtime_earnings > 0.0:
                overtime_hours = 0.0
                line_items.append(PayslipLineItem(
                    id=uuid.uuid4().hex,
                    description=f"Horas Extras ({overtime_hours:.1f}h a 1.5x)",
                    amount=overtime_earnings,
                    type="earning"
                ))

            for b in user_bonuses:
                line_items.append(PayslipLineItem(
                    id=uuid.uuid4().hex,
                    description=f"Bono ({b.type.upper()}): {b.description}",
                    amount=b.amount,
                    type="earning"
                ))

            from app.services.tax_engines import get_tax_engine
            tax_engine = get_tax_engine(country)
            
            tax_result = tax_engine.calculate_taxes(annual_salary, country_rules)
            annual_tax = tax_result.annual_tax
            
            # Map engine line items to PayslipLineItem models
            for item in tax_result.line_items:
                line_items.append(PayslipLineItem(
                    id=item["id"],
                    description=item["description"],
                    amount=item["amount"],
                    type=item["type"]
                ))

            monthly_deductions = annual_tax / 12.0
            monthly_net = monthly_gross - monthly_deductions

            payslip_id = uuid.uuid4().hex
            payslip = Payslip(
                id=payslip_id,
                cycle_id=cycle_id,
                employee_id=user.id,
                gross_salary=monthly_gross,
                deductions=monthly_deductions,
                net_salary=monthly_net,
                status="draft"
            )
            local_db.add(payslip)

            for li in line_items:
                li.payslip_id = payslip_id
                local_db.add(li)

            for b in user_bonuses:
                b.payslip_id = payslip_id
                b.status = "paid"

            await local_db.commit()
            return {"user_id": user_id, "gross": monthly_gross, "net": monthly_net, "failed": False}

        except Exception as e:
            logger.error(f"Failed to process employee {user_id}: {str(e)}")
            await local_db.rollback()
            return {"user_id": user_id, "gross": 0.0, "net": 0.0, "failed": True, "error": str(e)}


@router.post("/cycles/{cycle_id}/process")
async def process_payroll(
    cycle_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(PayrollCycle).where(PayrollCycle.id == cycle_id))
    cycle = result.scalars().first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    if cycle.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft cycles can be processed")

    users_result = await db.execute(select(User.id, User.base_salary, User.country).where(User.is_active == True))
    user_rows = users_result.all()
    user_ids = [row[0] for row in user_rows]

    rules_result = await db.execute(select(TaxRule))
    all_rules = rules_result.scalars().all()
    rules_dicts = _rules_to_dicts(all_rules)

    tenant_schema = _extract_tenant_schema(db)
    total_employees = len(user_ids)

    r = await get_redis()
    await r.hset(f"payroll:progress:{cycle_id}", mapping={
        "processed": 0,
        "total": total_employees,
        "failed": 0
    })

    BATCH_SIZE = 20
    all_results: List[Dict[str, Any]] = []
    processed_count = 0
    failed_count = 0

    for i in range(0, total_employees, BATCH_SIZE):
        batch_ids = user_ids[i:i + BATCH_SIZE]

        tasks = [
            _process_single_employee(
                tenant_schema=tenant_schema,
                user_id=uid,
                cycle_id=cycle_id,
                cycle_start_date=cycle.start_date,
                cycle_end_date=cycle.end_date,
                rules_dicts=rules_dicts,
            )
            for uid in batch_ids
        ]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in batch_results:
            if isinstance(res, Exception):
                logger.error(f"Unhandled exception in batch: {str(res)}")
                failed_count += 1
                processed_count += 1
                all_results.append({"gross": 0.0, "net": 0.0, "failed": True})
            else:
                all_results.append(res)
                if res.get("failed"):
                    failed_count += 1
                processed_count += 1

        await r.hset(f"payroll:progress:{cycle_id}", mapping={
            "processed": processed_count,
            "total": total_employees,
            "failed": failed_count
        })

    total_gross = sum(r.get("gross", 0.0) or 0.0 for r in all_results)
    total_net = sum(r.get("net", 0.0) or 0.0 for r in all_results)

    cycle.status = "processing"
    cycle.total_gross = total_gross
    cycle.total_net = total_net
    await db.commit()

    await r.hset(f"payroll:progress:{cycle_id}", mapping={
        "processed": processed_count,
        "total": total_employees,
        "failed": failed_count
    })

    return {
        "message": f"Processed {total_employees - failed_count}/{total_employees} employees",
        "total_processed": total_employees - failed_count,
        "failed": failed_count,
        "total_gross": total_gross,
        "total_net": total_net
    }

# --- Admin Management Endpoints ---

@router.get("/rules", response_model=List[TaxRuleSchema])
async def get_tax_rules(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(TaxRule).order_by(TaxRule.country_code, TaxRule.min_salary))
    return result.scalars().all()

@router.put("/rules/{rule_id}", response_model=TaxRuleSchema)
async def update_tax_rule(
    rule_id: str,
    payload: TaxRuleUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(TaxRule).where(TaxRule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Tax rule not found")
        
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
        
    await db.commit()
    await db.refresh(rule)
    return rule

@router.get("/employees/{employee_id}/bonuses", response_model=List[BonusSchema])
async def get_employee_bonuses(
    employee_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)
    user_roles = current_user.get("roles", []) or current_user.get("https://successcore.com/roles", [])
    is_hr_admin = "hr_admin" in user_roles

    if not is_hr_admin and employee_id != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own bonuses")

    result = await db.execute(select(Bonus).where(Bonus.employee_id == employee_id).order_by(Bonus.created_at.desc()))
    return result.scalars().all()


@router.post("/employees/{employee_id}/bonuses", response_model=BonusSchema)
async def create_employee_bonus(
    employee_id: str,
    data: BonusCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))
):
    db_bonus = Bonus(**data.model_dump(), employee_id=employee_id, status="pending")
    db.add(db_bonus)
    await db.commit()
    await db.refresh(db_bonus)
    return db_bonus


@router.delete("/bonuses/{bonus_id}")
async def delete_bonus(
    bonus_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))
):
    result = await db.execute(select(Bonus).where(Bonus.id == bonus_id))
    bonus = result.scalars().first()
    if not bonus:
        raise HTTPException(status_code=404, detail="Bonus not found")
    if bonus.status != "pending":
        raise HTTPException(status_code=400, detail="Cannot delete a paid bonus")
    await db.delete(bonus)
    await db.commit()
    return {"ok": True}

@router.get("/employees/compensation", response_model=List[EmployeeCompensationSchema])
async def get_employees_compensation(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(User).where(User.is_active == True).order_by(User.full_name))
    users = result.scalars().all()
    
    # Map to schema (handling missing attributes via default fallbacks)
    comps = []
    for u in users:
        comps.append(EmployeeCompensationSchema(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            department=u.department,
            base_salary=u.base_salary if hasattr(u, 'base_salary') and u.base_salary else 50000.0,
            country=u.country if hasattr(u, 'country') and u.country else "ES"
        ))
    return comps

@router.put("/employees/{user_id}/compensation", response_model=EmployeeCompensationSchema)
async def update_employee_compensation(
    user_id: str,
    payload: EmployeeCompensationUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))  # [H3] Auth guard
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if payload.base_salary is not None:
        user.base_salary = payload.base_salary
    if payload.country is not None:
        user.country = payload.country
        
    await db.commit()
    
    return EmployeeCompensationSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        base_salary=user.base_salary,
        country=user.country
    )


@router.get("/payslips/{payslip_id}/explain")
async def get_payslip_explanation(
    payslip_id: str,
    prev_payslip_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate an LLM-based explanation comparing the current payslip to a previous one.
    """
    user_id = get_user_id(current_user)
    
    # Fetch current payslip to check permissions
    result = await db.execute(select(Payslip).where(Payslip.id == payslip_id))
    payslip = result.scalar_one_or_none()
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
        
    user_roles = current_user.get("roles", []) or current_user.get("https://successcore.com/roles", [])
    is_hr_admin = "hr_admin" in user_roles or "admin" in user_roles or "super_admin" in user_roles
    
    if not is_hr_admin and payslip.employee_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this payslip explanation")
        
    from app.services.payroll_intelligence import explain_payslip_differences
    explanation = await explain_payslip_differences(db, payslip.employee_id, payslip_id, prev_payslip_id)
    return {"explanation": explanation}


@router.get("/employees/{employee_id}/tax-optimization")
async def get_employee_tax_optimization(
    employee_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate and return Spanish tax optimization / flexible compensation recommendations.
    """
    user_id = get_user_id(current_user)
    user_roles = current_user.get("roles", []) or current_user.get("https://successcore.com/roles", [])
    is_hr_admin = "hr_admin" in user_roles or "admin" in user_roles or "super_admin" in user_roles
    
    if not is_hr_admin and employee_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this tax optimization")
        
    from app.services.payroll_intelligence import get_tax_optimization_recommendations
    recs = await get_tax_optimization_recommendations(db, employee_id)
    return {"recommendations": recs}


@router.get("/cycles/{cycle_id}/anomalies")
async def get_cycle_anomalies(
    cycle_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "admin"]))
):
    """
    Identify and return anomalies (>15% deviation from historical averages) in draft payslips.
    """
    from app.services.payroll_intelligence import detect_payroll_cycle_anomalies
    anomalies = await detect_payroll_cycle_anomalies(db, cycle_id)
    return {"anomalies": anomalies}


@router.get("/cycles/{cycle_id}/sepa")
async def export_cycle_sepa(
    cycle_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "admin", "payroll_admin"]))
):
    from app.services.sepa_export import generate_salary_sepa_xml
    from app.models.pay import Payslip, PayrollCycle
    from app.models.user import User

    payslips_res = await db.execute(
        select(Payslip).where(Payslip.cycle_id == cycle_id)
    )
    payslips = payslips_res.scalars().all()
    if not payslips:
        raise HTTPException(status_code=404, detail="No payslips found for this cycle")

    employees_pay = []
    for p in payslips:
        u_res = await db.execute(select(User).where(User.id == p.employee_id))
        user = u_res.scalar_one_or_none()
        employees_pay.append({
            "full_name": user.full_name if user and user.full_name else "Employee",
            "iban": getattr(user, "iban", ""),
            "bic": getattr(user, "bic", ""),
            "net_pay": p.net_salary,
            "currency": "EUR",
            "period": f"Cycle {cycle_id[:8]}",
        })

    tenant_id = current_user.get("tenant_id", "default")
    company = {"name": tenant_id.upper(), "tax_id": "", "iban": "", "bic": "", "country": "ES", "address": ""}

    xml_content = generate_salary_sepa_xml(employees_pay, company)

    return Response(
        content=xml_content.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=sepa_salary_{cycle_id[:8]}.xml"}
    )


@router.get("/payslips/{payslip_id}/pdf-professional")
async def get_professional_payslip_pdf(
    payslip_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.payslip_pdf import generate_payslip_pdf as gen_pdf
    from app.models.pay import Payslip, PayrollCycle
    from app.models.user import User

    result = await db.execute(select(Payslip).where(Payslip.id == payslip_id))
    payslip = result.scalar_one_or_none()
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")

    user_id = payslip.employee_id
    if "hr_admin" not in current_user.get("roles", []) and user_id != current_user.get("sub", "").split("|")[-1]:
        raise HTTPException(status_code=403, detail="Access denied")

    u_res = await db.execute(select(User).where(User.id == user_id))
    user = u_res.scalar_one_or_none()

    data = {
        "doc_type": "NÓMINA",
        "language": "es",
        "currency": "EUR",
        "issue_date": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "payslip_id": payslip_id,
        "irpf_rate": 15.0,
        "employee": {
            "full_name": user.full_name if user else "Employee",
            "tax_id": getattr(user, "tax_id", "***"),
            "department": getattr(user, "department", ""),
            "position": getattr(user, "position", ""),
            "category": getattr(user, "category", ""),
            "contribution_group": "1",
            "ss_number": getattr(user, "ss_number", "***"),
            "seniority": "",
            "contract_type": getattr(user, "contract_type", "Indefinido"),
            "workday_type": "Completa",
        },
        "company": {"name": current_user.get("tenant_id", "Company").upper(), "tax_id": "", "address": ""},
        "period": {"label": payslip.period_name or ""},
        "earnings": [
            {"concept": "Salario Base", "amount": payslip.gross_salary},
        ],
        "deductions": [
            {"concept": "IRPF", "rate_pct": 15.0, "amount": payslip.deductions},
        ],
        "totals": {"gross": payslip.gross_salary, "deductions": payslip.deductions, "net": payslip.net_salary},
    }

    pdf_bytes = gen_pdf(data)
    return Response(
        content=pdf_bytes if isinstance(pdf_bytes, bytes) else pdf_bytes.encode("utf-8"),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payslip_{payslip_id[:8]}.pdf"}
    )


@router.get("/siltra/afiliacion")
async def export_siltra_afiliacion(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "admin", "payroll_admin"]))
):
    from app.services.siltra_sepe import generate_siltra_afiliacion_xml
    from app.models.user import User

    employees_res = await db.execute(select(User).where(User.is_active == True).limit(100))
    employees = employees_res.scalars().all()

    emp_data = [{
        "full_name": e.full_name or e.email,
        "tax_id": getattr(e, "tax_id", ""),
        "ss_number": getattr(e, "ss_number", ""),
        "birth_date": getattr(e, "birth_date", ""),
        "hire_date": e.hire_date.isoformat() if getattr(e, "hire_date", None) else "",
        "termination_date": "",
        "contract_type_code": CONTRACT_TYPE_TO_SEPE.get(getattr(e, "contract_type", "indefinido"), "100"),
        "part_time_pct": "100",
        "contribution_group": getattr(e, "contribution_group", "1"),
        "at_code": "",
        "occupation_code": "",
        "last_name1": "",
        "last_name2": "",
    } for e in employees]

    company = {"name": current_user.get("tenant_id", "Company"), "tax_id": "", "ccc": ""}
    xml = generate_siltra_afiliacion_xml(company, emp_data)
    return Response(content=xml.encode("utf-8"), media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename=siltra_afiliacion.xml"})


@router.get("/siltra/cotizacion")
async def export_siltra_cotizacion(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "admin", "payroll_admin"]))
):
    from app.services.siltra_sepe import generate_siltra_cotizacion_xml, calculate_social_security_costs
    from app.models.user import User

    employees_res = await db.execute(select(User).where(User.is_active == True).limit(100))
    employees = employees_res.scalars().all()

    emp_data = []
    for e in employees:
        costs = await calculate_social_security_costs(
            getattr(e, "base_salary", 0) or 1500,
            getattr(e, "contribution_group", "1"),
            getattr(e, "contract_type", "indefinido"),
        )
        emp_data.append({
            "full_name": e.full_name or e.email,
            "ss_number": getattr(e, "ss_number", ""),
            "gross_salary": costs["gross_salary"],
            "cc_base": costs["gross_salary"],
            "cp_base": costs["gross_salary"],
            "unemp_base": costs["gross_salary"],
            "fogasa_base": costs["gross_salary"],
            "fp_base": costs["gross_salary"],
            "employer_cost": costs["total_employer_cost"],
            "employee_cost": costs["total_employee_cost"],
            "overtime_hours": 0,
            "days_worked": 30,
        })

    company = {"name": current_user.get("tenant_id", "Company"), "ccc": ""}
    xml = generate_siltra_cotizacion_xml(company, emp_data)
    return Response(content=xml.encode("utf-8"), media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename=siltra_cotizacion.xml"})


@router.get("/siltra/costs")
async def calculate_ss_costs(
    gross_salary: float = 1500,
    contract_type: str = "indefinido",
    contribution_group: str = "1",
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "admin", "payroll_admin"]))
):
    from app.services.siltra_sepe import calculate_social_security_costs
    return await calculate_social_security_costs(gross_salary, contribution_group, contract_type)


class TaxCalculateRequest(BaseModel):
    gross_salary: float
    country_code: str


@router.get("/tax/countries")
async def get_tax_countries():
    from app.services.tax_calculator import get_all_countries
    return get_all_countries()


@router.get("/tax/brackets/{country_code}")
async def get_tax_brackets_endpoint(country_code: str):
    from app.services.tax_calculator import get_tax_brackets
    return get_tax_brackets(country_code)


@router.post("/tax/calculate")
async def calculate_tax_endpoint(data: TaxCalculateRequest):
    from app.services.tax_calculator import calculate_tax
    return calculate_tax(data.gross_salary, data.country_code)

