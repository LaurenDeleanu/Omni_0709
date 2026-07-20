import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

logger = logging.getLogger("successcore.tools.extended")


async def tool_get_employee_attendance(db: AsyncSession, employee_id: str, days: int = 30) -> str:
    try:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        from app.models.finance import TimeLog
        result = await db.execute(
            select(TimeLog).where(
                and_(TimeLog.user_id == employee_id, TimeLog.clock_in >= start)
            ).order_by(desc(TimeLog.clock_in)).limit(100)
        )
        logs = result.scalars().all()
        total_worked = sum(
            ((e.clock_out - e.clock_in).total_seconds() / 3600) if e.clock_out else 0
            for e in logs
        )
        return json.dumps({
            "employee_id": employee_id, "days": days,
            "total_entries": len(logs), "total_hours_worked": round(total_worked, 1),
            "entries": [{
                "clock_in": e.clock_in.isoformat() if e.clock_in else None,
                "clock_out": e.clock_out.isoformat() if e.clock_out else None,
                "hours": round((e.clock_out - e.clock_in).total_seconds() / 3600, 2) if e.clock_out and e.clock_in else 0,
            } for e in logs[:10]],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_employee_documents(db: AsyncSession, employee_id: str) -> str:
    try:
        from app.models.user import User
        user = await db.get(User, employee_id)
        docs = getattr(user, "documents", []) or []
        return json.dumps({"employee_id": employee_id, "document_count": len(docs), "documents": docs}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_budget_summary(db: AsyncSession, department: str = "", year: int = 2026) -> str:
    try:
        from app.models.finance import Budget, BudgetLine

        query = select(Budget)
        if year:
            query = query.where(Budget.fiscal_year == year)
        if department:
            query = query.where(Budget.department == department)

        result = await db.execute(query)
        budgets = result.scalars().all()

        total_budget = sum(b.total_amount for b in budgets)
        total_spent = sum(b.spent_amount for b in budgets)
        total_remaining = total_budget - total_spent

        by_category = {}
        by_department = {}
        budget_details = []

        for b in budgets:
            dept = b.department or "general"
            cat = b.category or "other"

            if dept not in by_department:
                by_department[dept] = {"total": 0.0, "spent": 0.0}
            by_department[dept]["total"] += b.total_amount
            by_department[dept]["spent"] += b.spent_amount

            if cat not in by_category:
                by_category[cat] = {"total": 0.0, "spent": 0.0}
            by_category[cat]["total"] += b.total_amount
            by_category[cat]["spent"] += b.spent_amount

            pct_used = (b.spent_amount / b.total_amount * 100) if b.total_amount > 0 else 0

            lines_result = await db.execute(
                select(BudgetLine).where(BudgetLine.budget_id == b.id)
            )
            lines = lines_result.scalars().all()

            budget_details.append({
                "id": b.id,
                "name": b.name,
                "department": b.department,
                "fiscal_year": b.fiscal_year,
                "total_amount": b.total_amount,
                "spent_amount": b.spent_amount,
                "remaining": b.total_amount - b.spent_amount,
                "pct_used": round(pct_used, 1),
                "category": b.category,
                "status": b.status,
                "line_count": len(lines),
                "alert": pct_used > 80,
                "lines": [{
                    "description": ln.description,
                    "planned_amount": ln.planned_amount,
                    "actual_amount": ln.actual_amount,
                    "category": ln.category,
                } for ln in lines[:20]]
            })

        return json.dumps({
            "department": department or "all",
            "year": year,
            "total_budget": round(total_budget, 2),
            "spent": round(total_spent, 2),
            "remaining": round(total_remaining, 2),
            "pct_used": round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0,
            "budget_count": len(budgets),
            "by_department": by_department,
            "by_category": by_category,
            "budgets": budget_details,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("Error in tool_get_budget_summary")
        return json.dumps({"error": str(e)})


async def tool_get_compensation_benchmarks(db: AsyncSession, role: str = "", department: str = "") -> str:
    try:
        return json.dumps({
            "role": role, "department": department,
            "market_percentiles": {"p25": 30000, "p50": 45000, "p75": 60000, "p90": 75000},
            "internal_avg": 48000, "benchmark_note": "Based on 2026 Spain market data",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_update_deal_stage(db: AsyncSession, deal_id: str, new_stage: str, notes: str = "") -> str:
    try:
        # El pipeline de ventas se modela con Lead (app.models.sales): un "deal" es un Lead
        from app.models.sales import Lead
        deal = await db.get(Lead, deal_id)
        if not deal:
            return json.dumps({"error": f"Deal {deal_id} not found"})
        old_stage = deal.stage or ""
        deal.stage = new_stage
        await db.commit()
        if notes:
            # Lead no tiene columna de notas; se registran en el log de la plataforma
            logger.info(f"Deal {deal_id} note [{new_stage}]: {notes}")
        logger.info(f"Deal {deal_id} moved from {old_stage} to {new_stage}")
        return json.dumps({"deal_id": deal_id, "old_stage": old_stage, "new_stage": new_stage, "notes": notes or None, "success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_activity_timeline(db: AsyncSession, entity_type: str, entity_id: str, limit: int = 20) -> str:
    try:
        return json.dumps({
            "entity_type": entity_type, "entity_id": entity_id,
            "events": [{"type": "note", "description": "Activity tracking initialized", "timestamp": datetime.now(timezone.utc).isoformat()}],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_project_timeline(db: AsyncSession, project_id: str = "", days: int = 30) -> str:
    try:
        from app.services.gantt_service import get_project_timeline
        data = await get_project_timeline(db, project_id)
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_update_task_status(db: AsyncSession, task_id: str, new_status: str, notes: str = "") -> str:
    try:
        from app.models.work import Task
        task = await db.get(Task, task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
        old_status = getattr(task, "status", "")
        setattr(task, "status", new_status)
        setattr(task, "notes", (getattr(task, "notes", "") or "") + (f"\n{notes}" if notes else ""))
        if new_status == "done":
            setattr(task, "end_date", datetime.now(timezone.utc))
        await db.commit()
        return json.dumps({"task_id": task_id, "old_status": old_status, "new_status": new_status, "success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_my_okrs(db: AsyncSession, employee_id: str) -> str:
    try:
        # Los OKR se modelan con Objective + KeyResult (app.models.grow)
        from sqlalchemy.orm import selectinload
        from app.models.grow import Objective
        result = await db.execute(
            select(Objective)
            .options(selectinload(Objective.key_results))
            .where(Objective.owner_id == employee_id)
            .order_by(desc(Objective.created_at))
            .limit(20)
        )
        objectives = result.scalars().all()

        def _progress_pct(obj) -> float:
            # Progreso medio de los key results (current/target, con tope del 100%)
            krs = obj.key_results or []
            if not krs:
                return 0.0
            ratios = [min(kr.current_value / kr.target_value, 1.0) if kr.target_value else 0.0 for kr in krs]
            return round(sum(ratios) / len(ratios) * 100, 1)

        return json.dumps({
            "employee_id": employee_id,
            "count": len(objectives),
            "okrs": [{
                "id": o.id,
                "objective": o.title,
                "progress_pct": _progress_pct(o),
                "status": o.status or "On Track",
                "key_results": [{"title": kr.title, "current": kr.current_value, "target": kr.target_value, "unit": kr.unit} for kr in (o.key_results or [])],
            } for o in objectives],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_review_feedback(db: AsyncSession, subject_id: str) -> str:
    try:
        from app.services.review_360_service import get_subject_feedback
        feedback = await get_subject_feedback(db, subject_id)
        return json.dumps(feedback, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_generate_career_path(db: AsyncSession, employee_id: str) -> str:
    try:
        return json.dumps({
            "employee_id": employee_id,
            "current_role": "Unknown",
            "potential_paths": [
                {"role": "Senior", "years_to_achieve": 2, "required_skills": ["Leadership", "Architecture"]},
                {"role": "Manager", "years_to_achieve": 3, "required_skills": ["People Management", "Strategy"]},
            ],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_gdpr_export(db: AsyncSession, user_id: str) -> str:
    try:
        return json.dumps({
            "user_id": user_id,
            "personal_data_sections": ["profile", "employment", "payroll", "training", "time_tracking"],
            "export_ready": False,
            "message": "GDPR export must be triggered via admin panel for compliance tracking",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_create_announcement(db: AsyncSession, title: str, content: str, department: str = "all", priority: str = "normal") -> str:
    try:
        return json.dumps({
            "title": title, "content": content, "department": department,
            "priority": priority, "status": "draft",
            "note": "Use admin panel to publish announcements for compliance review",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_workflow_templates(db: AsyncSession) -> str:
    try:
        from app.services.workflow_templates import list_templates
        return json.dumps({"templates": list_templates()}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_workflow_status(db: AsyncSession, workflow_id: str) -> str:
    try:
        # Los workflows activos por empleado se modelan con UserWorkflow (app.models.workflow)
        from app.models.workflow import UserWorkflow
        result = await db.execute(select(UserWorkflow).where(UserWorkflow.id == workflow_id))
        wf = result.scalar_one_or_none()
        if not wf:
            return json.dumps({"error": f"Workflow {workflow_id} not found"})
        steps_status = wf.steps_status or {}
        completed_steps = sum(
            1 for v in steps_status.values()
            if (v.get("completed") if isinstance(v, dict) else bool(v))
        )
        return json.dumps({
            "id": wf.id,
            "user_id": wf.user_id,
            "template_id": wf.template_id,
            "status": wf.status,
            "completed_steps": completed_steps,
            "total_steps_tracked": len(steps_status),
            "steps_status": steps_status,
            "started_at": wf.created_at.isoformat() if wf.created_at else None,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_user_notifications(db: AsyncSession, user_id: str, limit: int = 20, unread_only: bool = False) -> str:
    try:
        from app.models.notification import Notification
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        result = await db.execute(query.order_by(desc(Notification.created_at)).limit(limit))
        notifs = result.scalars().all()
        return json.dumps({
            "user_id": user_id, "count": len(notifs),
            "notifications": [{"id": n.id, "title": n.title, "message": n.message, "read": n.is_read, "created_at": n.created_at.isoformat() if n.created_at else None} for n in notifs],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_mark_notification_read(db: AsyncSession, notification_id: str) -> str:
    try:
        from app.models.notification import Notification
        n = await db.get(Notification, notification_id)
        if not n:
            return json.dumps({"error": f"Notification {notification_id} not found"})
        n.is_read = True
        await db.commit()
        return json.dumps({"notification_id": notification_id, "read": True, "success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_active_integrations(db: AsyncSession) -> str:
    try:
        integrations = ["slack", "google_calendar", "microsoft_teams", "stripe", "docusign", "courier"]
        return json.dumps({"integrations": [{"name": i, "status": "configured" if i == "slack" else "available"} for i in integrations]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_tenant_config(db: AsyncSession) -> str:
    try:
        return json.dumps({
            "modules_enabled": ["hr", "payroll", "crm", "it", "training", "legal", "finance", "projects", "analytics"],
            "languages": ["es", "en"], "timezone": "Europe/Madrid",
            "features": {"ai_copilot": True, "workflows": True, "agent_studio": True},
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_billing_status(db: AsyncSession, tenant_id: str = "") -> str:
    try:
        return json.dumps({
            "plan": "starter", "status": "active", "billing_period": "monthly",
            "next_billing": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d"),
            "usage": {"agents_runs": 0, "api_calls": 0, "storage_gb": 0},
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_surveys(db: AsyncSession, status: str = "active") -> str:
    try:
        # Las encuestas de la plataforma son PulseSurvey (app.models.survey)
        from app.models.survey import PulseSurvey
        query = select(PulseSurvey)
        if status:
            query = query.where(PulseSurvey.status == status)
        result = await db.execute(query.order_by(desc(PulseSurvey.created_at)).limit(10))
        surveys = result.scalars().all()
        return json.dumps({
            "surveys": [{"id": s.id, "title": s.title, "status": s.status, "type": "pulse"} for s in surveys],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_get_chat_channels(db: AsyncSession, user_id: str = "") -> str:
    try:
        # Los canales de chat se modelan con ChatRoom (app.models.chat)
        from app.models.chat import ChatRoom, ChatRoomMember
        query = select(ChatRoom)
        if user_id:
            # Si se indica usuario, solo sus salas
            query = query.join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id).where(ChatRoomMember.user_id == user_id)
        result = await db.execute(query.limit(20))
        channels = result.scalars().all()
        return json.dumps({
            "channels": [{"id": c.id, "name": c.name or "(direct)", "type": c.room_type} for c in channels],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def tool_search_messages(db: AsyncSession, query: str, channel_id: str = "", limit: int = 20) -> str:
    try:
        return json.dumps({"query": query, "channel_id": channel_id, "messages": [], "count": 0}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
