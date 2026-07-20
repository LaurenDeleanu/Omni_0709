import logging
import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.it import ITTicket
from app.models.calendar import VacationRequest
from app.services.tool_registry import register_tool
from app.services.tool_acl import enforce_tool_acl, DESTRUCTIVE_TOOLS
from app.services.agent_workflow_bridge import _tool_trigger_workflow, _tool_complete_workflow_step
from app.services.it_knowledge_base import (
    search_kb_articles as it_kb_search,
    auto_tag_ticket as it_kb_auto_tag,
    suggest_solutions as it_kb_suggest,
)
from app.services.platform_tools_business import (
    tool_enroll_in_course,
    tool_get_training_progress,
    tool_get_course_catalog,
    tool_recommend_courses,
    tool_validate_fundae,
    tool_create_job_posting,
    tool_add_candidate,
    tool_move_candidate_stage,
    tool_schedule_interview,
    tool_get_job_applications,
    tool_get_pipeline_stats,
    tool_promote_to_employee,
    tool_create_okr,
    tool_update_key_result,
    tool_create_review,
    tool_get_team_okrs,
    tool_get_kudos_received,
    tool_get_pipeline_overview,
    tool_get_client_details,
    tool_search_clients,
    tool_get_deal_stats,
    tool_create_task_for_lead,
    tool_log_lead_activity,
    tool_create_project,
    tool_create_project_task,
    tool_get_project_status,
    tool_create_wiki_page,
    tool_get_contracts,
    tool_get_compliance_status,
    tool_submit_whistleblower,
)
from app.services.platform_tools_hr import (
    tool_create_employee, tool_update_employee, tool_archive_employee,
    tool_search_employees, tool_get_employee_profile, tool_get_org_chart,
    tool_get_span_of_control, tool_get_pto_balance, tool_get_department_members,
    tool_get_recent_hires,
    tool_request_vacation, tool_approve_vacation, tool_get_team_calendar,
    tool_create_meeting, tool_get_work_schedule,
    tool_create_payroll_cycle, tool_process_payroll, tool_get_payslip,
    tool_get_tax_rules, tool_update_compensation, tool_create_bonus,
    tool_get_financial_ledger, tool_get_expense_summary,
    tool_clock_in, tool_clock_out, tool_get_time_logs,
    tool_assign_it_ticket, tool_resolve_it_ticket, tool_get_it_assets,
    tool_get_ticket_stats,
)

logger = logging.getLogger(__name__)

async def get_employee_profile(db: AsyncSession, email: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """
    Busca el perfil de un empleado por correo o por ID.
    """
    try:
        query = select(User)
        if email:
            query = query.where(User.email == email)
        elif user_id:
            query = query.where(User.id == user_id)
        else:
            return json.dumps({"error": "Debe especificar 'email' o 'user_id'"})
            
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return json.dumps({"error": "Empleado no encontrado"})
            
        return json.dumps({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role,
            "vacation_allowance": user.vacation_allowance,
            "is_active": user.is_active,
            "phone_number": user.phone_number,
            "contract_type": user.contract_type,
            "hire_date": user.hire_date.isoformat() if user.hire_date else None
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool get_employee_profile: {e}")
        return json.dumps({"error": f"Fallo al buscar perfil: {str(e)}"})

async def list_department_members(db: AsyncSession, department: str) -> str:
    """
    Lista todos los empleados en un departamento específico.
    """
    try:
        query = select(User).where(User.department == department, User.is_active == True)
        result = await db.execute(query)
        users = result.scalars().all()
        
        members = []
        for u in users:
            members.append({
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role
            })
            
        return json.dumps({"department": department, "count": len(members), "members": members}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool list_department_members: {e}")
        return json.dumps({"error": f"Fallo al listar departamento: {str(e)}"})

async def get_vacation_balance(db: AsyncSession, user_id: str = "", email: str = "") -> str:
    try:
        if email and not user_id:
            result = await db.execute(select(User).where(User.email == email))
            u = result.scalar_one_or_none()
            if u:
                user_id = u.id
        user_query = select(User).where(User.id == user_id)
        u_res = await db.execute(user_query)
        user = u_res.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "Usuario no encontrado"})
            
        req_query = select(VacationRequest).where(VacationRequest.user_id == user_id)
        req_res = await db.execute(req_query)
        requests = req_res.scalars().all()
        
        req_list = []
        days_used = 0
        for r in requests:
            req_list.append({
                "id": r.id,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "status": r.status, # pending, approved, rejected
                "days": r.days_requested
            })
            if r.status == "approved":
                days_used += r.days_requested
                
        return json.dumps({
            "user_id": user_id,
            "full_name": user.full_name,
            "total_allowance": user.vacation_allowance,
            "days_used": days_used,
            "days_remaining": max(0, user.vacation_allowance - days_used),
            "history": req_list
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool get_vacation_balance: {e}")
        return json.dumps({"error": f"Fallo al obtener balance de vacaciones: {str(e)}"})

async def create_it_ticket(db: AsyncSession, requester_id: str, title: str, description: str, category: str = "Hardware") -> str:
    """
    Crea un ticket de soporte técnico (IT Ticket) en la plataforma.
    """
    try:
        import uuid
        ticket = ITTicket(
            id=uuid.uuid4().hex,
            title=title,
            description=description,
            category=category,
            priority="Medium",
            status="Open",
            requester_id=requester_id
        )
        db.add(ticket)
        await db.commit()
        return json.dumps({
            "success": True,
            "ticket_id": ticket.id,
            "title": ticket.title,
            "status": ticket.status,
            "message": "Ticket de IT creado exitosamente."
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool create_it_ticket: {e}")
        return json.dumps({"error": f"Fallo al crear ticket: {str(e)}"})


async def search_employees(db: AsyncSession, query: str) -> str:
    try:
        result = await db.execute(select(User).where(User.full_name.ilike(f"%{query}%") | User.email.ilike(f"%{query}%")).limit(10))
        users = result.scalars().all()
        return json.dumps([{"id": u.id, "email": u.email, "name": u.full_name, "department": u.department, "role": u.role} for u in users], ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

async def get_department_stats(db: AsyncSession, department: str) -> str:
    try:
        result = await db.execute(select(User).where(User.department == department, User.is_active == True))
        users = result.scalars().all()
        total = len(users)
        avg = round(sum(u.base_salary or 0 for u in users) / max(total, 1), 2)
        return json.dumps({"department": department, "headcount": total, "avg_salary": avg})
    except Exception as e:
        return json.dumps({"error": str(e)})

async def get_expense_summary(db: AsyncSession, user_email: str) -> str:
    try:
        from app.models.finance import ExpenseClaim
        user_res = await db.execute(select(User).where(User.email == user_email))
        user = user_res.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "User not found"})
        result = await db.execute(select(ExpenseClaim).where(ExpenseClaim.user_id == user.id).order_by(ExpenseClaim.created_at.desc()).limit(10))
        claims = result.scalars().all()
        return json.dumps([{"id": c.id, "category": c.category, "amount": c.total_amount, "status": c.status, "created": c.created_at.isoformat() if c.created_at else None} for c in claims], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

async def get_training_progress(db: AsyncSession, user_email: str) -> str:
    try:
        from app.models.training import CourseEnrollment, Course
        user_res = await db.execute(select(User).where(User.email == user_email))
        user = user_res.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "User not found"})
        result = await db.execute(select(CourseEnrollment).where(CourseEnrollment.user_id == user.id).limit(10))
        enrollments = result.scalars().all()
        data = []
        for e in enrollments:
            c = (await db.execute(select(Course).where(Course.id == e.course_id))).scalar_one_or_none()
            data.append({"course": c.title if c else "Unknown", "status": e.status, "enrolled": e.enrolled_at.isoformat() if e.enrolled_at else None})
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

async def get_company_announcements(db: AsyncSession, limit: int = 5) -> str:
    try:
        from app.models.announcement import Announcement
        result = await db.execute(select(Announcement).where(Announcement.is_active == True).order_by(Announcement.created_at.desc()).limit(limit))
        return json.dumps([{"id": a.id, "title": a.title, "content": a.content[:200]} for a in result.scalars().all()], ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

async def get_upcoming_vacations(db: AsyncSession, department: str) -> str:
    try:
        from datetime import datetime, timezone as tz
        result = await db.execute(select(VacationRequest).where(VacationRequest.status == "approved", VacationRequest.start_date >= datetime.now(tz.utc)).limit(10))
        vacs = result.scalars().all()
        return json.dumps([{"user_id": v.user_id, "start": v.start_date.isoformat() if v.start_date else None, "end": v.end_date.isoformat() if v.end_date else None, "days": v.days_requested} for v in vacs], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

async def get_kudos_leaderboard(db: AsyncSession, limit: int = 5) -> str:
    try:
        from app.models.kudos import Kudos
        from sqlalchemy import func
        result = await db.execute(select(Kudos.receiver_id, func.count(Kudos.id).label("count")).group_by(Kudos.receiver_id).order_by(func.count(Kudos.id).desc()).limit(limit))
        rows = result.all()
        data = []
        for receiver_id, count in rows:
            u = (await db.execute(select(User).where(User.id == receiver_id))).scalar_one_or_none()
            data.append({"name": u.full_name or u.email if u else receiver_id, "kudos": count})
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def create_client(db: AsyncSession, name: str, email: str, contact_person: str = "", phone: str = "") -> str:
    try:
        import uuid
        from datetime import datetime, timezone
        from sqlalchemy import text as sa_text
        # Use ORM model to respect schema translate map
        from app.models.sales import Client
        cid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        db.add(Client(
            id=cid,
            company_name=name,
            primary_contact_name=contact_person or name,
            primary_contact_email=email,
            primary_contact_phone=phone,
            created_at=now
        ))
        await db.commit()
        return json.dumps({"success": True, "client_id": cid, "name": name, "message": f"Cliente '{name}' creado exitosamente"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def book_vacation(db: AsyncSession, user_email: str, start_date: str, end_date: str, days: int = 1) -> str:
    try:
        import uuid
        from app.models.calendar import VacationRequest
        user_res = await db.execute(select(User).where(User.email == user_email))
        user = user_res.scalar_one_or_none()
        if not user:
            return json.dumps({"error": f"Usuario {user_email} no encontrado"})
        vid = str(uuid.uuid4())
        db.add(VacationRequest(id=vid, user_id=user.id, start_date=start_date, end_date=end_date, status="pending"))
        await db.commit()
        return json.dumps({"success": True, "vacation_id": vid, "message": f"Vacaciones solicitadas del {start_date} al {end_date}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def create_kudos(db: AsyncSession, receiver_email: str, sender_email: str, message: str, badge: str = "⭐") -> str:
    try:
        import uuid
        from app.models.kudos import Kudos
        receiver = (await db.execute(select(User).where(User.email == receiver_email))).scalar_one_or_none()
        sender = (await db.execute(select(User).where(User.email == sender_email))).scalar_one_or_none()
        if not receiver:
            return json.dumps({"error": f"Destinatario {receiver_email} no encontrado"})
        kid = str(uuid.uuid4())
        db.add(Kudos(id=kid, sender_id=sender.id if sender else "unknown", receiver_id=receiver.id, message=message, badge=badge))
        await db.commit()
        return json.dumps({"success": True, "message": f"Kudos enviado a {receiver.full_name or receiver_email}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def create_expense(db: AsyncSession, user_email: str, amount: float, category: str, description: str = "") -> str:
    try:
        import uuid
        from app.models.finance import ExpenseClaim
        user_res = await db.execute(select(User).where(User.email == user_email))
        user = user_res.scalar_one_or_none()
        if not user:
            return json.dumps({"error": f"Usuario {user_email} no encontrado"})
        eid = str(uuid.uuid4())
        db.add(ExpenseClaim(id=eid, user_id=user.id, total_amount=amount, category=category, description=description, status="pending"))
        await db.commit()
        return json.dumps({"success": True, "expense_id": eid, "message": f"Gasto de {amount} registrado en {category}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def create_task(db: AsyncSession, title: str, description: str = "", assigned_to_email: str = "", priority: str = "medium") -> str:
    try:
        import uuid
        from app.models.calendar import Task
        assigned_id = None
        if assigned_to_email:
            u = (await db.execute(select(User).where(User.email == assigned_to_email))).scalar_one_or_none()
            if u:
                assigned_id = u.id
        tid = str(uuid.uuid4())
        db.add(Task(id=tid, title=title, description=description, assigned_to=assigned_id, priority=priority, status="pending"))
        await db.commit()
        return json.dumps({"success": True, "task_id": tid, "message": f"Tarea '{title}' creada"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def get_agent_name(agent_id: str, db: AsyncSession) -> str:
    try:
        from app.models.agent import Agent
        agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent:
            return agent.name
        return "Unknown Agent"
    except Exception:
        return "Unknown Agent"


AVAILABLE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_employee_profile",
            "description": "Get detailed profile of an employee by email or user ID. Returns full name, department, role, vacation allowance, and contact info.",
            "parameters": {"type": "object", "properties": {"email": {"type": "string"}, "user_id": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_department_members",
            "description": "List all members of a specific department. Returns employee IDs, names, emails, and roles.",
            "parameters": {"type": "object", "properties": {"department": {"type": "string", "description": "Department name"}}, "required": ["department"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vacation_balance",
            "description": "Get the remaining vacation balance for an employee by email or user ID.",
            "parameters": {"type": "object", "properties": {"email": {"type": "string"}, "user_id": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_it_ticket",
            "description": "Create an IT support ticket for an employee.",
            "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "priority": {"type": "string"}, "user_email": {"type": "string"}}, "required": ["title", "description"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_employees",
            "description": "Search employees by name or email. Returns matching employees with basic info.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_department_stats",
            "description": "Get department statistics including headcount and average salary.",
            "parameters": {"type": "object", "properties": {"department": {"type": "string"}}, "required": ["department"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense_summary",
            "description": "Get recent expense claims summary for an employee.",
            "parameters": {"type": "object", "properties": {"user_email": {"type": "string"}}, "required": ["user_email"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_training_progress",
            "description": "Get training enrollment progress for an employee by employee ID. Returns course name, status, progress_pct, score, and completed_at for each enrollment.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}}, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_announcements",
            "description": "Get recent company announcements. Useful for agents to reference company news.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_vacations",
            "description": "Get approved upcoming vacation requests. Useful for planning coverage.",
            "parameters": {"type": "object", "properties": {"department": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_kudos_leaderboard",
            "description": "Get top kudos receivers leaderboard.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_onboarding_plan",
            "description": "Generate a personalized AI-guided onboarding plan for a new employee based on role, department, location, and seniority.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}}, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_onboarding_buddy",
            "description": "Assign an onboarding buddy for a new employee. Finds the best match in the same department using AI ranking.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}}, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_client",
            "description": "Register a new client/company in the CRM.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}, "email": {"type": "string"},
                "contact_person": {"type": "string"}, "phone": {"type": "string"}
            }, "required": ["name", "email"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_vacation",
            "description": "Request vacation days for an employee.",
            "parameters": {"type": "object", "properties": {
                "user_email": {"type": "string"}, "start_date": {"type": "string"},
                "end_date": {"type": "string"}, "days": {"type": "integer"}
            }, "required": ["user_email", "start_date", "end_date"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_kudos",
            "description": "Send recognition/kudos to a colleague.",
            "parameters": {"type": "object", "properties": {
                "receiver_email": {"type": "string"}, "sender_email": {"type": "string"},
                "message": {"type": "string"}, "badge": {"type": "string"}
            }, "required": ["receiver_email", "sender_email", "message"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_expense",
            "description": "Create an expense claim for reimbursement.",
            "parameters": {"type": "object", "properties": {
                "user_email": {"type": "string"}, "amount": {"type": "number"},
                "category": {"type": "string"}, "description": {"type": "string"}
            }, "required": ["user_email", "amount", "category"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a task/reminder.",
            "parameters": {"type": "object", "properties": {
                "title": {"type": "string"}, "description": {"type": "string"},
                "assigned_to_email": {"type": "string"}, "priority": {"type": "string"}
            }, "required": ["title"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_resume",
            "description": "Parse a candidate's resume file (PDF, DOCX, TXT) and extract structured data: name, email, phone, skills, experience, education, languages, current title/company, and LinkedIn.",
            "parameters": {"type": "object", "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the uploaded resume file"},
                "model": {"type": "string", "description": "LLM model to use for parsing (default: gpt-4o-mini)"}
            }, "required": ["file_path"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "match_candidate_to_job",
            "description": "Score a parsed candidate profile against job requirements (0-100). Returns matching skills, missing skills, fit summary, and recommendation.",
            "parameters": {"type": "object", "properties": {
                "candidate_data": {"type": "object", "description": "Parsed candidate profile with skills, experience, education fields"},
                "job_requirements": {"type": "string", "description": "Job title, department, and full description text"}
            }, "required": ["candidate_data", "job_requirements"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "screen_resume",
            "description": "Full resume screening pipeline: parse resume file and optionally match against a job posting to get a fit score.",
            "parameters": {"type": "object", "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the uploaded resume file"},
                "job_id": {"type": "string", "description": "Optional job posting ID to match the candidate against"}
            }, "required": ["file_path"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_workflow",
            "description": "Start an onboarding or offboarding workflow for a user. Use this when asked to onboard or offboard an employee.",
            "parameters": {"type": "object", "properties": {
                "user_id": {"type": "string", "description": "User ID of the employee"},
                "workflow_template_id": {"type": "string", "description": "Workflow template ID to start"},
                "template_name": {"type": "string", "description": "Workflow template name to search by (e.g. 'Onboarding')"}
            }, "required": ["user_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_workflow_step",
            "description": "Mark a specific step in a user workflow as completed. Use this to advance an employee through onboarding/offboarding.",
            "parameters": {"type": "object", "properties": {
                "workflow_id": {"type": "string", "description": "ID of the user workflow"},
                "step_id": {"type": "string", "description": "ID of the step to mark complete"},
                "completed_by": {"type": "string", "description": "User ID or name of who completed the step"}
            }, "required": ["workflow_id", "step_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_workflow_from_description",
            "description": "Generate a complete onboarding/offboarding workflow from a natural language description. Describe the process and the system creates all steps automatically.",
            "parameters": {"type": "object", "properties": {
                "description": {"type": "string", "description": "Natural language description of the process, e.g. 'When a new employee is hired, send welcome email, assign onboarding tasks, create IT ticket for laptop, schedule 30-day check-in'"},
                "name": {"type": "string", "description": "Name for the new workflow template"}
            }, "required": ["description", "name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_workflow",
            "description": "Analyze an existing workflow and suggest optimizations: parallelizable steps, redundant approvals, missing notifications, SLA improvements.",
            "parameters": {"type": "object", "properties": {
                "workflow_id": {"type": "string", "description": "ID of the workflow template to analyze"}
            }, "required": ["workflow_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_it_knowledge_base",
            "description": "Search the IT knowledge base for solutions to technical problems. Returns similar resolved tickets, knowledge base articles, and resolution steps.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "The problem description or error message to search for"}
            }, "required": ["query"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "auto_tag_it_ticket",
            "description": "Automatically categorize an IT support ticket by analyzing its content. Returns suggested category, priority, tags, and assignee.",
            "parameters": {"type": "object", "properties": {
                "ticket_id": {"type": "string", "description": "ID of the IT ticket to auto-tag"}
            }, "required": ["ticket_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_it_solution",
            "description": "Suggest solutions from past resolved IT tickets that are similar to the given ticket. Returns top matches with similarity scores and resolution details.",
            "parameters": {"type": "object", "properties": {
                "ticket_id": {"type": "string", "description": "ID of the IT ticket to find solutions for"}
            }, "required": ["ticket_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_employee",
            "description": "Create a new employee in the HR system. Sets up profile with email, name, department, role, salary, country, contract type, and vacation allowance.",
            "parameters": {"type": "object", "properties": {
                "email": {"type": "string"}, "full_name": {"type": "string"},
                "department": {"type": "string"}, "role": {"type": "string"},
                "base_salary": {"type": "number"}, "country": {"type": "string"},
                "contract_type": {"type": "string"}, "hire_date": {"type": "string"},
                "vacation_allowance": {"type": "integer"}
            }, "required": ["email", "full_name", "department"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_employee",
            "description": "Update any field on an employee record by ID. Fields dict maps column name to new value.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "fields": {"type": "object"}
            }, "required": ["employee_id", "fields"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "archive_employee",
            "description": "Archive an employee by setting is_active=False. Fires employee.archived event.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_employees_advanced",
            "description": "Multi-field employee search: name, email, department, role, active status. Returns matching employees with key fields.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"}, "department": {"type": "string"},
                "role": {"type": "string"}, "is_active": {"type": "boolean"},
                "limit": {"type": "integer"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_profile_full",
            "description": "Get full employee profile by ID with all canonical fields (no PII).",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_org_chart",
            "description": "Returns the hierarchical organization structure as a nested tree. Uses manager_id to build the tree.",
            "parameters": {"type": "object", "properties": {
                "max_depth": {"type": "integer"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_span_of_control",
            "description": "Counts direct reports per manager. Returns list of {manager_name, report_count, department}.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pto_balance",
            "description": "Get PTO balance for an employee: allowance, used days, remaining days.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_department_members",
            "description": "Lists all active employees in a specific department.",
            "parameters": {"type": "object", "properties": {
                "department": {"type": "string"}
            }, "required": ["department"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_hires",
            "description": "Lists employees hired in the last N days.",
            "parameters": {"type": "object", "properties": {
                "days": {"type": "integer"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_vacation",
            "description": "Request vacation days for an employee. Creates a VacationRequest with status=pending and validates no overlapping approved requests.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "start_date": {"type": "string"},
                "end_date": {"type": "string"}, "reason": {"type": "string"}
            }, "required": ["employee_id", "start_date", "end_date"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_vacation",
            "description": "Approve or reject a vacation request. Sets reviewed_by and reviewed_at. Publishes vacation event.",
            "parameters": {"type": "object", "properties": {
                "vacation_id": {"type": "string"}, "approved": {"type": "boolean"},
                "reviewer_id": {"type": "string"}
            }, "required": ["vacation_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_calendar",
            "description": "Returns all vacations, meetings, and tasks for a team/department in a date range ahead.",
            "parameters": {"type": "object", "properties": {
                "department": {"type": "string"}, "days": {"type": "integer"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_meeting",
            "description": "Create a scheduled meeting with organizer, attendees, location, and description.",
            "parameters": {"type": "object", "properties": {
                "title": {"type": "string"}, "organizer_id": {"type": "string"},
                "start_datetime": {"type": "string"}, "end_datetime": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string"}, "description": {"type": "string"}
            }, "required": ["title", "organizer_id", "start_datetime", "end_datetime"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_schedule",
            "description": "Returns an employee's work schedule from the work_schedules table: day_of_week to {start_time, end_time}.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_payroll_cycle",
            "description": "Creates a new PayrollCycle with status=draft.",
            "parameters": {"type": "object", "properties": {
                "period_name": {"type": "string"}, "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            }, "required": ["period_name", "start_date", "end_date"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_payroll",
            "description": "Triggers payroll processing for a cycle. Generates payslips for all active employees with line items.",
            "parameters": {"type": "object", "properties": {
                "cycle_id": {"type": "string"}
            }, "required": ["cycle_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_payslip",
            "description": "Returns a payslip with line items for an employee. If no cycle_id, returns the latest payslip.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "cycle_id": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tax_rules",
            "description": "Returns tax rules. Filter by country code if provided.",
            "parameters": {"type": "object", "properties": {
                "country_code": {"type": "string"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_compensation",
            "description": "Updates an employee's base_salary and currency. Fires salary.changed event.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "base_salary": {"type": "number"},
                "currency": {"type": "string"}
            }, "required": ["employee_id", "base_salary"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_bonus",
            "description": "Creates a Bonus record for an employee with status=pending.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "amount": {"type": "number"},
                "description": {"type": "string"}, "bonus_type": {"type": "string"}
            }, "required": ["employee_id", "amount", "description"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_ledger",
            "description": "Returns journal entries within a date range with their line items.",
            "parameters": {"type": "object", "properties": {
                "start_date": {"type": "string"}, "end_date": {"type": "string"},
                "limit": {"type": "integer"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense_summary_agg",
            "description": "Aggregates expenses across departments and categories: totals, by category, by department.",
            "parameters": {"type": "object", "properties": {
                "department": {"type": "string"}, "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clock_in",
            "description": "Creates a new TimeLog entry with clock_in set to now. Validates no active session exists.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "notes": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clock_out",
            "description": "Sets clock_out to now on an existing TimeLog entry.",
            "parameters": {"type": "object", "properties": {
                "log_id": {"type": "string"}, "notes": {"type": "string"}
            }, "required": ["log_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_logs",
            "description": "Returns time log entries for an employee in a date range.",
            "parameters": {"type": "object", "properties": {
                "employee_id": {"type": "string"}, "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            }, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_it_ticket",
            "description": "Assigns an IT support ticket to a support agent. Sets status to in_progress.",
            "parameters": {"type": "object", "properties": {
                "ticket_id": {"type": "string"}, "assignee_id": {"type": "string"}
            }, "required": ["ticket_id", "assignee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_it_ticket",
            "description": "Resolves an IT ticket: sets status=resolved, resolved_at, resolution_notes. Generates KB article reference.",
            "parameters": {"type": "object", "properties": {
                "ticket_id": {"type": "string"}, "resolution_notes": {"type": "string"}
            }, "required": ["ticket_id", "resolution_notes"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_it_assets",
            "description": "Lists IT assets. Filter by assigned employee or category.",
            "parameters": {"type": "object", "properties": {
                "assigned_to_id": {"type": "string"}, "category": {"type": "string"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket_stats",
            "description": "Returns IT ticket statistics: opened, resolved, avg resolution time, grouped by category.",
            "parameters": {"type": "object", "properties": {
                "days": {"type": "integer"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enroll_in_course",
            "description": "Enroll an employee in a training course. Checks for duplicate enrollment.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "course_id": {"type": "string"}}, "required": ["employee_id", "course_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_catalog",
            "description": "List available training courses. Filter by category keyword or FUNDAE eligibility.",
            "parameters": {"type": "object", "properties": {"category": {"type": "string"}, "fundae_only": {"type": "boolean"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_courses",
            "description": "Get AI-powered course recommendations for an employee based on role, department, and history.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_fundae",
            "description": "Run FUNDAE compliance validation for a course enrollment. Returns duration, progress, test, and survey checks.",
            "parameters": {"type": "object", "properties": {"enrollment_id": {"type": "string"}}, "required": ["enrollment_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_job_posting",
            "description": "Create a new job posting / vacancy.",
            "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "department": {"type": "string"}, "description": {"type": "string"}, "location": {"type": "string"}, "employment_type": {"type": "string"}}, "required": ["title", "department", "description"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_candidate",
            "description": "Add a candidate to a job posting.",
            "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}, "first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"}, "phone": {"type": "string"}, "source": {"type": "string"}, "notes": {"type": "string"}}, "required": ["job_id", "first_name", "last_name", "email"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_candidate_stage",
            "description": "Move a candidate to a new pipeline stage (applied, screening, interview, offer, hired, rejected).",
            "parameters": {"type": "object", "properties": {"candidate_id": {"type": "string"}, "new_stage": {"type": "string"}}, "required": ["candidate_id", "new_stage"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_interview",
            "description": "Schedule an interview for a candidate with an interviewer.",
            "parameters": {"type": "object", "properties": {"candidate_id": {"type": "string"}, "interviewer_id": {"type": "string"}, "scheduled_at": {"type": "string"}, "duration_minutes": {"type": "integer"}, "interview_type": {"type": "string"}}, "required": ["candidate_id", "interviewer_id", "scheduled_at"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_applications",
            "description": "Get all candidates and stage counts for a job posting.",
            "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_stats",
            "description": "Get recruitment pipeline metrics: open jobs, total candidates, stage distribution, avg time-to-hire.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "promote_to_employee",
            "description": "Convert a hired candidate into an employee. Creates User record and marks candidate as hired.",
            "parameters": {"type": "object", "properties": {"candidate_id": {"type": "string"}, "base_salary": {"type": "number"}, "contract_type": {"type": "string"}}, "required": ["candidate_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_okr",
            "description": "Create an Objective with optional Key Results for an employee.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}, "krs": {"type": "array", "items": {"type": "object"}}}, "required": ["employee_id", "title"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_key_result",
            "description": "Update the current value of a Key Result.",
            "parameters": {"type": "object", "properties": {"kr_id": {"type": "string"}, "current_value": {"type": "integer"}}, "required": ["kr_id", "current_value"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_review",
            "description": "Create a performance review for an employee.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "manager_id": {"type": "string"}, "cycle_name": {"type": "string"}, "self_assessment": {"type": "string"}}, "required": ["employee_id", "manager_id", "cycle_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_okrs",
            "description": "Get all OKRs for a department with key result progress.",
            "parameters": {"type": "object", "properties": {"department": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_kudos_received",
            "description": "Get recent kudos/recognition received by an employee.",
            "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["employee_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_overview",
            "description": "Get CRM sales pipeline overview: leads by stage with counts, total values, and avg probability.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_client_details",
            "description": "Get detailed client information with associated leads/deals.",
            "parameters": {"type": "object", "properties": {"client_id": {"type": "string"}}, "required": ["client_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_clients",
            "description": "Search clients by company name or industry.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "industry": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_deal_stats",
            "description": "Get deal statistics: won count/value, loss rate, avg deal size for a period (month/quarter/year).",
            "parameters": {"type": "object", "properties": {"period": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task_for_lead",
            "description": "Create a calendar task linked to a sales lead.",
            "parameters": {"type": "object", "properties": {"lead_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}, "due_date": {"type": "string"}}, "required": ["lead_id", "title"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_lead_activity",
            "description": "Log a CRM activity (call, email, meeting, note) for a lead.",
            "parameters": {"type": "object", "properties": {"lead_id": {"type": "string"}, "activity_type": {"type": "string"}, "notes": {"type": "string"}}, "required": ["lead_id", "activity_type", "notes"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_project",
            "description": "Create a new project.",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "status": {"type": "string"}}, "required": ["name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_project_task",
            "description": "Create a task within a project.",
            "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}, "assignee_id": {"type": "string"}, "priority": {"type": "string"}, "due_date": {"type": "string"}}, "required": ["project_id", "title"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_status",
            "description": "Get project status with task breakdown: total, completed, in_progress, blocked.",
            "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_wiki_page",
            "description": "Create a wiki page, optionally linked to a project.",
            "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "project_id": {"type": "string"}}, "required": ["title", "content"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contracts",
            "description": "Get contracts list. Filter by status (draft, pending_signature, active, expired).",
            "parameters": {"type": "object", "properties": {"status": {"type": "string"}}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_compliance_status",
            "description": "Get compliance overview: GDPR, FUNDAE, and labor law status.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_whistleblower",
            "description": "Submit a whistleblower report (anonymous or named). Returns tracking code.",
            "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "category": {"type": "string"}, "is_anonymous": {"type": "boolean"}}, "required": ["title", "description"]}
        }
    },
]

async def execute_tool(db: AsyncSession, name: str, arguments: Dict[str, Any], user_payload: dict = None, agent_id: str = None, run_id: str = None) -> str:
    """
    Despacha la ejecución de la herramienta correspondiente.
    Si se proporciona user_payload, se aplica ACL antes de ejecutar.
    Para herramientas destructivas, requiere aprobación humana.
    """
    from app.services.tool_registry import TOOL_REGISTRY

    if user_payload is not None:
        acl_result = await enforce_tool_acl(name, user_payload, db)
        if acl_result.denied:
            return json.dumps({
                "error": acl_result.message,
                "reason": acl_result.reason,
                "requires_confirmation": acl_result.requires_confirmation,
            }, ensure_ascii=False)

    if name in DESTRUCTIVE_TOOLS and user_payload is not None:
        try:
            from app.services.human_approval import request_approval, check_approval
            import asyncio

            user_id = user_payload.get("user_id", "")
            action_description = f"Tool: {name} — Args: {json.dumps(arguments, default=str)[:200]}"
            action_type = name.replace("process_payroll", "payroll_process").replace("update_compensation", "salary_change").replace("archive_employee", "termination").replace("approve_vacation", "vacation_approval").replace("create_bonus", "bonus_creation").replace("move_candidate_stage", "candidate_stage_change").replace("promote_to_employee", "employee_promotion").replace("create_payroll_cycle", "payroll_cycle_creation").replace("submit_whistleblower", "whistleblower_report")

            approval_id = await request_approval(
                agent_id=agent_id or "unknown",
                run_id=run_id or "unknown",
                action_description=action_description,
                action_type=action_type,
                tool_name=name,
                tool_args=arguments,
                user_id=user_id,
                db=db,
            )

            status = await check_approval(approval_id, db)
            if status != "approved":
                return json.dumps({
                    "status": "pending_approval",
                    "message": f"Esta acción requiere aprobación. Solicitud creada: {approval_id}",
                    "approval_id": approval_id,
                    "tool": name,
                    "action_type": action_type,
                }, ensure_ascii=False)

            logger.info(f"Destructive tool {name} approved via {approval_id} — executing")
        except Exception as e:
            logger.error(f"Approval system error for tool {name}: {e}")
            return json.dumps({
                "error": f"Approval system unavailable: {e}. Tool execution aborted.",
                "tool": name,
            }, ensure_ascii=False)

    if name == "get_employee_profile":
        return await get_employee_profile(db, email=arguments.get("email"), user_id=arguments.get("user_id"))
    elif name == "list_department_members":
        return await list_department_members(db, department=arguments.get("department", ""))
    elif name == "get_vacation_balance":
        return await get_vacation_balance(db, user_id=arguments.get("user_id", ""), email=arguments.get("email", ""))
    elif name == "create_it_ticket":
        return await create_it_ticket(
            db, requester_id=arguments.get("requester_id", ""),
            title=arguments.get("title", ""), description=arguments.get("description", ""),
            category=arguments.get("category", "Hardware")
        )
    elif name == "search_employees":
        return await search_employees(db, query=arguments.get("query", ""))
    elif name == "get_department_stats":
        return await get_department_stats(db, department=arguments.get("department", ""))
    elif name == "get_expense_summary":
        return await get_expense_summary(db, user_email=arguments.get("user_email", ""))
    elif name == "get_training_progress":
        return await tool_get_training_progress(db, employee_id=arguments.get("employee_id",""))
    elif name == "get_company_announcements":
        return await get_company_announcements(db, limit=arguments.get("limit", 5))
    elif name == "get_upcoming_vacations":
        return await get_upcoming_vacations(db, department=arguments.get("department", ""))
    elif name == "get_kudos_leaderboard":
        return await get_kudos_leaderboard(db, limit=arguments.get("limit", 5))
    elif name == "create_client":
        return await create_client(db, name=arguments.get("name",""), email=arguments.get("email",""), contact_person=arguments.get("contact_person",""), phone=arguments.get("phone",""))
    elif name == "book_vacation":
        return await book_vacation(db, user_email=arguments.get("user_email",""), start_date=arguments.get("start_date",""), end_date=arguments.get("end_date",""), days=arguments.get("days",1))
    elif name == "create_kudos":
        return await create_kudos(db, receiver_email=arguments.get("receiver_email",""), sender_email=arguments.get("sender_email",""), message=arguments.get("message",""), badge=arguments.get("badge","⭐"))
    elif name == "create_expense":
        return await create_expense(db, user_email=arguments.get("user_email",""), amount=arguments.get("amount",0), category=arguments.get("category",""), description=arguments.get("description",""))
    elif name == "create_task":
        return await create_task(db, title=arguments.get("title",""), description=arguments.get("description",""), assigned_to_email=arguments.get("assigned_to_email",""), priority=arguments.get("priority","medium"))
    elif name == "parse_resume":
        return await _tool_parse_resume(db, file_path=arguments.get("file_path",""), model=arguments.get("model","gpt-4o-mini"))
    elif name == "match_candidate_to_job":
        return await _tool_match_candidate_to_job(db, candidate_data=arguments.get("candidate_data",{}), job_requirements=arguments.get("job_requirements",""), model=arguments.get("model","gpt-4o-mini"))
    elif name == "screen_resume":
        return await _tool_screen_resume(db, file_path=arguments.get("file_path",""), job_id=arguments.get("job_id",""))
    elif name == "trigger_workflow":
        return await _tool_trigger_workflow(db, user_id=arguments.get("user_id",""), workflow_template_id=arguments.get("workflow_template_id",""), template_name=arguments.get("template_name",""))
    elif name == "complete_workflow_step":
        return await _tool_complete_workflow_step(db, workflow_id=arguments.get("workflow_id",""), step_id=arguments.get("step_id",""), completed_by=arguments.get("completed_by",""))
    elif name == "create_workflow_from_description":
        return await _tool_create_workflow_from_description(db, description=arguments.get("description",""), name=arguments.get("name",""), user_id=arguments.get("user_id",""))
    elif name == "analyze_workflow":
        return await _tool_analyze_workflow(db, workflow_id=arguments.get("workflow_id",""))
    elif name == "search_it_knowledge_base":
        return await _tool_search_it_kb(db, query=arguments.get("query",""))
    elif name == "auto_tag_it_ticket":
        return await _tool_auto_tag_it_ticket(db, ticket_id=arguments.get("ticket_id",""))
    elif name == "suggest_it_solution":
        return await _tool_suggest_it_solution(db, ticket_id=arguments.get("ticket_id",""))
    elif name == "enroll_in_course":
        return await tool_enroll_in_course(db, employee_id=arguments.get("employee_id",""), course_id=arguments.get("course_id",""))
    elif name == "get_course_catalog":
        return await tool_get_course_catalog(db, category=arguments.get("category",""), fundae_only=arguments.get("fundae_only", False))
    elif name == "recommend_courses":
        return await tool_recommend_courses(db, employee_id=arguments.get("employee_id",""), limit=arguments.get("limit",3))
    elif name == "validate_fundae":
        return await tool_validate_fundae(db, enrollment_id=arguments.get("enrollment_id",""))
    elif name == "create_job_posting":
        return await tool_create_job_posting(db, title=arguments.get("title",""), department=arguments.get("department",""), description=arguments.get("description",""), location=arguments.get("location",""), employment_type=arguments.get("employment_type","full-time"))
    elif name == "add_candidate":
        return await tool_add_candidate(db, job_id=arguments.get("job_id",""), first_name=arguments.get("first_name",""), last_name=arguments.get("last_name",""), email=arguments.get("email",""), phone=arguments.get("phone",""), source=arguments.get("source",""), notes=arguments.get("notes",""))
    elif name == "move_candidate_stage":
        return await tool_move_candidate_stage(db, candidate_id=arguments.get("candidate_id",""), new_stage=arguments.get("new_stage",""))
    elif name == "schedule_interview":
        return await tool_schedule_interview(db, candidate_id=arguments.get("candidate_id",""), interviewer_id=arguments.get("interviewer_id",""), scheduled_at=arguments.get("scheduled_at",""), duration_minutes=arguments.get("duration_minutes",60), interview_type=arguments.get("interview_type","video"))
    elif name == "get_job_applications":
        return await tool_get_job_applications(db, job_id=arguments.get("job_id",""))
    elif name == "get_pipeline_stats":
        return await tool_get_pipeline_stats(db)
    elif name == "promote_to_employee":
        return await tool_promote_to_employee(db, candidate_id=arguments.get("candidate_id",""), base_salary=arguments.get("base_salary"), contract_type=arguments.get("contract_type","indefinido"))
    elif name == "create_okr":
        return await tool_create_okr(db, employee_id=arguments.get("employee_id",""), title=arguments.get("title",""), description=arguments.get("description",""), krs=arguments.get("krs"))
    elif name == "update_key_result":
        return await tool_update_key_result(db, kr_id=arguments.get("kr_id",""), current_value=arguments.get("current_value",0))
    elif name == "create_review":
        return await tool_create_review(db, employee_id=arguments.get("employee_id",""), manager_id=arguments.get("manager_id",""), cycle_name=arguments.get("cycle_name",""), self_assessment=arguments.get("self_assessment",""))
    elif name == "get_team_okrs":
        return await tool_get_team_okrs(db, department=arguments.get("department",""))
    elif name == "get_kudos_received":
        return await tool_get_kudos_received(db, employee_id=arguments.get("employee_id",""), limit=arguments.get("limit",10))
    elif name == "get_pipeline_overview":
        return await tool_get_pipeline_overview(db)
    elif name == "get_client_details":
        return await tool_get_client_details(db, client_id=arguments.get("client_id",""))
    elif name == "search_clients":
        return await tool_search_clients(db, query=arguments.get("query",""), industry=arguments.get("industry",""))
    elif name == "get_deal_stats":
        return await tool_get_deal_stats(db, period=arguments.get("period","month"))
    elif name == "create_task_for_lead":
        return await tool_create_task_for_lead(db, lead_id=arguments.get("lead_id",""), title=arguments.get("title",""), description=arguments.get("description",""), due_date=arguments.get("due_date",""))
    elif name == "log_lead_activity":
        return await tool_log_lead_activity(db, lead_id=arguments.get("lead_id",""), activity_type=arguments.get("activity_type",""), notes=arguments.get("notes",""))
    elif name == "create_project":
        return await tool_create_project(db, name=arguments.get("name",""), description=arguments.get("description",""), status=arguments.get("status","active"))
    elif name == "create_project_task":
        return await tool_create_project_task(db, project_id=arguments.get("project_id",""), title=arguments.get("title",""), description=arguments.get("description",""), assignee_id=arguments.get("assignee_id",""), priority=arguments.get("priority","medium"), due_date=arguments.get("due_date",""))
    elif name == "get_project_status":
        return await tool_get_project_status(db, project_id=arguments.get("project_id",""))
    elif name == "create_wiki_page":
        return await tool_create_wiki_page(db, title=arguments.get("title",""), content=arguments.get("content",""), project_id=arguments.get("project_id",""))
    elif name == "get_contracts":
        return await tool_get_contracts(db, status=arguments.get("status",""))
    elif name == "get_compliance_status":
        return await tool_get_compliance_status(db)
    elif name == "submit_whistleblower":
        return await tool_submit_whistleblower(db, title=arguments.get("title",""), description=arguments.get("description",""), category=arguments.get("category",""), is_anonymous=arguments.get("is_anonymous", False))
    elif name == "handoff_to_specialist":
        return await _tool_handoff_to_specialist(db, arguments, agent_id, run_id)
    elif name == "negotiate_with_agents":
        return await _tool_negotiate_with_agents(db, arguments, agent_id, run_id)
    else:
        from app.services.tool_registry import resolve_tool_name
        resolved_name = resolve_tool_name(name)
        tool_entry = TOOL_REGISTRY.get(resolved_name)
        if tool_entry and tool_entry.get("handler"):
            try:
                handler = tool_entry["handler"]
                if callable(handler):
                    kwargs = {"db": db}
                    if hasattr(handler, "__code__"):
                        sig = handler.__code__.co_varnames[:handler.__code__.co_argcount]
                        for k, v in (arguments or {}).items():
                            if k in sig:
                                kwargs[k] = v
                        missing_required = [p for p in sig if p != "db" and p not in kwargs]
                        if missing_required:
                            kwargs.update({p: arguments.get(p) for p in missing_required if p in (arguments or {})})
                    else:
                        kwargs.update(arguments or {})
                    if user_payload:
                        kwargs.setdefault("user_payload", user_payload)
                        kwargs.setdefault("user_id", user_payload.get("user_id", ""))
                    if agent_id:
                        kwargs.setdefault("agent_id", agent_id)
                    if run_id:
                        kwargs.setdefault("run_id", run_id)
                    result = await handler(**kwargs)
                    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                logger.error(f"Registry tool '{name}' execution failed: {e}", exc_info=True)
                return json.dumps({"error": f"Tool execution error: {str(e)}"}, ensure_ascii=False)
        return json.dumps({"error": f"La herramienta '{name}' no esta registrada en el ejecutor."})



async def _tool_handoff_to_specialist(db: AsyncSession, arguments: dict, agent_id: str = None, run_id: str = None) -> str:
    from app.services.agent_handoff import AgentHandoffProtocol

    to_agent_type = arguments.get("to_agent_type", "")
    user_id = arguments.get("user_id", "")
    task = arguments.get("task", "")
    session_id = arguments.get("session_id", "")
    context = arguments.get("context", {})

    if not to_agent_type:
        return json.dumps({"error": "Missing required parameter: to_agent_type"}, ensure_ascii=False)

    if not context:
        try:
            context = await AgentHandoffProtocol.build_handoff_context(
                from_agent_id=agent_id or "unknown",
                user_id=user_id,
                session_id=session_id or "",
                db=db,
            )
        except Exception as e:
            logger.warning(f"Could not auto-build handoff context: {e}")
            context = {"summary": f"Handoff from agent {agent_id}", "decisions": [], "open_items": []}

    if not task:
        task = f"Handle the user's pending request. Context: {context.get('summary', 'No summary available')}"

    result = await AgentHandoffProtocol.handoff(
        from_agent_id=agent_id or "unknown",
        to_agent_type=to_agent_type,
        user_id=user_id,
        task=task,
        context=context,
        db=db,
    )

    return json.dumps({
        "status": result.status,
        "from_agent": result.from_agent,
        "to_agent": result.to_agent,
        "new_run_id": result.new_run_id,
        "session_id": result.session_id,
        "error": result.error,
        "message": (
            f"Handoff to {to_agent_type} completed successfully."
            if result.status == "completed"
            else f"Handoff failed: {result.error}"
        ),
    }, ensure_ascii=False)


register_tool("get_employee_profile", AVAILABLE_TOOLS_SCHEMA[0], get_employee_profile)
register_tool("list_department_members", AVAILABLE_TOOLS_SCHEMA[1], list_department_members)
register_tool("get_vacation_balance", AVAILABLE_TOOLS_SCHEMA[2], get_vacation_balance)
register_tool("create_it_ticket", AVAILABLE_TOOLS_SCHEMA[3], create_it_ticket)
register_tool("search_employees", AVAILABLE_TOOLS_SCHEMA[4], search_employees)
register_tool("get_department_stats", AVAILABLE_TOOLS_SCHEMA[5], get_department_stats)
register_tool("get_expense_summary", AVAILABLE_TOOLS_SCHEMA[6], get_expense_summary)
register_tool("get_training_progress", AVAILABLE_TOOLS_SCHEMA[7], tool_get_training_progress)
register_tool("get_company_announcements", AVAILABLE_TOOLS_SCHEMA[8], get_company_announcements)
register_tool("get_upcoming_vacations", AVAILABLE_TOOLS_SCHEMA[9], get_upcoming_vacations)
register_tool("get_kudos_leaderboard", AVAILABLE_TOOLS_SCHEMA[10], get_kudos_leaderboard)
register_tool("create_client", {"type":"function","function":{"name":"create_client","description":"Create a new client/company in the CRM","parameters":{"type":"object","properties":{"name":{"type":"string"},"email":{"type":"string"},"contact_person":{"type":"string"},"phone":{"type":"string"}},"required":["name","email"]}}}, create_client)
register_tool("book_vacation", {"type":"function","function":{"name":"book_vacation","description":"Request vacation days for an employee","parameters":{"type":"object","properties":{"user_email":{"type":"string"},"start_date":{"type":"string"},"end_date":{"type":"string"},"days":{"type":"integer"}},"required":["user_email","start_date","end_date"]}}}, book_vacation)
register_tool("create_kudos", {"type":"function","function":{"name":"create_kudos","description":"Send recognition/kudos to a colleague","parameters":{"type":"object","properties":{"receiver_email":{"type":"string"},"sender_email":{"type":"string"},"message":{"type":"string"},"badge":{"type":"string"}},"required":["receiver_email","sender_email","message"]}}}, create_kudos)
register_tool("create_expense", {"type":"function","function":{"name":"create_expense","description":"Create an expense claim for reimbursement","parameters":{"type":"object","properties":{"user_email":{"type":"string"},"amount":{"type":"number"},"category":{"type":"string"},"description":{"type":"string"}},"required":["user_email","amount","category"]}}}, create_expense)
register_tool("create_task", {"type":"function","function":{"name":"create_task","description":"Create a task/reminder for yourself or assign to someone","parameters":{"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"assigned_to_email":{"type":"string"},"priority":{"type":"string"}},"required":["title"]}}}, create_task)


async def _tool_parse_resume(db: AsyncSession, file_path: str, model: str = "gpt-4o-mini") -> str:
    try:
        from app.services.resume_parser import parse_resume
        result = await parse_resume(file_path, model=model)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in parse_resume tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_match_candidate_to_job(db: AsyncSession, candidate_data: dict, job_requirements: str, model: str = "gpt-4o-mini") -> str:
    try:
        from app.services.resume_parser import match_candidate_to_job
        result = await match_candidate_to_job(candidate_data, job_requirements, model=model)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in match_candidate_to_job tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_screen_resume(db: AsyncSession, file_path: str, job_id: str = "") -> str:
    try:
        import os as _os
        if not _os.path.isfile(file_path):
            return json.dumps({"error": f"File not found: {file_path}"})
        filename = _os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_content = f.read()
        if len(file_content) == 0:
            return json.dumps({"error": "File is empty"})
        from app.services.resume_parser import screen_resume
        result = await screen_resume(file_content, filename, job_id=job_id if job_id else None)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in screen_resume tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_screen_candidate(db: AsyncSession, file_path: str, job_id: str = "", model: str = "gpt-4o-mini") -> str:
    try:
        import os as _os
        if not _os.path.isfile(file_path):
            return json.dumps({"error": f"File not found: {file_path}"})
        filename = _os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_content = f.read()
        if len(file_content) == 0:
            return json.dumps({"error": "File is empty"})
        from app.services.candidate_screener import screen_resume_full
        result = await screen_resume_full(file_content, filename, job_id=job_id if job_id else None, db=db, model=model)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in screen_candidate tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_rank_candidates(db: AsyncSession, candidate_ids: list, job_id: str = "", model: str = "gpt-4o-mini") -> str:
    try:
        from app.services.candidate_screener import rank_candidates
        result = await rank_candidates(candidate_ids, job_id, db, model=model)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in rank_candidates tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_generate_interview_questions(db: AsyncSession, candidate_id: str, job_id: str = "", model: str = "gpt-4o-mini") -> str:
    try:
        from sqlalchemy import select
        from app.models.hire import Candidate, JobPosting
        from app.services.candidate_screener import generate_interview_questions, _get_job_requirements
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return json.dumps({"error": f"Candidate {candidate_id} not found"})
        # La firma real en candidate_screener es _get_job_requirements(job_id, db)
        job_requirements = await _get_job_requirements(job_id, db)
        if not job_requirements:
            return json.dumps({"error": f"Job {job_id} not found"})
        candidate_profile = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "notes": candidate.notes,
            "stage": candidate.stage,
        }
        questions = await generate_interview_questions(candidate_profile, job_requirements, model=model)
        question_count = len(questions) if isinstance(questions, list) else 0
        return json.dumps({"success": True, "candidate_id": candidate_id, "job_id": job_id, "question_count": question_count, "questions": questions}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in generate_interview_questions tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_generate_smart_goals(db: AsyncSession, employee_id: str, count: int = 3) -> str:
    try:
        from app.services.goal_generator import generate_smart_goals
        result = await generate_smart_goals(employee_id, db, count=count)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in generate_smart_goals tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_suggest_goal_adjustments(db: AsyncSession, employee_id: str) -> str:
    try:
        from app.services.goal_generator import suggest_goal_adjustments
        result = await suggest_goal_adjustments(employee_id, db)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in suggest_goal_adjustments tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_create_workflow_from_description(db: AsyncSession, description: str, name: str, user_id: str = "") -> str:
    try:
        if not description or not description.strip():
            return json.dumps({"error": "Description is required", "detail": "Please provide a natural language description of the workflow process."})
        if not name or not name.strip():
            return json.dumps({"error": "Name is required", "detail": "Please provide a name for the workflow template."})

        from app.services.nl_workflow_builder import create_workflow_from_nl

        logger.info(f"Creating workflow from description: '{name}' (user={user_id})")

        result = await create_workflow_from_nl(
            description=description,
            name=name,
            user_id=user_id,
            tenant_id="",
            db=db,
        )

        if not result.get("success"):
            logger.warning(f"Workflow creation failed: {result.get('error', 'unknown error')}, validation_errors={result.get('validation_errors', [])}")

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in create_workflow_from_description tool: {e}", exc_info=True)
        return json.dumps({"error": f"Workflow creation failed: {str(e)}", "detail": str(e)})


async def _tool_analyze_workflow(db: AsyncSession, workflow_id: str) -> str:
    try:
        from app.services.nl_workflow_builder import suggest_workflow_improvements
        result = await suggest_workflow_improvements(workflow_id=workflow_id, db=db)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in analyze_workflow tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_search_it_kb(db: AsyncSession, query: str) -> str:
    try:
        results = await it_kb_search(query, db, top_k=5)
        return json.dumps({"results": results}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in search_it_knowledge_base tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_auto_tag_it_ticket(db: AsyncSession, ticket_id: str) -> str:
    try:
        result = await it_kb_auto_tag(ticket_id, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in auto_tag_it_ticket tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_suggest_it_solution(db: AsyncSession, ticket_id: str) -> str:
    try:
        result = await it_kb_suggest(ticket_id, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in suggest_it_solution tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_generate_onboarding_plan(db: AsyncSession, employee_id: str) -> str:
    try:
        from app.services.onboarding_planner import generate_onboarding_plan
        result = await generate_onboarding_plan(employee_id, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in generate_onboarding_plan tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_assign_onboarding_buddy(db: AsyncSession, employee_id: str) -> str:
    try:
        from app.services.onboarding_planner import assign_onboarding_buddy
        result = await assign_onboarding_buddy(employee_id, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in assign_onboarding_buddy tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_score_lead(db: AsyncSession, lead_id: str) -> str:
    try:
        from app.services.lead_scorer import score_lead as do_score
        result = await do_score(lead_id, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in score_lead tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_suggest_sales_action(db: AsyncSession, lead_id: str) -> str:
    try:
        from app.services.lead_scorer import suggest_next_action as do_action
        result = await do_action(lead_id, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in suggest_sales_action tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_generate_email_template(db: AsyncSession, lead_id: str, email_type: str) -> str:
    try:
        from app.services.lead_scorer import generate_email_template as do_email
        result = await do_email(lead_id, email_type, db)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error in generate_email_template tool: {e}")
        return json.dumps({"error": str(e)})


register_tool("score_lead", {"type":"function","function":{"name":"score_lead","description":"Score a sales lead using multi-factor AI analysis (0-100). Returns quality tier and conversion probability.","parameters":{"type":"object","properties":{"lead_id":{"type":"string","description":"Lead ID to score"}},"required":["lead_id"]}}}, _tool_score_lead)
register_tool("suggest_sales_action", {"type":"function","function":{"name":"suggest_sales_action","description":"Recommend the next best action for a sales lead: call, email, meeting, demo, proposal, follow_up, nurture, or disqualify.","parameters":{"type":"object","properties":{"lead_id":{"type":"string","description":"Lead ID to analyze"}},"required":["lead_id"]}}}, _tool_suggest_sales_action)
register_tool("generate_email_template", {"type":"function","function":{"name":"generate_email_template","description":"Generate a personalized email template for a lead (cold_outreach, follow_up, demo_invite, proposal_cover, check_in, re_engagement, breakup).","parameters":{"type":"object","properties":{"lead_id":{"type":"string","description":"Lead ID"},"email_type":{"type":"string","description":"Email type"}},"required":["lead_id","email_type"]}}}, _tool_generate_email_template)

register_tool("search_it_knowledge_base", {"type":"function","function":{"name":"search_it_knowledge_base","description":"Search the IT knowledge base for solutions to technical problems. Returns similar resolved tickets, knowledge base articles, and resolution steps.","parameters":{"type":"object","properties":{"query":{"type":"string","description":"The problem description or error message to search for"}},"required":["query"]}}}, _tool_search_it_kb)
register_tool("auto_tag_it_ticket", {"type":"function","function":{"name":"auto_tag_it_ticket","description":"Automatically categorize an IT support ticket by analyzing its content. Returns suggested category, priority, tags, and assignee.","parameters":{"type":"object","properties":{"ticket_id":{"type":"string","description":"ID of the IT ticket to auto-tag"}},"required":["ticket_id"]}}}, _tool_auto_tag_it_ticket)
register_tool("suggest_it_solution", {"type":"function","function":{"name":"suggest_it_solution","description":"Suggest solutions from past resolved IT tickets that are similar to the given ticket. Returns top matches with similarity scores and resolution details.","parameters":{"type":"object","properties":{"ticket_id":{"type":"string","description":"ID of the IT ticket to find solutions for"}},"required":["ticket_id"]}}}, _tool_suggest_it_solution)

register_tool("parse_resume", {"type":"function","function":{"name":"parse_resume","description":"Parse a resume file (PDF/DOCX/TXT) and extract structured candidate data: name, email, phone, skills, experience, education, languages, current title/company, LinkedIn URL","parameters":{"type":"object","properties":{"file_path":{"type":"string","description":"Absolute path to the uploaded resume file"},"model":{"type":"string","description":"LLM model to use"}},"required":["file_path"]}}}, _tool_parse_resume)
register_tool("match_candidate_to_job", {"type":"function","function":{"name":"match_candidate_to_job","description":"Score a parsed candidate profile against job requirements (0-100). Returns matching skills, missing skills, fit summary, and recommendation","parameters":{"type":"object","properties":{"candidate_data":{"type":"object","description":"Parsed candidate profile"},"job_requirements":{"type":"string","description":"Job title, department, and description"},"model":{"type":"string","description":"LLM model"}},"required":["candidate_data","job_requirements"]}}}, _tool_match_candidate_to_job)
register_tool("screen_resume", {"type":"function","function":{"name":"screen_resume","description":"Full resume screening pipeline: parse resume file and match against a job posting to get a fit score","parameters":{"type":"object","properties":{"file_path":{"type":"string","description":"Absolute path to the uploaded resume file"},"job_id":{"type":"string","description":"Optional job posting ID to match the candidate against"}},"required":["file_path"]}}}, _tool_screen_resume)
register_tool("trigger_workflow", {"type":"function","function":{"name":"trigger_workflow","description":"Start an onboarding or offboarding workflow for a user","parameters":{"type":"object","properties":{"user_id":{"type":"string"},"workflow_template_id":{"type":"string"},"template_name":{"type":"string"}},"required":["user_id"]}}}, _tool_trigger_workflow)
register_tool("complete_workflow_step", {"type":"function","function":{"name":"complete_workflow_step","description":"Mark a specific step in a user workflow as completed","parameters":{"type":"object","properties":{"workflow_id":{"type":"string"},"step_id":{"type":"string"},"completed_by":{"type":"string"}},"required":["workflow_id","step_id"]}}}, _tool_complete_workflow_step)
register_tool("create_workflow_from_description", {"type":"function","function":{"name":"create_workflow_from_description","description":"Generate a complete onboarding/offboarding workflow from a natural language description","parameters":{"type":"object","properties":{"description":{"type":"string","description":"Natural language description of the process"},"name":{"type":"string","description":"Name for the new workflow template"}},"required":["description","name"]}}}, _tool_create_workflow_from_description)
register_tool("analyze_workflow", {"type":"function","function":{"name":"analyze_workflow","description":"Analyze an existing workflow and suggest optimizations","parameters":{"type":"object","properties":{"workflow_id":{"type":"string","description":"ID of the workflow template to analyze"}},"required":["workflow_id"]}}}, _tool_analyze_workflow)
register_tool("generate_onboarding_plan", {"type":"function","function":{"name":"generate_onboarding_plan","description":"Generate a personalized AI-guided onboarding plan for a new employee based on role, department, location, and seniority","parameters":{"type":"object","properties":{"employee_id":{"type":"string","description":"Employee user ID"}},"required":["employee_id"]}}}, _tool_generate_onboarding_plan)
register_tool("assign_onboarding_buddy", {"type":"function","function":{"name":"assign_onboarding_buddy","description":"Assign an onboarding buddy for a new employee. Finds the best match in the same department using AI ranking","parameters":{"type":"object","properties":{"employee_id":{"type":"string","description":"Employee user ID"}},"required":["employee_id"]}}}, _tool_assign_onboarding_buddy)
schema_generate_smart_goals = {"type":"function","function":{"name":"generate_smart_goals","description":"Generate AI-powered SMART goals for an employee based on their role, department OKRs, and company strategy","parameters":{"type":"object","properties":{"employee_id":{"type":"string","description":"Employee user ID"},"count":{"type":"integer","description":"Number of goals to generate (default 3)"}},"required":["employee_id"]}}}
register_tool("generate_smart_goals", schema_generate_smart_goals, _tool_generate_smart_goals)
schema_suggest_goal_adjustments = {"type":"function","function":{"name":"suggest_goal_adjustments","description":"Mid-quarter review of an employee's goals with adjustment suggestions","parameters":{"type":"object","properties":{"employee_id":{"type":"string","description":"Employee user ID"}},"required":["employee_id"]}}}
register_tool("suggest_goal_adjustments", schema_suggest_goal_adjustments, _tool_suggest_goal_adjustments)
schema_screen_candidate = {"type":"function","function":{"name":"screen_candidate","description":"Full AI-powered resume screening: parse, score against job requirements, detect bias, and generate interview questions. Returns detailed breakdown with sub-scores and recommendations.","parameters":{"type":"object","properties":{"file_path":{"type":"string","description":"Absolute path to the uploaded resume file"},"job_id":{"type":"string","description":"Job posting ID to screen against"},"model":{"type":"string","description":"LLM model to use"}},"required":["file_path"]}}}
register_tool("screen_candidate", schema_screen_candidate, _tool_screen_candidate)
schema_rank_candidates = {"type":"function","function":{"name":"rank_candidates","description":"Rank multiple candidates against a job posting (0-100 scale with sub-scores). Returns sorted list with scores, strengths, weaknesses, and recommendations.","parameters":{"type":"object","properties":{"candidate_ids":{"type":"array","items":{"type":"string"},"description":"List of candidate IDs"},"job_id":{"type":"string","description":"Job posting ID"},"model":{"type":"string","description":"LLM model to use"}},"required":["candidate_ids","job_id"]}}}
register_tool("rank_candidates", schema_rank_candidates, _tool_rank_candidates)
schema_interview_questions = {"type":"function","function":{"name":"generate_interview_questions","description":"Generate 5-8 tailored interview questions (technical, behavioral, situational, cultural) for a candidate vs a job. Each question includes category, target skill, difficulty, and suggested answer key points.","parameters":{"type":"object","properties":{"candidate_id":{"type":"string","description":"Candidate ID"},"job_id":{"type":"string","description":"Job posting ID"},"model":{"type":"string","description":"LLM model to use"}},"required":["candidate_id","job_id"]}}}
register_tool("generate_interview_questions", schema_interview_questions, _tool_generate_interview_questions)

# ── Phase 2.2 Business Tools ──
register_tool("enroll_in_course", {"type":"function","function":{"name":"enroll_in_course","description":"Enroll an employee in a training course. Checks for duplicate enrollment.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"course_id":{"type":"string"}},"required":["employee_id","course_id"]}}}, tool_enroll_in_course)
register_tool("get_course_catalog", {"type":"function","function":{"name":"get_course_catalog","description":"List available training courses. Filter by category keyword or FUNDAE eligibility.","parameters":{"type":"object","properties":{"category":{"type":"string"},"fundae_only":{"type":"boolean"}},"required":[]}}}, tool_get_course_catalog)
register_tool("recommend_courses", {"type":"function","function":{"name":"recommend_courses","description":"Get AI-powered course recommendations for an employee based on role, department, and history.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"limit":{"type":"integer"}},"required":["employee_id"]}}}, tool_recommend_courses)
register_tool("validate_fundae", {"type":"function","function":{"name":"validate_fundae","description":"Run FUNDAE compliance validation for a course enrollment. Returns duration, progress, test, and survey checks.","parameters":{"type":"object","properties":{"enrollment_id":{"type":"string"}},"required":["enrollment_id"]}}}, tool_validate_fundae)
register_tool("create_job_posting", {"type":"function","function":{"name":"create_job_posting","description":"Create a new job posting / vacancy.","parameters":{"type":"object","properties":{"title":{"type":"string"},"department":{"type":"string"},"description":{"type":"string"},"location":{"type":"string"},"employment_type":{"type":"string"}},"required":["title","department","description"]}}}, tool_create_job_posting)
register_tool("add_candidate", {"type":"function","function":{"name":"add_candidate","description":"Add a candidate to a job posting.","parameters":{"type":"object","properties":{"job_id":{"type":"string"},"first_name":{"type":"string"},"last_name":{"type":"string"},"email":{"type":"string"},"phone":{"type":"string"},"source":{"type":"string"},"notes":{"type":"string"}},"required":["job_id","first_name","last_name","email"]}}}, tool_add_candidate)
register_tool("move_candidate_stage", {"type":"function","function":{"name":"move_candidate_stage","description":"Move a candidate to a new pipeline stage (applied, screening, interview, offer, hired, rejected).","parameters":{"type":"object","properties":{"candidate_id":{"type":"string"},"new_stage":{"type":"string"}},"required":["candidate_id","new_stage"]}}}, tool_move_candidate_stage)
register_tool("schedule_interview", {"type":"function","function":{"name":"schedule_interview","description":"Schedule an interview for a candidate with an interviewer.","parameters":{"type":"object","properties":{"candidate_id":{"type":"string"},"interviewer_id":{"type":"string"},"scheduled_at":{"type":"string"},"duration_minutes":{"type":"integer"},"interview_type":{"type":"string"}},"required":["candidate_id","interviewer_id","scheduled_at"]}}}, tool_schedule_interview)
register_tool("get_job_applications", {"type":"function","function":{"name":"get_job_applications","description":"Get all candidates and stage counts for a job posting.","parameters":{"type":"object","properties":{"job_id":{"type":"string"}},"required":["job_id"]}}}, tool_get_job_applications)
register_tool("get_pipeline_stats", {"type":"function","function":{"name":"get_pipeline_stats","description":"Get recruitment pipeline metrics: open jobs, total candidates, stage distribution, avg time-to-hire.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_pipeline_stats)
register_tool("promote_to_employee", {"type":"function","function":{"name":"promote_to_employee","description":"Convert a hired candidate into an employee. Creates User record and marks candidate as hired.","parameters":{"type":"object","properties":{"candidate_id":{"type":"string"},"base_salary":{"type":"number"},"contract_type":{"type":"string"}},"required":["candidate_id"]}}}, tool_promote_to_employee)
register_tool("create_okr", {"type":"function","function":{"name":"create_okr","description":"Create an Objective with optional Key Results for an employee.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"},"krs":{"type":"array","items":{"type":"object"}}},"required":["employee_id","title"]}}}, tool_create_okr)
register_tool("update_key_result", {"type":"function","function":{"name":"update_key_result","description":"Update the current value of a Key Result.","parameters":{"type":"object","properties":{"kr_id":{"type":"string"},"current_value":{"type":"integer"}},"required":["kr_id","current_value"]}}}, tool_update_key_result)
register_tool("create_review", {"type":"function","function":{"name":"create_review","description":"Create a performance review for an employee.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"manager_id":{"type":"string"},"cycle_name":{"type":"string"},"self_assessment":{"type":"string"}},"required":["employee_id","manager_id","cycle_name"]}}}, tool_create_review)
register_tool("get_team_okrs", {"type":"function","function":{"name":"get_team_okrs","description":"Get all OKRs for a department with key result progress.","parameters":{"type":"object","properties":{"department":{"type":"string"}},"required":[]}}}, tool_get_team_okrs)
register_tool("get_kudos_received", {"type":"function","function":{"name":"get_kudos_received","description":"Get recent kudos/recognition received by an employee.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"limit":{"type":"integer"}},"required":["employee_id"]}}}, tool_get_kudos_received)
register_tool("get_pipeline_overview", {"type":"function","function":{"name":"get_pipeline_overview","description":"Get CRM sales pipeline overview: leads by stage with counts, total values, and avg probability.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_pipeline_overview)
register_tool("get_client_details", {"type":"function","function":{"name":"get_client_details","description":"Get detailed client information with associated leads/deals.","parameters":{"type":"object","properties":{"client_id":{"type":"string"}},"required":["client_id"]}}}, tool_get_client_details)
register_tool("search_clients", {"type":"function","function":{"name":"search_clients","description":"Search clients by company name or industry.","parameters":{"type":"object","properties":{"query":{"type":"string"},"industry":{"type":"string"}},"required":[]}}}, tool_search_clients)
register_tool("get_deal_stats", {"type":"function","function":{"name":"get_deal_stats","description":"Get deal statistics: won count/value, loss rate, avg deal size for a period (month/quarter/year).","parameters":{"type":"object","properties":{"period":{"type":"string"}},"required":[]}}}, tool_get_deal_stats)
register_tool("create_task_for_lead", {"type":"function","function":{"name":"create_task_for_lead","description":"Create a calendar task linked to a sales lead.","parameters":{"type":"object","properties":{"lead_id":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"},"due_date":{"type":"string"}},"required":["lead_id","title"]}}}, tool_create_task_for_lead)
register_tool("log_lead_activity", {"type":"function","function":{"name":"log_lead_activity","description":"Log a CRM activity (call, email, meeting, note) for a lead.","parameters":{"type":"object","properties":{"lead_id":{"type":"string"},"activity_type":{"type":"string"},"notes":{"type":"string"}},"required":["lead_id","activity_type","notes"]}}}, tool_log_lead_activity)
register_tool("create_project", {"type":"function","function":{"name":"create_project","description":"Create a new project.","parameters":{"type":"object","properties":{"name":{"type":"string"},"description":{"type":"string"},"status":{"type":"string"}},"required":["name"]}}}, tool_create_project)
register_tool("create_project_task", {"type":"function","function":{"name":"create_project_task","description":"Create a task within a project.","parameters":{"type":"object","properties":{"project_id":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"},"assignee_id":{"type":"string"},"priority":{"type":"string"},"due_date":{"type":"string"}},"required":["project_id","title"]}}}, tool_create_project_task)
register_tool("get_project_status", {"type":"function","function":{"name":"get_project_status","description":"Get project status with task breakdown: total, completed, in_progress, blocked.","parameters":{"type":"object","properties":{"project_id":{"type":"string"}},"required":["project_id"]}}}, tool_get_project_status)
register_tool("create_wiki_page", {"type":"function","function":{"name":"create_wiki_page","description":"Create a wiki page, optionally linked to a project.","parameters":{"type":"object","properties":{"title":{"type":"string"},"content":{"type":"string"},"project_id":{"type":"string"}},"required":["title","content"]}}}, tool_create_wiki_page)
register_tool("get_contracts", {"type":"function","function":{"name":"get_contracts","description":"Get contracts list. Filter by status (draft, pending_signature, active, expired).","parameters":{"type":"object","properties":{"status":{"type":"string"}},"required":[]}}}, tool_get_contracts)
register_tool("get_compliance_status", {"type":"function","function":{"name":"get_compliance_status","description":"Get compliance overview: GDPR, FUNDAE, and labor law status.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_compliance_status)
register_tool("submit_whistleblower", {"type":"function","function":{"name":"submit_whistleblower","description":"Submit a whistleblower report (anonymous or named). Returns tracking code.","parameters":{"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"category":{"type":"string"},"is_anonymous":{"type":"boolean"}},"required":["title","description"]}}}, tool_submit_whistleblower)


async def _tool_negotiate_with_agents(db: AsyncSession, arguments: dict, agent_id: str = None, run_id: str = None) -> str:
    try:
        from app.services.agent_negotiation import run_negotiation, NEGOTIATION_SCENARIOS

        topic = arguments.get("topic", "")
        user_id = arguments.get("user_id", "")
        scenario = arguments.get("scenario", "")
        agent_configs = arguments.get("agent_configs", [])
        max_rounds = int(arguments.get("max_rounds", 5))
        timeout_seconds = int(arguments.get("timeout_seconds", 120))

        if not topic:
            return json.dumps({"error": "Missing required parameter: topic"}, ensure_ascii=False)

        if not agent_configs:
            agent_configs = [
                {"role": "Negotiator A", "agent_type": "negotiator", "id": "agent_a"},
                {"role": "Negotiator B", "agent_type": "negotiator", "id": "agent_b"},
            ]

        result = await run_negotiation(
            topic=topic,
            agent_configs=agent_configs,
            user_id=user_id,
            db=db,
            scenario=scenario if scenario in NEGOTIATION_SCENARIOS else "",
            max_rounds=min(max_rounds, 10),
            timeout_seconds=min(timeout_seconds, 300),
        )

        return json.dumps({
            "consensus_reached": result.consensus_reached,
            "rounds_run": result.rounds_run,
            "total_cost_usd": result.total_cost_usd,
            "total_tokens": result.total_tokens,
            "deadlock_points": result.deadlock_points,
            "suggested_mediator": result.suggested_mediator,
            "final_agreement": result.final_agreement,
            "agent_positions_count": sum(len(r.get("positions", [])) for r in result.agent_positions),
        }, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"Error in negotiate_with_agents tool: {e}")
        return json.dumps({"error": f"Negotiation failed: {str(e)}"}, ensure_ascii=False)


register_tool("negotiate_with_agents", {
    "type": "function",
    "function": {
        "name": "negotiate_with_agents",
        "description": "Run a multi-agent negotiation on a topic. Agents representing different roles negotiate to reach consensus. Supports SCHEDULING, BUDGET_ALLOCATION, POLICY_DRAFTING, and CONTRACT_NEGOTIATION scenarios.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The negotiation topic or question"},
                "user_id": {"type": "string", "description": "ID of the user initiating the negotiation"},
                "scenario": {"type": "string", "description": "Pre-defined scenario: SCHEDULING, BUDGET_ALLOCATION, POLICY_DRAFTING, or CONTRACT_NEGOTIATION"},
                "agent_configs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "description": "Name of the role this agent represents"},
                            "agent_type": {"type": "string", "description": "Agent type category"},
                            "id": {"type": "string", "description": "Unique ID for this agent"}
                        }
                    },
                    "description": "List of agent configurations participating in the negotiation"
                },
                "max_rounds": {"type": "integer", "description": "Maximum negotiation rounds (default 5)"},
                "timeout_seconds": {"type": "integer", "description": "Timeout in seconds (default 120)"}
            },
            "required": ["topic"]
        }
    }
}, _tool_negotiate_with_agents)

register_tool("create_employee", {"type":"function","function":{"name":"create_employee","description":"Create a new employee in the HR system. Sets up profile with email, name, department, role, salary, country, contract type, and vacation allowance.","parameters":{"type":"object","properties":{"email":{"type":"string"},"full_name":{"type":"string"},"department":{"type":"string"},"role":{"type":"string"},"base_salary":{"type":"number"},"country":{"type":"string"},"contract_type":{"type":"string"},"hire_date":{"type":"string"},"vacation_allowance":{"type":"integer"}},"required":["email","full_name","department"]}}}, tool_create_employee)
register_tool("update_employee", {"type":"function","function":{"name":"update_employee","description":"Update any field on an employee record by ID. Fields dict maps column name to new value.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"fields":{"type":"object"}},"required":["employee_id","fields"]}}}, tool_update_employee)
register_tool("archive_employee", {"type":"function","function":{"name":"archive_employee","description":"Archive an employee by setting is_active=False. Fires employee.archived event.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_archive_employee)
register_tool("search_employees_advanced", {"type":"function","function":{"name":"search_employees_advanced","description":"Multi-field employee search: name, email, department, role, active status. Returns matching employees with key fields.","parameters":{"type":"object","properties":{"query":{"type":"string"},"department":{"type":"string"},"role":{"type":"string"},"is_active":{"type":"boolean"},"limit":{"type":"integer"}},"required":[]}}}, tool_search_employees)
register_tool("get_employee_profile_full", {"type":"function","function":{"name":"get_employee_profile_full","description":"Get full employee profile by ID with all canonical fields (no PII).","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_get_employee_profile)
register_tool("get_org_chart", {"type":"function","function":{"name":"get_org_chart","description":"Returns the hierarchical organization structure as a nested tree. Uses manager_id to build the tree.","parameters":{"type":"object","properties":{"max_depth":{"type":"integer"}},"required":[]}}}, tool_get_org_chart)
register_tool("get_span_of_control", {"type":"function","function":{"name":"get_span_of_control","description":"Counts direct reports per manager. Returns list of {manager_name, report_count, department}.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_span_of_control)
register_tool("get_pto_balance", {"type":"function","function":{"name":"get_pto_balance","description":"Get PTO balance for an employee: allowance, used days, remaining days.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_get_pto_balance)
register_tool("get_department_members", {"type":"function","function":{"name":"get_department_members","description":"Lists all active employees in a specific department.","parameters":{"type":"object","properties":{"department":{"type":"string"}},"required":["department"]}}}, tool_get_department_members)
register_tool("get_recent_hires", {"type":"function","function":{"name":"get_recent_hires","description":"Lists employees hired in the last N days.","parameters":{"type":"object","properties":{"days":{"type":"integer"}},"required":[]}}}, tool_get_recent_hires)
register_tool("request_vacation", {"type":"function","function":{"name":"request_vacation","description":"Request vacation days for an employee. Creates a VacationRequest with status=pending and validates no overlapping approved requests.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"start_date":{"type":"string"},"end_date":{"type":"string"},"reason":{"type":"string"}},"required":["employee_id","start_date","end_date"]}}}, tool_request_vacation)
register_tool("approve_vacation", {"type":"function","function":{"name":"approve_vacation","description":"Approve or reject a vacation request. Sets reviewed_by and reviewed_at. Publishes vacation event.","parameters":{"type":"object","properties":{"vacation_id":{"type":"string"},"approved":{"type":"boolean"},"reviewer_id":{"type":"string"}},"required":["vacation_id"]}}}, tool_approve_vacation)
register_tool("get_team_calendar", {"type":"function","function":{"name":"get_team_calendar","description":"Returns all vacations, meetings, and tasks for a team/department in a date range ahead.","parameters":{"type":"object","properties":{"department":{"type":"string"},"days":{"type":"integer"}},"required":[]}}}, tool_get_team_calendar)
register_tool("create_meeting", {"type":"function","function":{"name":"create_meeting","description":"Create a scheduled meeting with organizer, attendees, location, and description.","parameters":{"type":"object","properties":{"title":{"type":"string"},"organizer_id":{"type":"string"},"start_datetime":{"type":"string"},"end_datetime":{"type":"string"},"attendees":{"type":"array","items":{"type":"string"}},"location":{"type":"string"},"description":{"type":"string"}},"required":["title","organizer_id","start_datetime","end_datetime"]}}}, tool_create_meeting)
register_tool("get_work_schedule", {"type":"function","function":{"name":"get_work_schedule","description":"Returns an employee's work schedule from the work_schedules table: day_of_week to {start_time, end_time}.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_get_work_schedule)
register_tool("create_payroll_cycle", {"type":"function","function":{"name":"create_payroll_cycle","description":"Creates a new PayrollCycle with status=draft.","parameters":{"type":"object","properties":{"period_name":{"type":"string"},"start_date":{"type":"string"},"end_date":{"type":"string"}},"required":["period_name","start_date","end_date"]}}}, tool_create_payroll_cycle)
register_tool("process_payroll", {"type":"function","function":{"name":"process_payroll","description":"Triggers payroll processing for a cycle. Generates payslips for all active employees with line items.","parameters":{"type":"object","properties":{"cycle_id":{"type":"string"}},"required":["cycle_id"]}}}, tool_process_payroll)
register_tool("get_payslip", {"type":"function","function":{"name":"get_payslip","description":"Returns a payslip with line items for an employee. If no cycle_id, returns the latest payslip.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"cycle_id":{"type":"string"}},"required":["employee_id"]}}}, tool_get_payslip)
register_tool("get_tax_rules", {"type":"function","function":{"name":"get_tax_rules","description":"Returns tax rules. Filter by country code if provided.","parameters":{"type":"object","properties":{"country_code":{"type":"string"}},"required":[]}}}, tool_get_tax_rules)
register_tool("update_compensation", {"type":"function","function":{"name":"update_compensation","description":"Updates an employee's base_salary and currency. Fires salary.changed event.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"base_salary":{"type":"number"},"currency":{"type":"string"}},"required":["employee_id","base_salary"]}}}, tool_update_compensation)
register_tool("create_bonus", {"type":"function","function":{"name":"create_bonus","description":"Creates a Bonus record for an employee with status=pending.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"amount":{"type":"number"},"description":{"type":"string"},"bonus_type":{"type":"string"}},"required":["employee_id","amount","description"]}}}, tool_create_bonus)
register_tool("get_financial_ledger", {"type":"function","function":{"name":"get_financial_ledger","description":"Returns journal entries within a date range with their line items.","parameters":{"type":"object","properties":{"start_date":{"type":"string"},"end_date":{"type":"string"},"limit":{"type":"integer"}},"required":[]}}}, tool_get_financial_ledger)
register_tool("get_expense_summary_agg", {"type":"function","function":{"name":"get_expense_summary_agg","description":"Aggregates expenses across departments and categories: totals, by category, by department.","parameters":{"type":"object","properties":{"department":{"type":"string"},"start_date":{"type":"string"},"end_date":{"type":"string"}},"required":[]}}}, tool_get_expense_summary)
register_tool("clock_in", {"type":"function","function":{"name":"clock_in","description":"Creates a new TimeLog entry with clock_in set to now. Validates no active session exists.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"notes":{"type":"string"}},"required":["employee_id"]}}}, tool_clock_in)
register_tool("clock_out", {"type":"function","function":{"name":"clock_out","description":"Sets clock_out to now on an existing TimeLog entry.","parameters":{"type":"object","properties":{"log_id":{"type":"string"},"notes":{"type":"string"}},"required":["log_id"]}}}, tool_clock_out)
register_tool("get_time_logs", {"type":"function","function":{"name":"get_time_logs","description":"Returns time log entries for an employee in a date range.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"start_date":{"type":"string"},"end_date":{"type":"string"}},"required":["employee_id"]}}}, tool_get_time_logs)
register_tool("assign_it_ticket", {"type":"function","function":{"name":"assign_it_ticket","description":"Assigns an IT support ticket to a support agent. Sets status to in_progress.","parameters":{"type":"object","properties":{"ticket_id":{"type":"string"},"assignee_id":{"type":"string"}},"required":["ticket_id","assignee_id"]}}}, tool_assign_it_ticket)
register_tool("resolve_it_ticket", {"type":"function","function":{"name":"resolve_it_ticket","description":"Resolves an IT ticket: sets status=resolved, resolved_at, resolution_notes. Generates KB article reference.","parameters":{"type":"object","properties":{"ticket_id":{"type":"string"},"resolution_notes":{"type":"string"}},"required":["ticket_id","resolution_notes"]}}}, tool_resolve_it_ticket)
register_tool("get_it_assets", {"type":"function","function":{"name":"get_it_assets","description":"Lists IT assets. Filter by assigned employee or category.","parameters":{"type":"object","properties":{"assigned_to_id":{"type":"string"},"category":{"type":"string"}},"required":[]}}}, tool_get_it_assets)
register_tool("get_ticket_stats", {"type":"function","function":{"name":"get_ticket_stats","description":"Returns IT ticket statistics: opened, resolved, avg resolution time, grouped by category.","parameters":{"type":"object","properties":{"days":{"type":"integer"}},"required":[]}}}, tool_get_ticket_stats)

# ── PLATFORM EXTENDED TOOLS ──────────────────────────────────────────────────
from app.services.platform_tools_extended import (
    tool_get_employee_attendance, tool_get_employee_documents,
    tool_get_budget_summary, tool_get_compensation_benchmarks,
    tool_update_deal_stage, tool_get_activity_timeline,
    tool_get_project_timeline, tool_update_task_status,
    tool_get_my_okrs, tool_get_review_feedback, tool_generate_career_path,
    tool_get_gdpr_export, tool_create_announcement,
    tool_get_workflow_templates, tool_get_workflow_status,
    tool_get_user_notifications, tool_mark_notification_read,
    tool_get_active_integrations, tool_get_tenant_config,
    tool_get_billing_status, tool_get_surveys,
    tool_get_chat_channels, tool_search_messages,
)

register_tool("get_employee_attendance", {"type":"function","function":{"name":"get_employee_attendance","description":"Get employee attendance/time logs for the past N days. Shows clock in/out times and total hours worked.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"},"days":{"type":"integer"}},"required":["employee_id"]}}}, tool_get_employee_attendance)
register_tool("get_employee_documents", {"type":"function","function":{"name":"get_employee_documents","description":"List all documents associated with an employee.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_get_employee_documents)
register_tool("get_budget_summary", {"type":"function","function":{"name":"get_budget_summary","description":"Returns budget summary by department for a given year. Shows total budget, spent, remaining.","parameters":{"type":"object","properties":{"department":{"type":"string"},"year":{"type":"integer"}},"required":[]}}}, tool_get_budget_summary)
register_tool("get_compensation_benchmarks", {"type":"function","function":{"name":"get_compensation_benchmarks","description":"Returns market salary benchmarks for a given role and department. Shows p25-p90 percentiles.","parameters":{"type":"object","properties":{"role":{"type":"string"},"department":{"type":"string"}},"required":[]}}}, tool_get_compensation_benchmarks)
register_tool("update_deal_stage", {"type":"function","function":{"name":"update_deal_stage","description":"Move a CRM deal to a new stage. Logs the transition with notes.","parameters":{"type":"object","properties":{"deal_id":{"type":"string"},"new_stage":{"type":"string"},"notes":{"type":"string"}},"required":["deal_id","new_stage"]}}}, tool_update_deal_stage)
register_tool("get_activity_timeline", {"type":"function","function":{"name":"get_activity_timeline","description":"Returns the activity timeline for any entity (lead, deal, client, employee).","parameters":{"type":"object","properties":{"entity_type":{"type":"string"},"entity_id":{"type":"string"},"limit":{"type":"integer"}},"required":["entity_type","entity_id"]}}}, tool_get_activity_timeline)
register_tool("get_project_timeline", {"type":"function","function":{"name":"get_project_timeline","description":"Returns project Gantt/timeline data with tasks, dependencies, and milestones.","parameters":{"type":"object","properties":{"project_id":{"type":"string"},"days":{"type":"integer"}},"required":[]}}}, tool_get_project_timeline)
register_tool("update_task_status", {"type":"function","function":{"name":"update_task_status","description":"Update the status of a project task (todo, in_progress, done, blocked).","parameters":{"type":"object","properties":{"task_id":{"type":"string"},"new_status":{"type":"string"},"notes":{"type":"string"}},"required":["task_id","new_status"]}}}, tool_update_task_status)
register_tool("get_my_okrs", {"type":"function","function":{"name":"get_my_okrs","description":"Returns all OKRs for an employee with progress percentages.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_get_my_okrs)
register_tool("get_review_feedback", {"type":"function","function":{"name":"get_review_feedback","description":"Get 360 review feedback summary for an employee with category averages.","parameters":{"type":"object","properties":{"subject_id":{"type":"string"}},"required":["subject_id"]}}}, tool_get_review_feedback)
register_tool("generate_career_path", {"type":"function","function":{"name":"generate_career_path","description":"Generate potential career development paths for an employee based on skills and goals.","parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}, tool_generate_career_path)
register_tool("get_gdpr_export", {"type":"function","function":{"name":"get_gdpr_export","description":"Check GDPR data export status for a user. Lists personal data sections available for export.","parameters":{"type":"object","properties":{"user_id":{"type":"string"}},"required":["user_id"]}}}, tool_get_gdpr_export)
register_tool("create_announcement", {"type":"function","function":{"name":"create_announcement","description":"Create a company announcement draft. Use admin panel to publish.","parameters":{"type":"object","properties":{"title":{"type":"string"},"content":{"type":"string"},"department":{"type":"string"},"priority":{"type":"string"}},"required":["title","content"]}}}, tool_create_announcement)
register_tool("get_workflow_templates", {"type":"function","function":{"name":"get_workflow_templates","description":"List all available pre-built workflow templates with step counts.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_workflow_templates)
register_tool("get_workflow_status", {"type":"function","function":{"name":"get_workflow_status","description":"Get the current status and progress of a running workflow instance.","parameters":{"type":"object","properties":{"workflow_id":{"type":"string"}},"required":["workflow_id"]}}}, tool_get_workflow_status)
register_tool("get_user_notifications", {"type":"function","function":{"name":"get_user_notifications","description":"Get notifications for a user. Filter to unread only.","parameters":{"type":"object","properties":{"user_id":{"type":"string"},"limit":{"type":"integer"},"unread_only":{"type":"boolean"}},"required":["user_id"]}}}, tool_get_user_notifications)
register_tool("mark_notification_read", {"type":"function","function":{"name":"mark_notification_read","description":"Mark a notification as read.","parameters":{"type":"object","properties":{"notification_id":{"type":"string"}},"required":["notification_id"]}}}, tool_mark_notification_read)
register_tool("get_active_integrations", {"type":"function","function":{"name":"get_active_integrations","description":"List all active third-party integrations and their status.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_active_integrations)
register_tool("get_tenant_config", {"type":"function","function":{"name":"get_tenant_config","description":"Get current tenant settings: modules enabled, languages, timezone, features.","parameters":{"type":"object","properties":{},"required":[]}}}, tool_get_tenant_config)
register_tool("get_billing_status", {"type":"function","function":{"name":"get_billing_status","description":"Get billing status: plan, next billing date, usage metrics.","parameters":{"type":"object","properties":{"tenant_id":{"type":"string"}},"required":[]}}}, tool_get_billing_status)
register_tool("get_surveys", {"type":"function","function":{"name":"get_surveys","description":"List pulse surveys. Filter by status.","parameters":{"type":"object","properties":{"status":{"type":"string"}},"required":[]}}}, tool_get_surveys)
register_tool("get_chat_channels", {"type":"function","function":{"name":"get_chat_channels","description":"List chat channels available to the user.","parameters":{"type":"object","properties":{"user_id":{"type":"string"}},"required":[]}}}, tool_get_chat_channels)
register_tool("search_messages", {"type":"function","function":{"name":"search_messages","description":"Search chat messages for keywords in a channel.","parameters":{"type":"object","properties":{"query":{"type":"string"},"channel_id":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}}, tool_search_messages)

HANDOFF_TO_SPECIALIST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "handoff_to_specialist",
        "description": "Hand off the current conversation to a specialist agent. Use this when you cannot handle a request and need to transfer to the appropriate specialist: payroll_specialist for payroll, recruiter for hiring, hr_assistant for HR, it_helpdesk for IT, sales_coach for CRM, performance_coach for OKRs/reviews, onboarding_buddy for onboarding, compliance_officer for compliance, data_analyst for analytics, finance_manager for finance.",
        "parameters": {
            "type": "object",
            "properties": {
                "to_agent_type": {"type": "string", "description": "The specialist agent type to hand off to (e.g. payroll_specialist, recruiter, it_helpdesk, hr_assistant)"},
                "user_id": {"type": "string", "description": "The user ID of the person making the request"},
                "task": {"type": "string", "description": "A clear description of what the specialist needs to handle"},
                "session_id": {"type": "string", "description": "The current session ID (optional)"},
                "context": {"type": "object", "description": "Optional context dict with summary, decisions, and open_items from the current conversation"}
            },
            "required": ["to_agent_type", "user_id", "task"]
        }
    }
}
register_tool("handoff_to_specialist", HANDOFF_TO_SPECIALIST_SCHEMA, _tool_handoff_to_specialist)
