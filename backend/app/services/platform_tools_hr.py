import logging
import json
import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.models.user import User
from app.models.calendar import VacationRequest, Meeting, Task
from app.models.pay import PayrollCycle, Payslip, PayslipLineItem, TaxRule, Bonus
from app.models.finance import TimeLog, WorkSchedule, JournalEntry, JournalLine, ExpenseClaim
from app.models.it import ITTicket, ITAsset

logger = logging.getLogger(__name__)


async def tool_create_employee(
    db: AsyncSession,
    email: str,
    full_name: str,
    department: str,
    role: str = "employee",
    base_salary: float = 0,
    country: str = "ES",
    contract_type: str = "indefinido",
    hire_date: str = "",
    vacation_allowance: int = 22,
) -> str:
    try:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            return json.dumps({"error": f"Empleado con email {email} ya existe"})

        parsed_hire_date = None
        if hire_date:
            parsed_hire_date = datetime.fromisoformat(hire_date.replace("Z", "+00:00"))

        employee = User(
            id=uuid.uuid4().hex,
            email=email,
            full_name=full_name,
            department=department,
            role=role,
            base_salary=base_salary,
            country=country,
            contract_type=contract_type,
            hire_date=parsed_hire_date or datetime.now(timezone.utc),
            vacation_allowance=vacation_allowance,
            hashed_password=None,
            is_active=True,
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)

        return json.dumps({
            "success": True,
            "employee_id": employee.id,
            "email": employee.email,
            "full_name": employee.full_name,
            "department": employee.department,
            "role": employee.role,
            "message": "Empleado creado exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_create_employee: {e}")
        return json.dumps({"error": str(e)})


async def tool_update_employee(
    db: AsyncSession,
    employee_id: str,
    fields: Dict[str, Any] = None,
) -> str:
    try:
        if not fields:
            return json.dumps({"error": "Debe especificar 'fields' con los campos a actualizar"})

        result = await db.execute(select(User).where(User.id == employee_id))
        user = result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})

        valid_columns = {c.name for c in User.__table__.columns}

        for col, val in (fields or {}).items():
            if col in valid_columns:
                if col == "hire_date" and isinstance(val, str) and val:
                    val = datetime.fromisoformat(val.replace("Z", "+00:00"))
                setattr(user, col, val)

        user.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "updated_fields": list((fields or {}).keys()),
            "message": "Empleado actualizado exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_update_employee: {e}")
        return json.dumps({"error": str(e)})


async def tool_archive_employee(
    db: AsyncSession,
    employee_id: str,
) -> str:
    try:
        result = await db.execute(select(User).where(User.id == employee_id))
        user = result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})

        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "full_name": user.full_name,
            "event": "employee.archived",
            "message": "Empleado archivado (is_active=False).",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_archive_employee: {e}")
        return json.dumps({"error": str(e)})


async def tool_search_employees(
    db: AsyncSession,
    query: str = "",
    department: str = "",
    role: str = "",
    is_active: bool = True,
    limit: int = 20,
) -> str:
    try:
        conditions = []
        if query:
            conditions.append(
                User.full_name.ilike(f"%{query}%") | User.email.ilike(f"%{query}%")
            )
        if department:
            conditions.append(User.department == department)
        if role:
            conditions.append(User.role == role)
        conditions.append(User.is_active == is_active)

        stmt = select(User).where(and_(*conditions)).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()

        members = []
        for u in users:
            members.append({
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "department": u.department,
                "role": u.role,
                "is_active": u.is_active,
            })

        return json.dumps({
            "success": True,
            "count": len(members),
            "employees": members,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_search_employees: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_employee_profile(
    db: AsyncSession,
    employee_id: str,
) -> str:
    try:
        result = await db.execute(select(User).where(User.id == employee_id))
        user = result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})

        return json.dumps({
            "success": True,
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role,
            "is_active": user.is_active,
            "country": user.country,
            "contract_type": user.contract_type,
            "hire_date": user.hire_date.isoformat() if user.hire_date else None,
            "vacation_allowance": user.vacation_allowance,
            "base_salary": user.base_salary,
            "currency": user.currency,
            "manager_id": user.manager_id,
            "timezone": user.timezone,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_employee_profile: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_org_chart(
    db: AsyncSession,
    max_depth: int = 5,
) -> str:
    try:
        result = await db.execute(select(User))
        all_users = result.scalars().all()

        user_map: Dict[str, Dict[str, Any]] = {}
        for u in all_users:
            user_map[u.id] = {
                "id": u.id,
                "full_name": u.full_name or "",
                "department": u.department or "",
                "role": u.role or "",
                "children": [],
            }

        roots = []
        for u in all_users:
            if u.manager_id and u.manager_id in user_map:
                user_map[u.manager_id]["children"].append(user_map[u.id])
            else:
                roots.append(user_map[u.id])

        def prune_depth(node: dict, depth: int) -> dict:
            if depth >= max_depth:
                node["children"] = []
                return node
            node["children"] = [prune_depth(c, depth + 1) for c in node["children"]]
            return node

        chart = [prune_depth(r, 0) for r in roots]

        return json.dumps({
            "success": True,
            "max_depth": max_depth,
            "org_chart": chart,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_org_chart: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_span_of_control(
    db: AsyncSession,
) -> str:
    try:
        result = await db.execute(select(User))
        all_users = result.scalars().all()

        user_by_id = {u.id: u for u in all_users}
        report_counts: Dict[str, int] = {}
        for u in all_users:
            if u.manager_id:
                report_counts[u.manager_id] = report_counts.get(u.manager_id, 0) + 1

        spans = []
        for mgr_id, count in report_counts.items():
            mgr = user_by_id.get(mgr_id)
            if mgr:
                spans.append({
                    "manager_name": mgr.full_name or mgr.email,
                    "manager_id": mgr.id,
                    "department": mgr.department or "",
                    "report_count": count,
                })

        spans.sort(key=lambda x: x["report_count"], reverse=True)

        return json.dumps({
            "success": True,
            "spans": spans,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_span_of_control: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_pto_balance(
    db: AsyncSession,
    employee_id: str,
) -> str:
    try:
        result = await db.execute(select(User).where(User.id == employee_id))
        user = result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})

        req_result = await db.execute(
            select(VacationRequest).where(
                VacationRequest.user_id == employee_id,
                VacationRequest.status == "approved",
            )
        )
        approved_requests = req_result.scalars().all()

        days_used = 0
        for r in approved_requests:
            delta = (r.end_date - r.start_date).days + 1
            days_used += delta

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "allowance": user.vacation_allowance,
            "used": days_used,
            "remaining": max(0, user.vacation_allowance - days_used),
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_pto_balance: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_department_members(
    db: AsyncSession,
    department: str,
) -> str:
    try:
        result = await db.execute(
            select(User).where(
                User.department == department,
                User.is_active == True,
            )
        )
        users = result.scalars().all()

        members = []
        for u in users:
            members.append({
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
            })

        return json.dumps({
            "success": True,
            "department": department,
            "count": len(members),
            "members": members,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_department_members: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_recent_hires(
    db: AsyncSession,
    days: int = 30,
) -> str:
    try:
        cutoff = datetime.now(timezone.utc) - date.resolution * days
        result = await db.execute(
            select(User).where(
                User.is_active == True,
                User.hire_date >= cutoff,
            ).order_by(User.hire_date.desc())
        )
        users = result.scalars().all()

        hires = []
        for u in users:
            hires.append({
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "department": u.department,
                "role": u.role,
                "hire_date": u.hire_date.isoformat() if u.hire_date else None,
            })

        return json.dumps({
            "success": True,
            "days": days,
            "count": len(hires),
            "employees": hires,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_recent_hires: {e}")
        return json.dumps({"error": str(e)})


async def tool_request_vacation(
    db: AsyncSession,
    employee_id: str,
    start_date: str,
    end_date: str,
    reason: str = "",
) -> str:
    try:
        from datetime import timedelta

        sd = datetime.fromisoformat(start_date.replace("Z", "+00:00")).date()
        ed = datetime.fromisoformat(end_date.replace("Z", "+00:00")).date()

        if sd >= ed:
            return json.dumps({"error": "start_date debe ser anterior a end_date"})

        overlap_result = await db.execute(
            select(VacationRequest).where(
                VacationRequest.user_id == employee_id,
                VacationRequest.status.in_(["pending", "approved"]),
                VacationRequest.start_date <= ed,
                VacationRequest.end_date >= sd,
            )
        )
        if overlap_result.scalar_one_or_none():
            return json.dumps({"error": "Ya existe una solicitud de vacaciones en ese rango de fechas"})

        vr = VacationRequest(
            id=uuid.uuid4().hex,
            user_id=employee_id,
            start_date=sd,
            end_date=ed,
            reason=reason,
            status="pending",
        )
        db.add(vr)
        await db.commit()
        await db.refresh(vr)

        return json.dumps({
            "success": True,
            "vacation_id": vr.id,
            "status": vr.status,
            "start_date": sd.isoformat(),
            "end_date": ed.isoformat(),
            "message": "Solicitud de vacaciones creada (pending).",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_request_vacation: {e}")
        return json.dumps({"error": str(e)})


async def tool_approve_vacation(
    db: AsyncSession,
    vacation_id: str,
    approved: bool = True,
    reviewer_id: str = "",
) -> str:
    try:
        result = await db.execute(select(VacationRequest).where(VacationRequest.id == vacation_id))
        vr = result.scalar_one_or_none()
        if not vr:
            return json.dumps({"error": "Solicitud de vacaciones no encontrada"})

        vr.status = "approved" if approved else "rejected"
        vr.reviewed_by = reviewer_id or ""
        vr.reviewed_at = datetime.now(timezone.utc)
        await db.commit()

        event_type = "vacation.approved" if approved else "vacation.rejected"

        return json.dumps({
            "success": True,
            "vacation_id": vr.id,
            "status": vr.status,
            "event": event_type,
            "message": f"Solicitud {'aprobada' if approved else 'rechazada'}.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_approve_vacation: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_team_calendar(
    db: AsyncSession,
    department: str = "",
    days: int = 30,
) -> str:
    try:
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)

        employee_ids = []
        if department:
            user_result = await db.execute(
                select(User.id).where(User.department == department, User.is_active == True)
            )
            employee_ids = [row[0] for row in user_result.all()]

        vacations = []
        vac_conditions = [
            VacationRequest.end_date >= now.date(),
            VacationRequest.start_date <= cutoff.date(),
        ]
        if employee_ids:
            vac_conditions.append(VacationRequest.user_id.in_(employee_ids))
        vac_result = await db.execute(
            select(VacationRequest).where(and_(*vac_conditions))
        )
        for v in vac_result.scalars().all():
            vacations.append({
                "type": "vacation",
                "id": v.id,
                "user_id": v.user_id,
                "start_date": v.start_date.isoformat() if v.start_date else None,
                "end_date": v.end_date.isoformat() if v.end_date else None,
                "status": v.status,
            })

        meetings = []
        mtg_conditions = [
            Meeting.start_datetime >= now,
            Meeting.start_datetime <= cutoff,
        ]
        if employee_ids:
            mtg_conditions.append(Meeting.organizer_id.in_(employee_ids))
        mtg_result = await db.execute(
            select(Meeting).where(and_(*mtg_conditions))
        )
        for m in mtg_result.scalars().all():
            meetings.append({
                "type": "meeting",
                "id": m.id,
                "title": m.title,
                "start_datetime": m.start_datetime.isoformat() if m.start_datetime else None,
                "end_datetime": m.end_datetime.isoformat() if m.end_datetime else None,
                "location": m.location,
                "organizer_id": m.organizer_id,
            })

        tasks = []
        task_conditions = [Task.due_date >= now.date(), Task.due_date <= cutoff.date()]
        if employee_ids:
            task_conditions.append(Task.assigned_to.in_(employee_ids))
        task_result = await db.execute(
            select(Task).where(and_(*task_conditions))
        )
        for t in task_result.scalars().all():
            tasks.append({
                "type": "task",
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "priority": t.priority,
                "status": t.status,
                "assigned_to": t.assigned_to,
            })

        return json.dumps({
            "success": True,
            "department": department,
            "days_ahead": days,
            "events": vacations + meetings + tasks,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_team_calendar: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_meeting(
    db: AsyncSession,
    title: str,
    organizer_id: str,
    start_datetime: str,
    end_datetime: str,
    attendees: List[str] = None,
    location: str = "",
    description: str = "",
) -> str:
    try:
        sd = datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
        ed = datetime.fromisoformat(end_datetime.replace("Z", "+00:00"))

        if sd >= ed:
            return json.dumps({"error": "start_datetime debe ser anterior a end_datetime"})

        meeting = Meeting(
            id=uuid.uuid4().hex,
            title=title,
            description=description,
            start_datetime=sd,
            end_datetime=ed,
            location=location,
            organizer_id=organizer_id,
            attendees=attendees or [],
        )
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)

        return json.dumps({
            "success": True,
            "meeting_id": meeting.id,
            "title": meeting.title,
            "start_datetime": meeting.start_datetime.isoformat(),
            "end_datetime": meeting.end_datetime.isoformat(),
            "message": "Reunion creada exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_create_meeting: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_work_schedule(
    db: AsyncSession,
    employee_id: str,
) -> str:
    try:
        result = await db.execute(
            select(WorkSchedule).where(WorkSchedule.user_id == employee_id)
        )
        schedules = result.scalars().all()

        day_names = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
        schedule_data = {}
        for s in schedules:
            schedule_data[day_names.get(s.day_of_week, str(s.day_of_week))] = {
                "start_time": s.start_time,
                "end_time": s.end_time,
                "flexible": s.flexible,
            }

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "schedule": schedule_data,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_work_schedule: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_payroll_cycle(
    db: AsyncSession,
    period_name: str,
    start_date: str,
    end_date: str,
) -> str:
    try:
        sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        cycle = PayrollCycle(
            id=str(uuid.uuid4()),
            period_name=period_name,
            start_date=sd,
            end_date=ed,
            status="draft",
        )
        db.add(cycle)
        await db.commit()
        await db.refresh(cycle)

        return json.dumps({
            "success": True,
            "cycle_id": cycle.id,
            "period_name": cycle.period_name,
            "status": cycle.status,
            "message": "Ciclo de nomina creado exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_create_payroll_cycle: {e}")
        return json.dumps({"error": str(e)})


async def tool_process_payroll(
    db: AsyncSession,
    cycle_id: str,
) -> str:
    try:
        cycle_result = await db.execute(select(PayrollCycle).where(PayrollCycle.id == cycle_id))
        cycle = cycle_result.scalar_one_or_none()
        if not cycle:
            return json.dumps({"error": "Ciclo de nomina no encontrado"})
        if cycle.status != "draft":
            return json.dumps({"error": f"El ciclo ya esta en estado '{cycle.status}', no se puede procesar"})

        user_result = await db.execute(select(User).where(User.is_active == True))
        users = user_result.scalars().all()

        total_gross = 0.0
        total_net = 0.0
        payslip_count = 0

        for user in users:
            gross = user.base_salary
            deductions = gross * 0.19
            net = gross - deductions

            payslip = Payslip(
                id=str(uuid.uuid4()),
                cycle_id=cycle_id,
                employee_id=user.id,
                gross_salary=gross,
                deductions=deductions,
                net_salary=net,
                currency=user.currency or "EUR",
                status="draft",
            )
            db.add(payslip)

            db.add(PayslipLineItem(
                id=str(uuid.uuid4()),
                payslip_id=payslip.id,
                description="Salario base",
                amount=gross,
                type="earning",
            ))
            db.add(PayslipLineItem(
                id=str(uuid.uuid4()),
                payslip_id=payslip.id,
                description="IRPF",
                amount=deductions,
                type="deduction",
            ))

            total_gross += gross
            total_net += net
            payslip_count += 1

        cycle.status = "processing"
        cycle.total_gross = total_gross
        cycle.total_net = total_net

        await db.commit()

        return json.dumps({
            "success": True,
            "cycle_id": cycle_id,
            "status": cycle.status,
            "payslip_count": payslip_count,
            "total_gross": total_gross,
            "total_net": total_net,
            "message": "Nomina procesada exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_process_payroll: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_payslip(
    db: AsyncSession,
    employee_id: str,
    cycle_id: str = "",
) -> str:
    try:
        conditions = [Payslip.employee_id == employee_id]
        if cycle_id:
            conditions.append(Payslip.cycle_id == cycle_id)

        stmt = select(Payslip).where(and_(*conditions)).order_by(Payslip.created_at.desc())
        result = await db.execute(stmt)
        payslip = result.scalars().first()

        if not payslip:
            if cycle_id:
                return json.dumps({"error": "Nomina no encontrada para ese ciclo"})
            return json.dumps({"error": "No hay nominas para este empleado"})

        lines_result = await db.execute(
            select(PayslipLineItem).where(PayslipLineItem.payslip_id == payslip.id)
        )
        lines = lines_result.scalars().all()

        line_items = []
        for li in lines:
            line_items.append({
                "description": li.description,
                "amount": li.amount,
                "type": li.type,
            })

        return json.dumps({
            "success": True,
            "payslip_id": payslip.id,
            "cycle_id": payslip.cycle_id,
            "employee_id": payslip.employee_id,
            "gross_salary": payslip.gross_salary,
            "deductions": payslip.deductions,
            "net_salary": payslip.net_salary,
            "currency": payslip.currency,
            "status": payslip.status,
            "line_items": line_items,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_payslip: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_tax_rules(
    db: AsyncSession,
    country_code: str = "",
) -> str:
    try:
        if country_code:
            result = await db.execute(
                select(TaxRule).where(TaxRule.country_code == country_code)
            )
        else:
            result = await db.execute(select(TaxRule))
        rules = result.scalars().all()

        tax_list = []
        for r in rules:
            tax_list.append({
                "id": r.id,
                "country_code": r.country_code,
                "name": r.name,
                "calculation_type": r.calculation_type,
                "rate": r.rate,
                "min_salary": r.min_salary,
                "max_salary": r.max_salary,
                "is_deduction": r.is_deduction,
                "is_marginal": r.is_marginal,
            })

        return json.dumps({
            "success": True,
            "country_code": country_code or "all",
            "count": len(tax_list),
            "tax_rules": tax_list,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_tax_rules: {e}")
        return json.dumps({"error": str(e)})


async def tool_update_compensation(
    db: AsyncSession,
    employee_id: str,
    base_salary: float,
    currency: str = "EUR",
) -> str:
    try:
        result = await db.execute(select(User).where(User.id == employee_id))
        user = result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})

        old_salary = user.base_salary
        user.base_salary = base_salary
        user.currency = currency
        user.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "old_salary": old_salary,
            "new_salary": base_salary,
            "currency": currency,
            "event": "salary.changed",
            "message": "Compensacion actualizada exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_update_compensation: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_bonus(
    db: AsyncSession,
    employee_id: str,
    amount: float,
    description: str,
    bonus_type: str = "standard",
) -> str:
    try:
        result = await db.execute(select(User).where(User.id == employee_id))
        user = result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})

        bonus = Bonus(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            amount=amount,
            description=description,
            type=bonus_type,
            status="pending",
        )
        db.add(bonus)
        await db.commit()
        await db.refresh(bonus)

        return json.dumps({
            "success": True,
            "bonus_id": bonus.id,
            "employee_id": employee_id,
            "amount": amount,
            "type": bonus_type,
            "status": bonus.status,
            "message": "Bono creado exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_create_bonus: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_financial_ledger(
    db: AsyncSession,
    start_date: str = "",
    end_date: str = "",
    limit: int = 50,
) -> str:
    try:
        conditions = []
        from datetime import date as dt_date

        if start_date:
            sd = datetime.fromisoformat(start_date.replace("Z", "+00:00")).date()
            conditions.append(JournalEntry.date >= sd)
        if end_date:
            ed = datetime.fromisoformat(end_date.replace("Z", "+00:00")).date()
            conditions.append(JournalEntry.date <= ed)

        stmt = select(JournalEntry).order_by(JournalEntry.date.desc()).limit(limit)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await db.execute(stmt)
        entries = result.scalars().all()

        ledger = []
        for entry in entries:
            lines_result = await db.execute(
                select(JournalLine).where(JournalLine.entry_id == entry.id)
            )
            lines = lines_result.scalars().all()
            line_data = []
            for l in lines:
                line_data.append({
                    "account_code": l.account_code,
                    "account_name": l.account_name,
                    "debit": float(l.debit),
                    "credit": float(l.credit),
                })

            ledger.append({
                "id": entry.id,
                "reference": entry.reference,
                "date": entry.date.isoformat() if entry.date else None,
                "description": entry.description,
                "lines": line_data,
            })

        return json.dumps({
            "success": True,
            "count": len(ledger),
            "entries": ledger,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_financial_ledger: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_expense_summary(
    db: AsyncSession,
    department: str = "",
    start_date: str = "",
    end_date: str = "",
) -> str:
    try:
        conditions = []
        from datetime import date as dt_date

        if start_date:
            sd = datetime.fromisoformat(start_date.replace("Z", "+00:00")).date()
            conditions.append(ExpenseClaim.date >= sd)
        if end_date:
            ed = datetime.fromisoformat(end_date.replace("Z", "+00:00")).date()
            conditions.append(ExpenseClaim.date <= ed)

        if department:
            user_result = await db.execute(
                select(User.id).where(User.department == department)
            )
            dept_ids = [row[0] for row in user_result.all()]
            if dept_ids:
                conditions.append(ExpenseClaim.user_id.in_(dept_ids))
            else:
                return json.dumps({"success": True, "department": department, "total": 0, "by_category": {}, "by_department": {}, "count": 0}, ensure_ascii=False)

        stmt = select(ExpenseClaim)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await db.execute(stmt)
        claims = result.scalars().all()

        total = 0.0
        by_category: Dict[str, float] = {}
        by_dept: Dict[str, float] = {}
        user_departments: Dict[str, str] = {}

        user_ids = list(set(c.user_id for c in claims))
        if user_ids:
            user_result = await db.execute(
                select(User.id, User.department).where(User.id.in_(user_ids))
            )
            for row in user_result.all():
                user_departments[row[0]] = row[1] or "unknown"

        for c in claims:
            amt = float(c.total_amount)
            total += amt
            by_category[c.category] = by_category.get(c.category, 0) + amt
            dept = user_departments.get(c.user_id, "unknown")
            by_dept[dept] = by_dept.get(dept, 0) + amt

        return json.dumps({
            "success": True,
            "department": department,
            "start_date": start_date,
            "end_date": end_date,
            "total": total,
            "count": len(claims),
            "by_category": by_category,
            "by_department": by_dept,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_expense_summary: {e}")
        return json.dumps({"error": str(e)})


async def tool_clock_in(
    db: AsyncSession,
    employee_id: str,
    notes: str = "",
) -> str:
    try:
        active_result = await db.execute(
            select(TimeLog).where(
                TimeLog.user_id == employee_id,
                TimeLog.clock_out == None,
            )
        )
        if active_result.scalar_one_or_none():
            return json.dumps({"error": "El empleado ya tiene un fichaje activo sin salida"})

        log = TimeLog(
            id=uuid.uuid4().hex,
            user_id=employee_id,
            clock_in=datetime.now(timezone.utc),
            notes=notes,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        return json.dumps({
            "success": True,
            "log_id": log.id,
            "clock_in": log.clock_in.isoformat(),
            "message": "Fichaje de entrada registrado.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_clock_in: {e}")
        return json.dumps({"error": str(e)})


async def tool_clock_out(
    db: AsyncSession,
    log_id: str,
    notes: str = "",
) -> str:
    try:
        result = await db.execute(select(TimeLog).where(TimeLog.id == log_id))
        log = result.scalar_one_or_none()
        if not log:
            return json.dumps({"error": "Fichaje no encontrado"})
        if log.clock_out is not None:
            return json.dumps({"error": "Este fichaje ya tiene salida registrada"})

        log.clock_out = datetime.now(timezone.utc)
        if notes:
            existing = log.notes or ""
            log.notes = f"{existing}\n{notes}".strip()
        await db.commit()

        return json.dumps({
            "success": True,
            "log_id": log.id,
            "clock_in": log.clock_in.isoformat(),
            "clock_out": log.clock_out.isoformat(),
            "message": "Fichaje de salida registrado.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_clock_out: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_time_logs(
    db: AsyncSession,
    employee_id: str,
    start_date: str = "",
    end_date: str = "",
) -> str:
    try:
        conditions = [TimeLog.user_id == employee_id]
        if start_date:
            sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            conditions.append(TimeLog.clock_in >= sd)
        if end_date:
            ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            conditions.append(TimeLog.clock_in <= ed)

        result = await db.execute(
            select(TimeLog).where(and_(*conditions)).order_by(TimeLog.clock_in.desc())
        )
        logs = result.scalars().all()

        log_list = []
        for l in logs:
            log_list.append({
                "id": l.id,
                "clock_in": l.clock_in.isoformat() if l.clock_in else None,
                "clock_out": l.clock_out.isoformat() if l.clock_out else None,
                "notes": l.notes,
            })

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "count": len(log_list),
            "time_logs": log_list,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_time_logs: {e}")
        return json.dumps({"error": str(e)})


async def tool_assign_it_ticket(
    db: AsyncSession,
    ticket_id: str,
    assignee_id: str,
) -> str:
    try:
        result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            return json.dumps({"error": "Ticket de IT no encontrado"})

        ticket.assignee_id = assignee_id
        ticket.status = "in_progress"
        ticket.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return json.dumps({
            "success": True,
            "ticket_id": ticket.id,
            "assignee_id": assignee_id,
            "status": ticket.status,
            "message": "Ticket de IT asignado exitosamente.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_assign_it_ticket: {e}")
        return json.dumps({"error": str(e)})


async def tool_resolve_it_ticket(
    db: AsyncSession,
    ticket_id: str,
    resolution_notes: str,
) -> str:
    try:
        result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            return json.dumps({"error": "Ticket de IT no encontrado"})

        ticket.status = "resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        ticket.resolution_notes = resolution_notes
        ticket.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return json.dumps({
            "success": True,
            "ticket_id": ticket.id,
            "status": ticket.status,
            "resolved_at": ticket.resolved_at.isoformat(),
            "resolution_notes": resolution_notes,
            "kb_reference": f"KB-{ticket_id[:8]}",
            "message": "Ticket resuelto. Se ha generado referencia para KB.",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_resolve_it_ticket: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_it_assets(
    db: AsyncSession,
    assigned_to_id: str = "",
    category: str = "",
) -> str:
    try:
        conditions = []
        if assigned_to_id:
            conditions.append(ITAsset.assigned_to_id == assigned_to_id)
        if category:
            conditions.append(ITAsset.category == category)

        stmt = select(ITAsset)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await db.execute(stmt)
        assets = result.scalars().all()

        asset_list = []
        for a in assets:
            asset_list.append({
                "id": a.id,
                "name": a.name,
                "serial_number": a.serial_number,
                "category": a.category,
                "status": a.status,
                "assigned_to_id": a.assigned_to_id,
                "purchase_date": a.purchase_date.isoformat() if a.purchase_date else None,
                "cost": float(a.cost) if a.cost else None,
            })

        return json.dumps({
            "success": True,
            "count": len(asset_list),
            "assets": asset_list,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_it_assets: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_ticket_stats(
    db: AsyncSession,
    days: int = 30,
) -> str:
    try:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        all_tickets = await db.execute(
            select(ITTicket).where(ITTicket.created_at >= cutoff)
        )
        tickets = all_tickets.scalars().all()

        opened = 0
        resolved = 0
        resolution_times = []
        by_category: Dict[str, Dict[str, int]] = {}

        for t in tickets:
            category = t.category or "unknown"
            if category not in by_category:
                by_category[category] = {"opened": 0, "resolved": 0}
            by_category[category]["opened"] += 1
            opened += 1

            if t.status in ("resolved", "closed") and t.resolved_at:
                resolved += 1
                by_category[category]["resolved"] += 1
                delta = (t.resolved_at - t.created_at).total_seconds() / 3600.0
                resolution_times.append(delta)

        avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0

        return json.dumps({
            "success": True,
            "days": days,
            "opened": opened,
            "resolved": resolved,
            "avg_resolution_hours": round(avg_resolution, 1),
            "by_category": by_category,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool_get_ticket_stats: {e}")
        return json.dumps({"error": str(e)})
