from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import io
import csv
import base64
from datetime import datetime, timezone, date
import uuid
from app.api.dependencies import get_tenant_db, get_current_user, require_roles, check_module_enabled
from app.models.finance import ExpenseClaim, TimeLog, BreakLog, WorkSchedule, GeneralShift, JournalEntry, JournalLine, Budget, BudgetLine, Invoice, CurrencyRate
from app.models.user import User
from app.schemas.finance import (
    ExpenseClaimCreate, ExpenseClaimResponse, ExpenseClaimUpdate,
    TimeLogClockIn, TimeLogClockOut, TimeLogResponse,
    BreakLogCreate, BreakLogResponse, TimeLogResponseWithBreaks,
    WorkScheduleCreate, WorkScheduleResponse,
    GeneralShiftCreate, GeneralShiftResponse, BulkShiftAssignment,
    JournalEntryResponse,
    BudgetCreate, BudgetResponse, BudgetUpdate,
    BudgetLineCreate, BudgetLineResponse, BudgetLineUpdate,
    BudgetSummaryResponse,
    InvoiceCreate, InvoiceResponse, InvoiceUpdate, InvoiceAgingResponse,
    CurrencyRateResponse, CurrencyConvertRequest, CurrencyConvertResponse,
)

router = APIRouter(dependencies=[Depends(check_module_enabled("finance"))])


def _get_user_id(user_payload: dict) -> str:
    """
    [H2 FIX] Extract the actual user ID from the JWT payload.
    The 'sub' claim is the standard field (e.g. 'local|abc123' or 'auth0|xyz').
    user_payload.get('user_id') does NOT exist in standard JWTs.
    """
    # Tokens locales HS256: sub = 'local|<id>'
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    # Fallback: sub sin prefijo (tokens de prueba)
    return sub


# ==========================================
# EXPENSE CLAIMS ENDPOINTS
# ==========================================
@router.get("/expenses", response_model=List[ExpenseClaimResponse])
async def list_expenses(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar notas de gastos."""
    query = select(ExpenseClaim)
    current_user_id = _get_user_id(user_payload)
    
    # Restricciones por rol
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    if "employee" in user_roles and "hr_admin" not in user_roles:
        query = query.where(ExpenseClaim.user_id == current_user_id)
    elif user_id:
        query = query.where(ExpenseClaim.user_id == user_id)
        
    if status:
        query = query.where(ExpenseClaim.status == status)
        
    result = await db.execute(query.order_by(ExpenseClaim.created_at.desc()))
    return result.scalars().all()


@router.post("/expenses", response_model=ExpenseClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_in: ExpenseClaimCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Subir/Crear una nueva nota de gastos."""
    current_user_id = _get_user_id(user_payload)
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    if "employee" in user_roles and "hr_admin" not in user_roles and expense_in.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="No puedes crear gastos a nombre de otro empleado")

    expense = ExpenseClaim(
        id=uuid.uuid4().hex,
        status="pending",
        **expense_in.model_dump()
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseClaimResponse)
async def update_expense(
    expense_id: str,
    expense_in: ExpenseClaimUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Actualizar/Aprobar una nota de gastos."""
    result = await db.execute(select(ExpenseClaim).where(ExpenseClaim.id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Nota de gastos no encontrada")

    current_user_id = _get_user_id(user_payload)
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    is_employee_only = "employee" in user_roles and "hr_admin" not in user_roles

    # Restricciones por rol
    if is_employee_only:
        if expense.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="No puedes modificar un gasto ajeno")
        if expense.status != "pending":
            raise HTTPException(status_code=400, detail="No puedes editar un gasto ya procesado")
        # El empleado no puede aprobar sus propios gastos
        if expense_in.status and expense_in.status != expense.status:
            raise HTTPException(status_code=403, detail="Un empleado no puede modificar el estado de su gasto")
    else:
        # Si es admin y aprueba/rechaza, asignamos approved_by
        if expense_in.status in ["approved", "rejected"]:
            expense.approved_by_id = current_user_id

    for field, value in expense_in.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)

    # SAP FI integration: generate Journal Entry on Expense approval
    if expense.status in ["approved", "paid"]:
        try:
            from app.services.event_publisher import publish_expense_event
            await publish_expense_event(db, expense.id, expense.user_id, float(expense.total_amount), expense.category, "approved", "acme_corp")
        except Exception:
            pass
        ref = f"EXP-{expense.id}"
        exist_result = await db.execute(select(JournalEntry).where(JournalEntry.reference == ref))
        existing_entry = exist_result.scalar_one_or_none()
        if not existing_entry:
            tax_amt = float(expense.tax_amount or 0.0)
            total_amt = float(expense.total_amount)
            base_amt = total_amt - tax_amt
            
            entry = JournalEntry(
                id=uuid.uuid4().hex,
                reference=ref,
                date=expense.date,
                description=f"Aprobación Gasto: {expense.merchant} (Proveedor)"
            )
            db.add(entry)
            
            # Debit Line (629000 Otros servicios / Gastos diversos)
            db.add(JournalLine(
                id=uuid.uuid4().hex,
                entry_id=entry.id,
                account_code="629000",
                account_name="Otros servicios / Gastos diversos",
                debit=base_amt,
                credit=0.0
            ))
            
            # Debit Line (472000 Hacienda Pública, IVA Soportado)
            if tax_amt > 0:
                db.add(JournalLine(
                    id=uuid.uuid4().hex,
                    entry_id=entry.id,
                    account_code="472000",
                    account_name="Hacienda Pública, IVA Soportado",
                    debit=tax_amt,
                    credit=0.0
                ))
            
            # Credit Line (410000 Acreedores por prestaciones de servicios)
            db.add(JournalLine(
                id=uuid.uuid4().hex,
                entry_id=entry.id,
                account_code="410000",
                account_name="Acreedores por prestaciones de servicios",
                debit=0.0,
                credit=total_amt
            ))

    await db.commit()
    await db.refresh(expense)

    if expense.status == "approved":
        try:
            from app.services.notification_utils import create_and_push_notification
            await create_and_push_notification(
                db,
                user_id=expense.user_id,
                title="Expense Approved",
                message=f"Your expense for {expense.merchant} ({expense.total_amount}) has been approved",
                type_="system",
                link="/dashboard/finance?tab=expenses",
            )
            await db.commit()
        except Exception:
            pass

    return expense


# ==========================================
# AI RECEIPTS OCR SCANNER
# ==========================================
@router.post("/expenses/ocr")
async def scan_receipt_ocr(
    file: UploadFile = File(...),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """
    [C7 FIX] Endpoint de IA para el escaneo automático de facturas y recibos (OCR).
    Usa la API de OpenAI Vision (gpt-4o) para analizar la imagen real del recibo.
    Si la clave de OpenAI no está configurada, retorna un error claro en lugar de datos falsos.
    """
    from app.core.config import settings
    import openai
    import json
    
    # Read the uploaded file
    contents = await file.read()
    
    # Check if OpenAI is configured
    openai_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not openai_key:
        raise HTTPException(
            status_code=503,
            detail="El servicio de OCR no está configurado. Configura OPENAI_API_KEY en el servidor."
        )
    
    # Encode image to base64
    image_b64 = base64.b64encode(contents).decode("utf-8")
    
    # Detect MIME type
    mime_type = file.content_type or "image/jpeg"
    
    client = openai.AsyncOpenAI(api_key=openai_key)
    
    prompt = """
Analiza esta imagen de un recibo o factura y extrae la siguiente información en formato JSON:
{
  "merchant": "nombre del comercio o proveedor",
  "date": "fecha en formato YYYY-MM-DD (o null si no está visible)",
  "total_amount": "importe total como número decimal",
  "tax_amount": "importe del IVA/impuesto como número decimal (o null)",
  "category": "una de: meals, travel, software, supplies, accommodation, other",
  "comments": "breve descripción del gasto"
}
Responde SOLO con el JSON válido, sin texto adicional.
"""
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        
        extracted = json.loads(content)
        
        # Normalize the date
        receipt_date = extracted.get("date") or date.today().isoformat()
        
        return {
            "success": True,
            "source": "openai_vision",
            "data": {
                "merchant": extracted.get("merchant", ""),
                "date": receipt_date,
                "total_amount": float(extracted.get("total_amount") or 0),
                "tax_amount": float(extracted.get("tax_amount") or 0) if extracted.get("tax_amount") else None,
                "category": extracted.get("category", "other"),
                "comments": extracted.get("comments", "Extracción automática mediante SuccessCore AI OCR.")
            }
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail="No se pudo analizar la respuesta de la IA. Intenta con una imagen más clara."
        )
    except openai.OpenAIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al conectar con el servicio de IA: {str(e)}"
        )


# ==========================================
# EXPORT FINANCES (Sage / Holded)
# ==========================================
@router.get("/expenses/export")
async def export_expenses_file(
    format: str = "holded",  # holded, sage, a3innuva
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """
    Genera un archivo CSV/Excel mapeado directamente para importar notas de gastos
    en los ERPs de contabilidad más populares de España (Sage, Holded, a3innuva).
    """
    # Buscar todos los gastos aprobados
    result = await db.execute(select(ExpenseClaim).where(ExpenseClaim.status == "approved"))
    expenses = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    if format == "holded":
        # Formato de importación Holded: Concepto, Total, IVA, Categoría, Empleado, Fecha
        writer.writerow(["Concepto", "Total", "IVA", "Cuenta Contable", "Contacto/Empleado", "Fecha"])
        for exp in expenses:
            account_code = "629000"  # Código contable estándar español para Otros Servicios
            if exp.category == "meals":
                account_code = "629001"
            elif exp.category == "travel":
                account_code = "629002"
            elif exp.category == "software":
                account_code = "620000"
            
            writer.writerow([
                f"Gasto {exp.merchant}",
                str(exp.total_amount),
                str(exp.tax_amount or 0.0),
                account_code,
                f"User_{exp.user_id}",
                exp.date.isoformat()
            ])
            
    elif format == "sage":
        # Formato de diario Sage Despachos / Contaplus: CuentaDebito, CuentaCredito, Importe, Concepto, Fecha
        writer.writerow(["Fecha", "Subcuenta Debito", "Subcuenta Credito", "Concepto", "Importe"])
        for exp in expenses:
            account_code = "62900000"
            if exp.category == "meals":
                account_code = "62900001"
            elif exp.category == "travel":
                account_code = "62900002"
            writer.writerow([
                exp.date.strftime("%d/%m/%Y"),
                account_code,
                "46500000",  # Remuneraciones pendientes de pago (empleados)
                f"Nota de Gasto - {exp.merchant}",
                str(exp.total_amount)
            ])
    else:
        # Fallback genérico
        writer.writerow(["Fecha", "Empleado", "Proveedor", "Total", "Categoría"])
        for exp in expenses:
            writer.writerow([exp.date.isoformat(), exp.user_id, exp.merchant, str(exp.total_amount), exp.category])

    # Retornar como texto estructurado (CSV plano en la respuesta de API)
    return {
        "success": True,
        "format": format,
        "csv_content": output.getvalue()
    }


# ==========================================
# TIME LOGS (FICHAJE AVANZADO)
# ==========================================
@router.get("/time-logs", response_model=List[TimeLogResponse])
async def list_time_logs(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Obtener el listado de fichajes."""
    query = select(TimeLog)
    current_user_id = _get_user_id(user_payload)
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    
    if "employee" in user_roles and "hr_admin" not in user_roles:
        query = query.where(TimeLog.user_id == current_user_id)
    elif user_id:
        query = query.where(TimeLog.user_id == user_id)
        
    result = await db.execute(query.order_by(TimeLog.clock_in.desc()))
    return result.scalars().all()


@router.post("/time-logs/clock-in", response_model=TimeLogResponse)
async def clock_in(
    log_in: TimeLogClockIn,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Fichar Entrada (Clock-In) con geolocalización."""
    current_user_id = _get_user_id(user_payload)
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    if "employee" in user_roles and "hr_admin" not in user_roles and log_in.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="No puedes fichar por otro empleado")

    # Verificar si ya tiene un fichaje activo (sin salida)
    result = await db.execute(
        select(TimeLog).where(
            TimeLog.user_id == log_in.user_id,
            TimeLog.clock_out == None
        )
    )
    active_log = result.scalar_one_or_none()
    if active_log:
        raise HTTPException(status_code=400, detail="Ya tienes un fichaje activo sin salida")

    log = TimeLog(
        id=uuid.uuid4().hex,
        user_id=log_in.user_id,
        clock_in=datetime.now(timezone.utc),
        geolocation_in=log_in.geolocation_in,
        ip_address=log_in.ip_address,
        device_info=log_in.device_info,
        notes=log_in.notes
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.post("/time-logs/clock-out/{log_id}", response_model=TimeLogResponse)
async def clock_out(
    log_id: str,
    log_out: TimeLogClockOut,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Fichar Salida (Clock-Out) con geolocalización."""
    result = await db.execute(select(TimeLog).where(TimeLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Registro de fichaje no encontrado")

    current_user_id = _get_user_id(user_payload)
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    if "employee" in user_roles and "hr_admin" not in user_roles and log.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="No puedes fichar la salida de otro empleado")

    if log.clock_out:
        raise HTTPException(status_code=400, detail="Este fichaje ya tiene registrada una salida")

    log.clock_out = datetime.now(timezone.utc)
    log.geolocation_out = log_out.geolocation_out
    if log_out.notes:
        log.notes = (log.notes or "") + f" | Salida: {log_out.notes}"

    await db.commit()
    await db.refresh(log)
    return log


# ==========================================
# ACTIVE TIME LOG & BREAKS ENDPOINTS
# ==========================================

@router.get("/time-logs/active", response_model=Optional[TimeLogResponseWithBreaks])
async def get_active_time_log(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Obtener el fichaje activo actual del empleado (el que no tiene clock_out)."""
    user_id = _get_user_id(user_payload)  # [H2 FIX]
    
    # 1. Buscar fichaje activo
    result = await db.execute(
        select(TimeLog).where(
            TimeLog.user_id == user_id,
            TimeLog.clock_out == None
        )
    )
    active_log = result.scalar_one_or_none()
    if not active_log:
        return None

    # 2. Buscar descansos asociados
    breaks_res = await db.execute(
        select(BreakLog).where(BreakLog.time_log_id == active_log.id).order_by(BreakLog.start_time.asc())
    )
    breaks_list = breaks_res.scalars().all()
    
    # Mapear a respuesta extendida
    response_data = TimeLogResponseWithBreaks.model_validate(active_log)
    response_data.breaks = [BreakLogResponse.model_validate(b) for b in breaks_list]
    return response_data


@router.post("/time-logs/active/break/start", response_model=BreakLogResponse)
async def start_break(
    break_in: BreakLogCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Iniciar un descanso (pausa) en el fichaje activo."""
    user_id = user_payload.get("user_id")
    
    # 1. Obtener fichaje activo
    result = await db.execute(
        select(TimeLog).where(
            TimeLog.user_id == user_id,
            TimeLog.clock_out == None
        )
    )
    active_log = result.scalar_one_or_none()
    if not active_log:
        raise HTTPException(status_code=400, detail="No tienes una jornada activa iniciada. Ficha la entrada primero.")

    # 2. Verificar si ya hay un descanso activo sin finalizar
    break_active_res = await db.execute(
        select(BreakLog).where(
            BreakLog.time_log_id == active_log.id,
            BreakLog.end_time == None
        )
    )
    active_break = break_active_res.scalar_one_or_none()
    if active_break:
        raise HTTPException(status_code=400, detail="Ya tienes un descanso activo sin finalizar.")

    # 3. Crear descanso
    new_break = BreakLog(
        id=uuid.uuid4().hex,
        time_log_id=active_log.id,
        break_type=break_in.break_type,
        start_time=datetime.now(timezone.utc),
        notes=break_in.notes
    )
    db.add(new_break)
    await db.commit()
    await db.refresh(new_break)
    return new_break


@router.post("/time-logs/active/break/end", response_model=BreakLogResponse)
async def end_break(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Finalizar el descanso activo actual."""
    user_id = user_payload.get("user_id")
    
    # 1. Obtener fichaje activo
    result = await db.execute(
        select(TimeLog).where(
            TimeLog.user_id == user_id,
            TimeLog.clock_out == None
        )
    )
    active_log = result.scalar_one_or_none()
    if not active_log:
        raise HTTPException(status_code=400, detail="No tienes una jornada activa iniciada.")

    # 2. Obtener descanso activo
    break_active_res = await db.execute(
        select(BreakLog).where(
            BreakLog.time_log_id == active_log.id,
            BreakLog.end_time == None
        )
    )
    active_break = break_active_res.scalar_one_or_none()
    if not active_break:
        raise HTTPException(status_code=400, detail="No tienes ningún descanso activo que finalizar.")

    # 3. Finalizar descanso
    active_break.end_time = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(active_break)
    return active_break


# ==========================================
# CUMPLIMIENTO LABORAL (ESPAÑA) ENDPOINTS
# ==========================================

@router.get("/time-logs/compliance")
async def check_compliance(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Auditoría de cumplimiento legal según el Estatuto de los Trabajadores de España."""
    # Restricciones por rol
    current_role = user_payload.get("role")
    target_user_id = user_payload.get("user_id")
    if current_role == "hr_admin" and user_id:
        target_user_id = user_id

    # 1. Obtener fichajes del usuario en los últimos 7 días
    logs_res = await db.execute(
        select(TimeLog).where(TimeLog.user_id == target_user_id).order_by(TimeLog.clock_in.desc())
    )
    logs = logs_res.scalars().all()

    alerts = []
    checks = {
        "rest_between_shifts": {"status": "ok", "message": "Descanso mínimo de 12h entre jornadas respetado."},
        "continuous_work_break": {"status": "ok", "message": "Pausa obligatoria de 15 minutos en jornadas > 6h cumplida."},
        "max_daily_hours": {"status": "ok", "message": "Jornada ordinaria diaria <= 9h respetada."}
    }

    # -- Regla 1: 12 horas de descanso entre jornadas --
    if len(logs) >= 2:
        for i in range(len(logs) - 1):
            current_in = logs[i].clock_in
            prev_out = logs[i+1].clock_out
            if prev_out:
                rest_duration = (current_in - prev_out).total_seconds() / 3600.0
                if rest_duration < 12.0:
                    checks["rest_between_shifts"] = {
                        "status": "warning",
                        "message": f"Infracción: Descanso de {rest_duration:.2f}h entre jornadas (mínimo 12h requerido)."
                    }
                    alerts.append({
                        "type": "rest_between_shifts",
                        "date": current_in.date().isoformat(),
                        "severity": "critical",
                        "detail": f"El empleado descansó solo {rest_duration:.1f} horas entre la salida del {prev_out.date().isoformat()} y la entrada del {current_in.date().isoformat()}."
                    })
                    break

    # -- Regla 2 y 3: Pausa de 15m para >6h e Infracción >9h diarias --
    for log in logs[:5]:  # Analizar los últimos 5 fichajes
        in_time = log.clock_in
        out_time = log.clock_out or datetime.now(timezone.utc)
        total_duration = (out_time - in_time).total_seconds() / 3600.0
        
        # Obtener descansos de este log
        breaks_res = await db.execute(
            select(BreakLog).where(BreakLog.time_log_id == log.id)
        )
        breaks = breaks_res.scalars().all()
        
        total_break_duration = 0.0
        for b in breaks:
            b_end = b.end_time or datetime.now(timezone.utc)
            total_break_duration += (b_end - b.start_time).total_seconds() / 60.0 # en minutos

        # Regla 2: Jornada > 6h continuada sin descanso de 15m
        if total_duration > 6.0 and total_break_duration < 15.0:
            checks["continuous_work_break"] = {
                "status": "warning",
                "message": f"Infracción el {in_time.date().isoformat()}: Jornada de {total_duration:.1f}h con solo {total_break_duration:.0f} min de descanso (min 15 min)."
            }
            alerts.append({
                "type": "continuous_work_break",
                "date": in_time.date().isoformat(),
                "severity": "warning",
                "detail": f"Jornada continua de {total_duration:.1f} horas sin registrar la pausa obligatoria de 15 minutos (Art. 34.4 ET)."
            })

        # Regla 3: Jornada ordinaria > 9h
        net_duration = total_duration - (total_break_duration / 60.0)
        if net_duration > 9.0:
            checks["max_daily_hours"] = {
                "status": "warning",
                "message": f"Infracción el {in_time.date().isoformat()}: Horas efectivas diarias de {net_duration:.1f}h exceden el límite de 9h."
            }
            alerts.append({
                "type": "max_daily_hours",
                "date": in_time.date().isoformat(),
                "severity": "info",
                "detail": f"Jornada efectiva diaria de {net_duration:.1f} horas excede el límite estándar de 9 horas diarias (Art. 34.3 ET). Requiere registro como Horas Extras."
            })

    return {
        "user_id": target_user_id,
        "checks": checks,
        "alerts": alerts
    }


# ==========================================
# WORK SCHEDULES (HORARIOS DE TRABAJO) ENDPOINTS
# ==========================================

@router.get("/work-schedules/mine")
async def get_my_schedule(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Obtener el horario asignado al empleado actual."""
    user_id = _get_user_id(user_payload)  # [H2 FIX]
    result = await db.execute(
        select(WorkSchedule).where(WorkSchedule.user_id == user_id).order_by(WorkSchedule.day_of_week.asc())
    )
    schedule = result.scalars().all()

    # [L5 FIX] Return empty array instead of unpersisted mock objects.
    # Mock schedules had fake IDs ('default_0') that caused 404s on update/delete.
    # The frontend should show a "No schedule assigned — contact HR" state.
    return {
        "schedules": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "day_of_week": s.day_of_week,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "flexible": s.flexible,
            }
            for s in schedule
        ],
        "has_schedule": len(schedule) > 0,
        "message": None if schedule else "No tienes un horario asignado. Contacta con tu responsable de RRHH."
    }


@router.get("/work-schedules", response_model=List[WorkScheduleResponse])
async def list_all_schedules(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Obtener todos los horarios planificados del inquilino (Solo HR Admin)."""
    result = await db.execute(
        select(WorkSchedule).order_by(WorkSchedule.user_id, WorkSchedule.day_of_week.asc())
    )
    return result.scalars().all()


@router.post("/work-schedules/{employee_id}", response_model=List[WorkScheduleResponse])
async def assign_employee_schedule(
    employee_id: str,
    schedules_in: List[WorkScheduleCreate],
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Crear/Modificar el horario semanal asignado a un empleado específico (Solo HR Admin)."""
    # 1. Eliminar horarios existentes de ese usuario
    from sqlalchemy import delete
    await db.execute(delete(WorkSchedule).where(WorkSchedule.user_id == employee_id))
    
    # 2. Agregar nuevos horarios
    new_schedules = []
    for s in schedules_in:
        entry = WorkSchedule(
            id=uuid.uuid4().hex,
            user_id=employee_id,
            day_of_week=s.day_of_week,
            start_time=s.start_time,
            end_time=s.end_time,
            flexible=s.flexible
        )
        db.add(entry)
        new_schedules.append(entry)
        
    await db.commit()
    return new_schedules


# ==========================================
# GENERAL SHIFTS (TURNOS GENERALES) ENDPOINTS
# ==========================================

@router.get("/general-shifts", response_model=List[GeneralShiftResponse])
async def list_general_shifts(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar todas las plantillas de turnos de trabajo generales."""
    result = await db.execute(select(GeneralShift).order_by(GeneralShift.name.asc()))
    shifts = result.scalars().all()
    
    # Si está vacío, sembramos algunos turnos de demostración obligatorios por Convenio Colectivo
    if not shifts:
        shifts = [
            GeneralShift(id="gs_m", name="Turno Mañana (07:00 - 15:00)", start_time="07:00", end_time="15:00"),
            GeneralShift(id="gs_t", name="Turno Tarde (15:00 - 23:00)", start_time="15:00", end_time="23:00"),
            GeneralShift(id="gs_n", name="Turno Noche (23:00 - 07:00)", start_time="23:00", end_time="07:00"),
            GeneralShift(id="gs_o", name="Turno Oficina (09:00 - 18:00)", start_time="09:00", end_time="18:00")
        ]
        for s in shifts:
            db.add(s)
        await db.commit()
        # Refrescar
        result = await db.execute(select(GeneralShift).order_by(GeneralShift.name.asc()))
        shifts = result.scalars().all()
        
    return shifts


@router.post("/general-shifts", response_model=GeneralShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_general_shift(
    shift_in: GeneralShiftCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Crear una nueva plantilla de turno de trabajo general (Solo HR Admin)."""
    shift = GeneralShift(
        id=uuid.uuid4().hex,
        **shift_in.model_dump()
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.delete("/general-shifts/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_general_shift(
    shift_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar una plantilla de turno general (Solo HR Admin)."""
    result = await db.execute(select(GeneralShift).where(GeneralShift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Turno general no encontrado")
        
    await db.delete(shift)
    await db.commit()
    return None


@router.post("/general-shifts/assign", status_code=status.HTTP_200_OK)
async def assign_bulk_shift(
    assignment: BulkShiftAssignment,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Asignar un turno de trabajo general a múltiples empleados a la vez para los días indicados (Solo HR Admin)."""
    # 1. Obtener el turno general
    start_t, end_t = "09:00", "18:00"
    
    if assignment.general_shift_id.startswith("gs_"):
        if assignment.general_shift_id == "gs_m":
            start_t, end_t = "07:00", "15:00"
        elif assignment.general_shift_id == "gs_t":
            start_t, end_t = "15:00", "23:00"
        elif assignment.general_shift_id == "gs_n":
            start_t, end_t = "23:00", "07:00"
    else:
        result = await db.execute(select(GeneralShift).where(GeneralShift.id == assignment.general_shift_id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="El turno general especificado no existe")
        start_t, end_t = shift.start_time, shift.end_time

    from sqlalchemy import delete
    
    # 2. Iterar por cada empleado
    for emp_id in assignment.employee_ids:
        # Eliminar horarios existentes en los días seleccionados
        await db.execute(
            delete(WorkSchedule).where(
                WorkSchedule.user_id == emp_id,
                WorkSchedule.day_of_week.in_(assignment.days)
            )
        )
        
        # Insertar los horarios del turno
        for day in assignment.days:
            new_sched = WorkSchedule(
                id=uuid.uuid4().hex,
                user_id=emp_id,
                day_of_week=day,
                start_time=start_t,
                end_time=end_t,
                flexible=False
            )
            db.add(new_sched)

    await db.commit()
    return {"message": f"Turno asignado correctamente a {len(assignment.employee_ids)} empleados."}


@router.get("/ledger", response_model=List[JournalEntryResponse])
async def list_journal_entries(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Listar todos los asientos contables generados (Libro Diario SAP FI)."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.lines)).order_by(JournalEntry.created_at.desc())
    )
    return result.scalars().all()


# ==========================================
# BUDGET MANAGEMENT ENDPOINTS
# ==========================================
@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    fiscal_year: Optional[int] = None,
    department: Optional[str] = None,
    budget_status: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar todos los presupuestos con sus líneas."""
    query = select(Budget)
    if fiscal_year:
        query = query.where(Budget.fiscal_year == fiscal_year)
    if department:
        query = query.where(Budget.department == department)
    if budget_status:
        query = query.where(Budget.status == budget_status)

    result = await db.execute(query.order_by(Budget.fiscal_year.desc(), Budget.name.asc()))
    budgets = result.scalars().all()

    response = []
    for b in budgets:
        lines_result = await db.execute(
            select(BudgetLine).where(BudgetLine.budget_id == b.id)
        )
        lines = lines_result.scalars().all()
        budget_resp = _build_budget_response(b, lines)
        response.append(budget_resp)
    return response


def _build_budget_response(budget: Budget, lines: list) -> BudgetResponse:
    return BudgetResponse(
        id=budget.id,
        name=budget.name,
        department=budget.department,
        fiscal_year=budget.fiscal_year,
        total_amount=budget.total_amount,
        spent_amount=budget.spent_amount,
        category=budget.category,
        status=budget.status,
        tenant_id=budget.tenant_id,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
        variance=budget.total_amount - budget.spent_amount,
        lines=[
            BudgetLineResponse(
                id=ln.id, budget_id=ln.budget_id,
                description=ln.description,
                planned_amount=ln.planned_amount,
                actual_amount=ln.actual_amount,
                category=ln.category,
                created_at=ln.created_at,
            ) for ln in lines
        ]
    )


async def _get_budget_with_lines(budget_id: str, db: AsyncSession) -> Optional[BudgetResponse]:
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        return None
    lines_result = await db.execute(
        select(BudgetLine).where(BudgetLine.budget_id == budget.id)
    )
    return _build_budget_response(budget, lines_result.scalars().all())


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_in: BudgetCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Crear un nuevo presupuesto."""
    budget = Budget(
        id=uuid.uuid4().hex,
        **budget_in.model_dump()
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return _build_budget_response(budget, [])


@router.get("/budgets/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    fiscal_year: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Resumen financiero: totales por departamento, restante, y porcentaje."""
    query = select(Budget)
    if fiscal_year:
        query = query.where(Budget.fiscal_year == fiscal_year)

    result = await db.execute(query)
    budgets = result.scalars().all()

    total_budgeted = sum(b.total_amount for b in budgets)
    total_spent = sum(b.spent_amount for b in budgets)

    by_department = {}
    for b in budgets:
        dept = b.department or "Sin departamento"
        if dept not in by_department:
            by_department[dept] = {"total": 0.0, "spent": 0.0}
        by_department[dept]["total"] += b.total_amount
        by_department[dept]["spent"] += b.spent_amount

    budget_responses = []
    for b in budgets:
        lines_result = await db.execute(
            select(BudgetLine).where(BudgetLine.budget_id == b.id)
        )
        lines = lines_result.scalars().all()
        budget_responses.append(_build_budget_response(b, lines))

    return BudgetSummaryResponse(
        total_budgeted=round(total_budgeted, 2),
        total_spent=round(total_spent, 2),
        total_remaining=round(total_budgeted - total_spent, 2),
        budget_count=len(budgets),
        by_department={k: v for k, v in by_department.items()},
        budgets=budget_responses
    )


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Obtener un presupuesto con sus líneas."""
    budget_resp = await _get_budget_with_lines(budget_id, db)
    if not budget_resp:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return budget_resp


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    budget_in: BudgetUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Actualizar un presupuesto."""
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    for field, value in budget_in.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)

    await db.commit()
    await db.refresh(budget)

    await _notify_budget_threshold(budget, db)

    lines_result = await db.execute(
        select(BudgetLine).where(BudgetLine.budget_id == budget.id)
    )
    return _build_budget_response(budget, lines_result.scalars().all())


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar un presupuesto (cascada a sus líneas)."""
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    await db.delete(budget)
    await db.commit()
    return None


@router.post("/budgets/{budget_id}/lines", response_model=BudgetLineResponse, status_code=status.HTTP_201_CREATED)
async def add_budget_line(
    budget_id: str,
    line_in: BudgetLineCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Agregar una línea de presupuesto."""
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    line = BudgetLine(
        id=uuid.uuid4().hex,
        budget_id=budget_id,
        **line_in.model_dump()
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


@router.put("/budgets/lines/{line_id}", response_model=BudgetLineResponse)
async def update_budget_line(
    line_id: str,
    line_in: BudgetLineUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Actualizar una línea de presupuesto."""
    result = await db.execute(select(BudgetLine).where(BudgetLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Línea de presupuesto no encontrada")

    for field, value in line_in.model_dump(exclude_unset=True).items():
        setattr(line, field, value)

    await db.commit()
    await db.refresh(line)

    budget_result = await db.execute(select(Budget).where(Budget.id == line.budget_id))
    budget = budget_result.scalar_one_or_none()
    if budget:
        await _notify_budget_threshold(budget, db)

    return line


@router.delete("/budgets/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget_line(
    line_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar una línea de presupuesto."""
    result = await db.execute(select(BudgetLine).where(BudgetLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Línea de presupuesto no encontrada")

    await db.delete(line)
    await db.commit()
    return None


@router.post("/budgets/{budget_id}/alert")
async def check_budget_alert(
    budget_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Verificar alertas de presupuesto (>80% gastado)."""
    result = await db.execute(select(Budget).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    pct_used = (budget.spent_amount / budget.total_amount * 100) if budget.total_amount > 0 else 0
    alert_triggered = pct_used > 80

    return {
        "budget_id": budget.id,
        "budget_name": budget.name,
        "total_amount": budget.total_amount,
        "spent_amount": budget.spent_amount,
        "remaining": budget.total_amount - budget.spent_amount,
        "pct_used": round(pct_used, 2),
        "alert": alert_triggered,
        "severity": "critical" if pct_used > 95 else "warning" if pct_used > 80 else "normal",
        "message": f"ALERTA: El presupuesto '{budget.name}' está al {pct_used:.1f}% de su capacidad." if alert_triggered else "Presupuesto en estado normal."
    }


async def _notify_budget_threshold(budget: Budget, db: AsyncSession):
    if budget.total_amount <= 0:
        return
    pct = round((budget.spent_amount / budget.total_amount) * 100, 1)
    if pct > 80:
        try:
            from app.services.broadcast import broadcast_notification
            await broadcast_notification(
                db,
                title=f"Budget Alert: {budget.name}",
                message=f"{budget.name} has used {pct}% of its budget",
                type_="system",
                role="hr_admin",
                link="/dashboard/finance?tab=budgets",
            )
        except Exception:
            pass


# ==========================================
# INVOICE MANAGEMENT ENDPOINTS
# ==========================================
def _generate_invoice_number(invoice_type: str) -> str:
    year = datetime.utcnow().strftime("%Y")
    prefix = "INV" if invoice_type == "payable" else "REC"
    return f"{prefix}-{year}-{uuid.uuid4().hex[:4].upper()}"


def _recalc_invoice(invoice: Invoice) -> None:
    invoice.total_amount = invoice.amount + invoice.tax_amount
    invoice.base_amount = round(invoice.total_amount * invoice.exchange_rate, 2)


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = None,
    type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """List invoices with optional filtering by status, type, and date range."""
    query = select(Invoice)
    if status:
        query = query.where(Invoice.status == status)
    if type:
        query = query.where(Invoice.type == type)
    if date_from:
        query = query.where(Invoice.issue_date >= date_from)
    if date_to:
        query = query.where(Invoice.issue_date <= date_to)

    result = await db.execute(query.order_by(Invoice.created_at.desc()))
    return result.scalars().all()


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Create a new invoice with auto-generated invoice number."""
    invoice = Invoice(
        id=uuid.uuid4().hex,
        invoice_number=_generate_invoice_number(invoice_in.type),
        **invoice_in.model_dump()
    )
    _recalc_invoice(invoice)
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.get("/invoices/aging")
async def get_invoice_aging(
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """AR/AP aging report: 0-30, 31-60, 61-90, 90+ days overdue."""
    query = select(Invoice).where(
        Invoice.status.in_(["sent", "overdue"]),
        Invoice.due_date.isnot(None)
    )
    if type:
        query = query.where(Invoice.type == type)

    result = await db.execute(query)
    invoices = result.scalars().all()

    now = date.today()
    buckets = {"0_30": [0.0, 0], "31_60": [0.0, 0], "61_90": [0.0, 0], "90_plus": [0.0, 0]}

    for inv in invoices:
        if inv.due_date is None:
            continue
        days_overdue = (now - inv.due_date).days
        base = float(inv.base_amount)

        if days_overdue <= 30:
            buckets["0_30"][0] += base
            buckets["0_30"][1] += 1
        elif days_overdue <= 60:
            buckets["31_60"][0] += base
            buckets["31_60"][1] += 1
        elif days_overdue <= 90:
            buckets["61_90"][0] += base
            buckets["61_90"][1] += 1
        else:
            buckets["90_plus"][0] += base
            buckets["90_plus"][1] += 1

    total = sum(b[0] for b in buckets.values())

    return InvoiceAgingResponse(
        bucket_0_30=round(buckets["0_30"][0], 2),
        bucket_31_60=round(buckets["31_60"][0], 2),
        bucket_61_90=round(buckets["61_90"][0], 2),
        bucket_90_plus=round(buckets["90_plus"][0], 2),
        total_outstanding=round(total, 2),
        count_0_30=buckets["0_30"][1],
        count_31_60=buckets["31_60"][1],
        count_61_90=buckets["61_90"][1],
        count_90_plus=buckets["90_plus"][1],
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Get a single invoice by ID."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Update an invoice."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    for field, value in invoice_in.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)

    _recalc_invoice(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Delete an invoice (only if draft)."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar facturas en estado draft")

    await db.delete(invoice)
    await db.commit()
    return None


@router.post("/invoices/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Mark an invoice as paid."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    invoice.status = "paid"
    invoice.paid_date = datetime.utcnow()
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/mark-overdue", response_model=InvoiceResponse)
async def mark_invoice_overdue(
    invoice_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Mark an invoice as overdue (admin only)."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    invoice.status = "overdue"
    await db.commit()
    await db.refresh(invoice)

    try:
        from app.services.broadcast import broadcast_notification
        await broadcast_notification(
            db,
            title=f"Invoice Overdue: {invoice.invoice_number}",
            message=f"Invoice {invoice.invoice_number} from {invoice.supplier or 'Unknown'} for {invoice.total_amount} is now overdue",
            type_="system",
            role="hr_admin",
            link="/dashboard/finance?tab=invoices",
        )
    except Exception:
        pass

    return invoice


# ==========================================
# MULTI-CURRENCY ENDPOINTS
# ==========================================
@router.get("/currencies", response_model=List[CurrencyRateResponse])
async def list_currencies(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """List all supported currency exchange rates."""
    result = await db.execute(select(CurrencyRate).order_by(CurrencyRate.code.asc()))

    rates = result.scalars().all()

    if not rates:
        eur = CurrencyRate(
            id=uuid.uuid4().hex,
            code="EUR",
            rate_to_eur=1.0,
        )
        usd = CurrencyRate(
            id=uuid.uuid4().hex,
            code="USD",
            rate_to_eur=0.92,
        )
        gbp = CurrencyRate(
            id=uuid.uuid4().hex,
            code="GBP",
            rate_to_eur=1.18,
        )
        mxn = CurrencyRate(
            id=uuid.uuid4().hex,
            code="MXN",
            rate_to_eur=0.054,
        )
        db.add_all([eur, usd, gbp, mxn])
        await db.commit()
        result = await db.execute(select(CurrencyRate).order_by(CurrencyRate.code.asc()))
        rates = result.scalars().all()

    return rates


@router.post("/currencies/convert", response_model=CurrencyConvertResponse)
async def convert_currency(
    convert_in: CurrencyConvertRequest,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Convert an amount between two currencies using stored exchange rates."""
    if convert_in.from_currency == convert_in.to_currency:
        return CurrencyConvertResponse(
            from_currency=convert_in.from_currency,
            to_currency=convert_in.to_currency,
            original_amount=convert_in.amount,
            converted_amount=convert_in.amount,
            rate=1.0,
        )

    # Get rate for from_currency -> EUR
    result = await db.execute(
        select(CurrencyRate).where(CurrencyRate.code == convert_in.from_currency)
    )
    from_rate = result.scalar_one_or_none()
    if not from_rate:
        raise HTTPException(status_code=400, detail=f"Moneda no soportada: {convert_in.from_currency}")

    # Get rate for to_currency -> EUR
    result = await db.execute(
        select(CurrencyRate).where(CurrencyRate.code == convert_in.to_currency)
    )
    to_rate = result.scalar_one_or_none()
    if not to_rate:
        raise HTTPException(status_code=400, detail=f"Moneda no soportada: {convert_in.to_currency}")

    amount_in_eur = convert_in.amount * from_rate.rate_to_eur
    converted = amount_in_eur / to_rate.rate_to_eur
    effective_rate = from_rate.rate_to_eur / to_rate.rate_to_eur

    return CurrencyConvertResponse(
        from_currency=convert_in.from_currency,
        to_currency=convert_in.to_currency,
        original_amount=convert_in.amount,
        converted_amount=round(converted, 2),
        rate=round(effective_rate, 6),
    )


@router.get("/currencies/refresh")
async def refresh_currency_rates(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Fetch latest exchange rates from exchangerate-api.com and update DB (admin only)."""
    import httpx
    import asyncio

    # Delete existing rates to replace
    existing = await db.execute(select(CurrencyRate))
    for r in existing.scalars().all():
        await db.delete(r)

    eur = CurrencyRate(id=uuid.uuid4().hex, code="EUR", rate_to_eur=1.0)
    db.add(eur)

    codes_to_fetch = ["USD", "GBP", "MXN", "JPY", "CHF", "CAD", "AUD", "CNY", "BRL", "ARS"]
    updated = ["EUR"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://open.er-api.com/v6/latest/EUR")
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                for code in codes_to_fetch:
                    rate = rates.get(code)
                    if rate:
                        db.add(CurrencyRate(
                            id=uuid.uuid4().hex,
                            code=code,
                            rate_to_eur=round(1.0 / rate, 6),
                        ))
                        updated.append(code)
    except Exception:
        # Fallback: add seed rates
        fallback = {
            "USD": 0.92, "GBP": 1.18, "MXN": 0.054, "JPY": 0.0062,
            "CHF": 1.03, "CAD": 0.68, "AUD": 0.61, "CNY": 0.13,
            "BRL": 0.19, "ARS": 0.0011,
        }
        for code, rate in fallback.items():
            db.add(CurrencyRate(id=uuid.uuid4().hex, code=code, rate_to_eur=rate))
            updated.append(code)

    await db.commit()

    result = await db.execute(select(CurrencyRate).order_by(CurrencyRate.code.asc()))
    rates = result.scalars().all()

    return {
        "success": True,
        "updated_currencies": updated,
        "rates": [{"code": r.code, "rate_to_eur": r.rate_to_eur} for r in rates],
    }


# ── Forecasting ────────────────────────────────────────────────────────────────

@router.get("/forecast/cash-flow")
async def forecast_cashflow(
    months: int = Query(default=12, ge=1, le=36),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_forecasting import forecast_cash_flow
    tenant_id = current_user.get("tenant_id", "default")
    forecast = await forecast_cash_flow(tenant_id, db, months_ahead=months)
    return {"forecast": [f.model_dump() for f in forecast]}


@router.get("/forecast/budget-variance")
async def budget_variance(
    period_start: Optional[str] = Query(default=None),
    period_end: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_forecasting import analyze_budget_variance
    tenant_id = current_user.get("tenant_id", "default")
    variances = await analyze_budget_variance(tenant_id, db, period_start, period_end)
    total_variance = sum(v.variance for v in variances)
    return {
        "variances": [v.model_dump() for v in variances],
        "total_variance": total_variance,
        "count": len(variances),
    }


@router.get("/forecast/anomalies")
async def anomaly_detection(
    lookback_days: int = Query(default=90, ge=7, le=730),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_forecasting import detect_anomalies
    tenant_id = current_user.get("tenant_id", "default")
    anomalies = await detect_anomalies(tenant_id, db, lookback_days)
    return {"anomalies": [a.model_dump() for a in anomalies], "count": len(anomalies)}


@router.get("/forecast/report")
async def financial_summary(
    report_type: str = Query(default="summary"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_forecasting import generate_financial_report
    tenant_id = current_user.get("tenant_id", "default")
    return await generate_financial_report(tenant_id, db, report_type)


# ── Expense OCR ────────────────────────────────────────────────────────────────

class ReceiptScanRequest(BaseModel):
    text: Optional[str] = None
    image_base64: Optional[str] = None

@router.post("/expenses/scan-receipt")
async def scan_receipt(
    body: ReceiptScanRequest,
    current_user: dict = Depends(get_current_user),
):
    from app.services.expense_ocr import scan_receipt_text, scan_receipt_image
    if body.image_base64:
        result = await scan_receipt_image(body.image_base64)
    elif body.text:
        result = await scan_receipt_text(body.text)
    else:
        raise HTTPException(status_code=400, detail="Provide text or image_base64")
    if not result:
        raise HTTPException(status_code=422, detail="Could not extract receipt data")
    return {"receipt": result.model_dump()}


@router.post("/expenses/categorize")
async def categorize_expense_endpoint(
    description: str = Query(...),
    amount: float = Query(...),
    current_user: dict = Depends(get_current_user),
):
    from app.services.expense_ocr import categorize_expense
    category = await categorize_expense(description, amount)
    return {"category": category}


