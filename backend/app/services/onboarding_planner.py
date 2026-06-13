# app/services/onboarding_planner.py — AI-guided onboarding journey generator
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.event_catalog import ONBOARDING_COMPLETED, WORKFLOW_ASSIGNED
from app.services.event_sourcing import publish_event

logger = logging.getLogger("successcore.onboarding_planner")

ONBOARDING_PLAN_PROMPT = """You are an expert HR onboarding designer for a SaaS company called SuccessCore (100-500 employees). 
Design a comprehensive, personalized onboarding plan for the following employee:

Employee Profile:
- Full Name: {full_name}
- Role/Title: {role}
- Department: {department}
- Location: {location}
- Seniority (from hire_date): {seniority}
- Manager: {manager_name}
- Company Size: 100-500 employees (mid-market SaaS)

Context:
- Company offers: HR SaaS platform
- Available training courses: {training_courses}
- Culture: Innovation-focused, collaborative, remote-friendly, data-driven

Design the onboarding plan adapting to:
- Department: engineering plans have codebase/architecture learning; sales plans have product demos and CRM training; HR plans have policy reviews
- Seniority: junior employees get more structured support and mentoring; senior employees get strategic context, stakeholder introductions, and autonomy
- Location: remote employees get async activities and virtual coffee meetings; on-site employees get office tours and in-person meetings

Output ONLY valid JSON, no markdown formatting, no code blocks. Format:
{{
  "week_by_week": [
    {{
      "week_number": 1,
      "theme": "string",
      "tasks": [
        {{
          "day": 1,
          "title": "string",
          "description": "string",
          "action_type": "string (one of: send_email, create_task, schedule_meeting, enroll_in_training, create_it_ticket, send_notification, assign_task, wait_for_approval)",
          "assignee": "string (one of: employee, manager, hr_admin, it_admin, buddy)",
          "duration_minutes": 60,
          "required_resources": ["resource1", "resource2"]
        }}
      ]
    }}
  ],
  "first_day_schedule": [
    {{"time": "09:00", "activity": "string", "duration_minutes": 30, "with": "string"}}
  ],
  "required_setup": {{
    "equipment": ["item1"],
    "accounts": ["system1"],
    "software": ["app1"],
    "access_levels": ["repo-level", "folder-level"]
  }},
  "training_modules": [
    {{"course_title": "string", "priority": "high/medium/low", "timing_week": 1, "reason": "string"}}
  ],
  "key_contacts": {{
    "manager": {{"name": "string", "first_meeting": "day 1"}},
    "buddy": {{"name": "TBD", "first_meeting": "day 1"}},
    "team_members": ["role1", "role2"],
    "cross_functional": ["role1", "role2"]
  }},
  "30_60_90_day_goals": {{
    "day_30": ["goal1", "goal2"],
    "day_60": ["goal1", "goal2"],
    "day_90": ["goal1", "goal2"]
  }},
  "culture_items": ["item1", "item2"],
  "total_duration_weeks": 4
}}"""


WELCOME_PROMPT = """You are the CEO of SuccessCore, a mid-market HR SaaS company. Write a warm, personalized welcome message for a new employee.

Employee Profile:
- Full Name: {full_name}
- Role/Title: {role}
- Department: {department}
- Location: {location}
- Manager: {manager_name}

Tone: friendly, inspiring, professional. Mention:
1. Why we're excited to have them
2. Their role's impact on the company mission
3. What they'll experience in their first week
4. A note about our culture (innovation, collaboration, remote-friendly, data-driven)
5. Who they can reach out to for help

Output ONLY valid JSON, no markdown:
{{
  "subject": "string",
  "html_body": "<p>HTML formatted</p>",
  "plain_body": "Plain text version"
}}"""


BUDDY_SELECTION_PROMPT = """You are an HR specialist assigning onboarding buddies for new hires at SuccessCore (mid-market SaaS, 100-500 employees).

New Hire:
- Full Name: {full_name}
- Role: {role}
- Department: {department}
- Seniority: {seniority}

Available Candidates (from same department, >6 months tenure, not manager, not already a buddy):
{candidates_json}

Criteria for selection:
1. Same team/sub-team if possible
2. Similar role for mentorship relevance
3. Not overloaded (not currently an active buddy)
4. Longer tenure preferred
5. Known to be collaborative and helpful

Rank the top 3 candidates and select the best. Output ONLY valid JSON:
{{
  "selected_buddy": {{
    "user_id": "string",
    "full_name": "string",
    "email": "string",
    "role": "string",
    "tenure_months": 0
  }},
  "reasoning": "Detailed explanation of selection",
  "ranked_candidates": [
    {{"user_id": "string", "full_name": "string", "score": 0-100, "strengths": ["str1"], "weaknesses": ["str1"]}}
  ]
}}"""


def _get_llm_client():
    import os
    from openai import AsyncOpenAI
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key)


async def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
    client = _get_llm_client()
    if not client:
        logger.warning("No OPENAI_API_KEY configured — returning mock onboarding data")
        return None

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


async def _fetch_employee_profile(employee_id: str, db: AsyncSession) -> dict:
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == employee_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"Employee {employee_id} not found")

    manager_name = ""
    if user.manager_id:
        mgr_result = await db.execute(select(User).where(User.id == user.manager_id))
        mgr = mgr_result.scalar_one_or_none()
        if mgr:
            manager_name = mgr.full_name or mgr.email

    now = datetime.now(timezone.utc)
    hire_date = user.hire_date or now
    months_employed = max(0, (now - hire_date).days // 30)
    if months_employed <= 3:
        seniority = "new_hire"
    elif months_employed <= 24:
        seniority = "junior"
    elif months_employed <= 60:
        seniority = "mid_level"
    elif months_employed <= 120:
        seniority = "senior"
    else:
        seniority = "executive"

    return {
        "employee_id": user.id,
        "full_name": user.full_name or user.email,
        "email": user.email,
        "role": user.role or "employee",
        "department": user.department or "General",
        "location": user.country or "ES",
        "seniority": seniority,
        "manager_id": user.manager_id,
        "manager_name": manager_name,
        "hire_date": hire_date.isoformat() if hire_date else None,
    }


async def _fetch_training_courses(db: AsyncSession) -> list[str]:
    from app.models.training import Course
    result = await db.execute(select(Course.title).limit(30))
    return [row[0] for row in result.fetchall() if row[0]]


def _build_mock_plan(profile: dict, courses: list[str]) -> dict:
    role = profile.get("role", "employee")
    dept = profile.get("department", "General")
    seniority = profile.get("seniority", "junior")
    location = profile.get("location", "ES")
    is_remote = location not in ("ES", "MX", "CO", "AR", "CL", "PE") or "remote" in str(profile.get("role", "")).lower()

    if "engineering" in dept.lower() or "dev" in dept.lower() or "tech" in dept.lower():
        dept_type = "engineering"
    elif "sales" in dept.lower() or "marketing" in dept.lower():
        dept_type = "sales"
    else:
        dept_type = "general"

    if is_remote:
        location_type = "remote"
    else:
        location_type = "onsite"

    weeks = 4 if "senior" in seniority or "executive" in seniority else 6 if "junior" in seniority else 5

    first_day = [
        {"time": "09:00", "activity": "Welcome and IT setup verification", "duration_minutes": 30, "with": "IT Admin"},
        {"time": "09:30", "activity": "Meet your manager — role expectations and team intro", "duration_minutes": 60, "with": "Manager"},
        {"time": "10:30", "activity": "Meet your onboarding buddy", "duration_minutes": 30, "with": "Onboarding Buddy"},
        {"time": "11:00", "activity": "Office tour" if not is_remote else "Virtual office tour and tool walkthrough", "duration_minutes": 45, "with": "Buddy"},
        {"time": "12:00", "activity": "Lunch with team" if not is_remote else "Virtual coffee with team", "duration_minutes": 60, "with": "Team"},
        {"time": "13:00", "activity": "HR policies and benefits overview", "duration_minutes": 60, "with": "HR Admin"},
        {"time": "14:00", "activity": "Set up accounts and access credentials", "duration_minutes": 60, "with": "IT Admin"},
        {"time": "15:00", "activity": "Company culture and values session", "duration_minutes": 45, "with": "HR Admin"},
        {"time": "16:00", "activity": "Wrap-up: Q&A and first day reflections", "duration_minutes": 30, "with": "Manager"},
    ]

    week_by_week = []
    dept_tasks = {
        "engineering": [
            "Clone codebase and review architecture docs",
            "Set up local development environment",
            "Pair programming session with buddy",
            "Review CI/CD pipeline and deployment process",
            "Shadow on-call rotation (observe)",
            "First small PR assigned and reviewed",
        ],
        "sales": [
            "Learn product demo script",
            "Shadow discovery call with manager",
            "CRM overview and pipeline management",
            "Competitor landscape deep dive",
            "Practice demo with buddy (recorded)",
            "First qualified lead assignment",
        ],
        "general": [
            "Review department processes and workflows",
            "Shadow key team meetings",
            "Set up 1:1s with cross-functional partners",
            "Review quarterly OKRs and KPIs",
            "Map out stakeholder relationships",
            "First solo task assignment",
        ],
    }
    tasks_for_dept = dept_tasks.get(dept_type, dept_tasks["general"])

    week_themes = {
        "engineering": ["Welcome & Setup", "Codebase Deep Dive", "First Contributions", "Cross-Functional Context"],
        "sales": ["Welcome & Setup", "Product Knowledge", "Pipeline & Process", "First Outreach"],
        "general": ["Welcome & Setup", "Process & Tools", "Stakeholder Connections", "Independent Contribution"],
    }
    themes = week_themes.get(dept_type, week_themes["general"])

    for w in range(weeks):
        week_num = w + 1
        theme_idx = min(w, len(themes) - 1)
        week_tasks = []
        for d, task in enumerate(tasks_for_dept[:min(5, len(tasks_for_dept))]):
            assignee = "employee"
            if d == 0:
                assignee = "manager"
            elif d == 1:
                assignee = "it_admin" if dept_type == "engineering" else "manager"
            elif d == 4:
                assignee = "buddy"
            week_tasks.append({
                "day": (week_num - 1) * 5 + d + 1,
                "title": task,
                "description": f"Week {week_num}: {task}",
                "action_type": "create_task",
                "assignee": assignee,
                "duration_minutes": 60,
                "required_resources": ["Computer", "Company wiki access"] if d <= 1 else [],
            })
        week_by_week.append({
            "week_number": week_num,
            "theme": themes[theme_idx] if theme_idx < len(themes) else "Integration & Autonomy",
            "tasks": week_tasks,
        })

    course_candidates = [c for c in courses if any(kw in c.lower() for kw in ["onboarding", "security", "compliance", "hr", "code of conduct"])]
    if len(course_candidates) < 2:
        course_candidates += courses[:3]

    training_modules = []
    for i, c in enumerate(course_candidates[:4]):
        training_modules.append({
            "course_title": c,
            "priority": "high" if i == 0 else "medium",
            "timing_week": i + 1,
            "reason": "Essential compliance" if "compliance" in c.lower() or "security" in c.lower() else "Role-specific skill building",
        })

    seniority_goals = {
        "new_hire": {"day_30": ["Complete all compliance training", "Understand team workflow", "Make first contribution"], "day_60": ["Own one small feature/task end-to-end", "Build relationships with cross-functional partners"], "day_90": ["Operate independently on regular tasks", "Present learnings to team"]},
        "junior": {"day_30": ["Complete onboarding training", "Learn team tools and processes", "Complete first assigned tasks"], "day_60": ["Take ownership of a small project", "Present team meeting content"], "day_90": ["Ship an independent feature", "Mentor incoming interns"]},
        "mid_level": {"day_30": ["Understand team objectives and OKRs", "Identify process improvements", "Establish cross-functional relationships"], "day_60": ["Lead a small initiative", "Document best practices"], "day_90": ["Drive measurable impact", "Contribute to team strategy"]},
        "senior": {"day_30": ["Map stakeholder landscape", "Identify strategic opportunities", "Share external perspective"], "day_60": ["Propose roadmap contribution", "Mentor team members"], "day_90": ["Drive strategic initiative", "Establish thought leadership"]},
        "executive": {"day_30": ["Understand full org structure", "Build executive relationships", "Identify top priorities"], "day_60": ["Present strategic vision", "Align with board/leadership"], "day_90": ["Drive organizational impact", "Set long-term vision"]},
    }
    goals = seniority_goals.get(seniority, seniority_goals["junior"])

    culture_items = [
        "Innovation-first: we encourage experimentation and learning from failure",
        "Radical transparency: all-hands meetings, open dashboards, and honest feedback",
        "Remote-native collaboration: async-first communication, strong documentation culture",
        "Customer obsession: every decision starts with customer impact",
        "Continuous growth: learning budget, internal mobility, mentorship programs",
    ]
    if is_remote:
        culture_items.append("Distributed team rituals: virtual coffees, remote game nights, and quarterly offsites")

    return {
        "week_by_week": week_by_week,
        "first_day_schedule": first_day,
        "required_setup": {
            "equipment": ["Laptop", "Monitor", "Headset", "Webcam"] if is_remote else ["Laptop", "Monitor", "Keyboard", "Mouse"],
            "accounts": ["Email", "Slack/Teams", "HRIS", "GitHub" if dept_type == "engineering" else "CRM" if dept_type == "sales" else "Company intranet", "Password manager"],
            "software": ["VS Code" if dept_type == "engineering" else "Sales CRM" if dept_type == "sales" else "Office Suite", "VPN client", "Video conferencing tool", "Project management tool"],
            "access_levels": ["Code repos: read" if dept_type == "engineering" else "CRM: read" if dept_type == "sales" else "Company drive: read", "HR system: employee self-service", "Building access badge" if not is_remote else "Remote access VPN"],
        },
        "training_modules": training_modules,
        "key_contacts": {
            "manager": {"name": profile.get("manager_name", "HR Admin"), "first_meeting": "day 1"},
            "buddy": {"name": "TBD (auto-assigned)", "first_meeting": "day 1"},
            "team_members": ["Direct team members"],
            "cross_functional": ["HR Business Partner", "IT Support", "Department lead"],
        },
        "30_60_90_day_goals": goals,
        "culture_items": culture_items,
        "total_duration_weeks": weeks,
    }


async def generate_onboarding_plan(employee_id: str, db: AsyncSession) -> dict:
    profile = await _fetch_employee_profile(employee_id, db)
    courses = await _fetch_training_courses(db)

    user_prompt = ONBOARDING_PLAN_PROMPT.format(
        full_name=profile["full_name"],
        role=profile["role"],
        department=profile["department"],
        location=profile["location"],
        seniority=profile["seniority"],
        manager_name=profile.get("manager_name", "HR Admin"),
        training_courses=json.dumps(courses[:15]),
    )

    plan = await _call_llm(
        "You are an expert HR onboarding designer. Output ONLY valid JSON, no markdown, no explanation.",
        user_prompt,
        temperature=0.7,
    )

    if plan is None:
        plan = _build_mock_plan(profile, courses)

    plan["employee_id"] = employee_id
    plan["generated_at"] = datetime.now(timezone.utc).isoformat()
    plan["ai_generated"] = True

    return plan


async def assign_onboarding_buddy(employee_id: str, db: AsyncSession) -> dict:
    profile = await _fetch_employee_profile(employee_id, db)
    from app.models.user import User
    from app.models.workflow import UserWorkflow

    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    result = await db.execute(
        select(User).where(
            User.department == profile["department"],
            User.id != employee_id,
            User.id != profile.get("manager_id", ""),
            User.is_active == True,
            User.hire_date <= six_months_ago,
        )
    )
    candidates = result.scalars().all()

    active_buddy_ids = set()
    buddy_workflows = await db.execute(
        select(UserWorkflow).where(
            UserWorkflow.status == "in_progress",
            UserWorkflow.template_id.in_(
                select(UserWorkflow.template_id).where(UserWorkflow.user_id.in_([c.id for c in candidates]))
            ),
        )
    )
    for uw in buddy_workflows.scalars():
        active_buddy_ids.add(uw.user_id)

    filtered = [c for c in candidates if c.id not in active_buddy_ids]

    if not filtered:
        result2 = await db.execute(
            select(User).where(
                User.department == profile["department"],
                User.id != employee_id,
                User.id != profile.get("manager_id", ""),
                User.is_active == True,
            )
        )
        filtered = result2.scalars().all()

    if not filtered:
        return {
            "selected_buddy": None,
            "reasoning": "No eligible candidates found in the department.",
            "ranked_candidates": [],
        }

    candidate_data = [
        {
            "user_id": c.id,
            "full_name": c.full_name or c.email,
            "email": c.email,
            "role": c.role or "employee",
            "tenure_months": max(0, (datetime.now(timezone.utc) - (c.hire_date or datetime.now(timezone.utc))).days // 30),
        }
        for c in filtered[:20]
    ]

    prompt = BUDDY_SELECTION_PROMPT.format(
        full_name=profile["full_name"],
        role=profile["role"],
        department=profile["department"],
        seniority=profile.get("seniority", "junior"),
        candidates_json=json.dumps(candidate_data),
    )

    result_llm = await _call_llm(
        "You are an HR specialist assigning onboarding buddies. Output ONLY valid JSON.",
        prompt,
        temperature=0.5,
    )

    if result_llm is None:
        best = candidate_data[0]
        result_llm = {
            "selected_buddy": best,
            "reasoning": f"Selected {best['full_name']} as the best available match (fallback — no LLM available).",
            "ranked_candidates": [{"user_id": c["user_id"], "full_name": c["full_name"], "score": 80 - i * 5, "strengths": ["Same department"], "weaknesses": []} for i, c in enumerate(candidate_data[:3])],
        }

    return result_llm


async def create_onboarding_workflow(employee_id: str, plan: dict, db: AsyncSession) -> dict:
    from app.models.workflow import WorkflowTemplate, UserWorkflow

    template_id = uuid.uuid4().hex
    steps = []

    first_day = plan.get("first_day_schedule", [])
    for item in first_day:
        steps.append({
            "id": uuid.uuid4().hex,
            "title": item.get("activity", "First day activity"),
            "role": "employee",
            "deadline_days": 1,
            "action_type": "schedule_meeting",
            "assignee": item.get("with", "manager").lower().replace(" ", "_"),
            "duration_minutes": item.get("duration_minutes", 30),
        })

    for week in plan.get("week_by_week", []):
        for task in week.get("tasks", []):
            steps.append({
                "id": uuid.uuid4().hex,
                "title": task.get("title", "Task"),
                "role": task.get("assignee", "employee"),
                "deadline_days": week.get("week_number", 1) * 7,
                "action_type": task.get("action_type", "create_task"),
                "assignee": task.get("assignee", "employee"),
                "description": task.get("description", ""),
                "duration_minutes": task.get("duration_minutes", 60),
            })

    template = WorkflowTemplate(
        id=template_id,
        name=f"AI Onboarding — {plan.get('employee_id', employee_id)}",
        type="onboarding",
        steps=steps,
    )
    db.add(template)

    user_workflow_id = uuid.uuid4().hex
    steps_status = {}
    for step in steps:
        steps_status[step["id"]] = {"completed": False, "completed_at": None, "completed_by": None}

    user_workflow = UserWorkflow(
        id=user_workflow_id,
        user_id=employee_id,
        template_id=template_id,
        status="in_progress",
        steps_status=steps_status,
    )
    db.add(user_workflow)
    await db.commit()

    publish_event(WORKFLOW_ASSIGNED, {
        "workflow_id": user_workflow_id,
        "user_id": employee_id,
        "template_id": template_id,
        "total_steps": len(steps),
    }, tenant_id="acme_corp")

    return {
        "workflow_id": user_workflow_id,
        "template_id": template_id,
        "total_steps": len(steps),
        "steps": [{"id": s["id"], "title": s["title"]} for s in steps],
    }


async def complete_onboarding(employee_id: str, user_id: str = "", context: dict = None, db: AsyncSession = None) -> dict:
    if db is None:
        from app.core.database import AsyncSessionGlobal
        async with AsyncSessionGlobal() as session:
            return await _run_onboarding_pipeline(employee_id, user_id, context or {}, session)
    return await _run_onboarding_pipeline(employee_id, user_id, context or {}, db)


async def _run_onboarding_pipeline(employee_id: str, user_id: str, context: dict, db: AsyncSession) -> dict:
    target_id = employee_id or user_id
    if not target_id:
        return {"status": "error", "message": "No employee_id or user_id provided"}

    plan = await generate_onboarding_plan(target_id, db)
    buddy_result = await assign_onboarding_buddy(target_id, db)
    workflow_result = await create_onboarding_workflow(target_id, plan, db)

    export = {
        "status": "completed",
        "employee_id": target_id,
        "plan": plan,
        "buddy": buddy_result,
        "workflow": workflow_result,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    return export


async def get_onboarding_progress(employee_id: str, db: AsyncSession) -> dict:
    from app.models.workflow import UserWorkflow
    from app.models.user import User

    result = await db.execute(
        select(UserWorkflow).where(
            UserWorkflow.user_id == employee_id,
            UserWorkflow.status == "in_progress",
        ).order_by(UserWorkflow.created_at.desc()).limit(1)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        return {
            "employee_id": employee_id,
            "status": "not_found",
            "message": "No active onboarding workflow found",
            "overall_progress_pct": 0,
        }

    emp_result = await db.execute(select(User).where(User.id == employee_id))
    employee = emp_result.scalar_one_or_none()

    steps_status = workflow.steps_status or {}
    total = len(steps_status)
    completed = sum(1 for s in steps_status.values() if s.get("completed"))

    overall_pct = round((completed / total) * 100, 1) if total > 0 else 0

    hire_date = employee.hire_date if employee else None
    days_since_hire = 0
    days_remaining = None
    behind_schedule = False

    if hire_date:
        days_since_hire = (datetime.now(timezone.utc) - hire_date).days
        total_onboarding_days = total * 1.5
        expected_progress_pct = min(100, round((days_since_hire / total_onboarding_days) * 100, 1)) if total_onboarding_days > 0 else 100
        behind_schedule = overall_pct < expected_progress_pct - 10
        if overall_pct < 100:
            days_per_pct = total_onboarding_days / 100 if total_onboarding_days > 0 else 0
            days_remaining = round((100 - overall_pct) * days_per_pct)

    completed_steps = [{"id": k, **v} for k, v in steps_status.items() if v.get("completed")]
    pending_steps = [{"id": k, "title": v.get("title", k)} for k, v in steps_status.items() if not v.get("completed")]

    catch_up = []
    if behind_schedule:
        catch_up = [
            "Schedule a catch-up meeting with your manager and buddy",
            "Prioritize high-impact tasks for the next two weeks",
            "Consider reducing meeting load to focus on onboarding tasks",
            "HR can extend onboarding deadline if needed",
        ]

    return {
        "employee_id": employee_id,
        "workflow_id": workflow.id,
        "status": "in_progress",
        "completed_steps": completed_steps[:20],
        "pending_steps": pending_steps[:20],
        "total_steps": total,
        "completed_count": completed,
        "pending_count": total - completed,
        "overall_progress_pct": overall_pct,
        "days_since_hire": days_since_hire,
        "days_remaining": days_remaining,
        "behind_schedule": behind_schedule,
        "catch_up_recommendations": catch_up,
    }


async def generate_welcome_message(employee_id: str, db: AsyncSession) -> dict:
    profile = await _fetch_employee_profile(employee_id, db)

    prompt = WELCOME_PROMPT.format(
        full_name=profile["full_name"],
        role=profile["role"],
        department=profile["department"],
        location=profile["location"],
        manager_name=profile.get("manager_name", "your manager"),
    )

    message = await _call_llm(
        "You are the CEO of SuccessCore. Write a welcoming, inspiring, professional message.",
        prompt,
        temperature=0.8,
    )

    if message is None:
        message = {
            "subject": f"Welcome to SuccessCore, {profile['full_name']}!",
            "html_body": f"<p>Hi {profile['full_name']},</p><p>Welcome to SuccessCore! We're thrilled to have you join our {profile['department']} team as {profile['role']}.</p><p>Your manager, {profile.get('manager_name', 'your manager')}, will help you get settled in. Your first week will focus on getting to know the team, our tools, and our culture.</p><p>We believe in innovation, collaboration, and data-driven decisions. You're joining a team that values these principles deeply.</p><p>If you need anything, reach out to your manager, your onboarding buddy, or HR. We're all here to support you.</p><p>Welcome aboard!</p><p>— SuccessCore Team</p>",
            "plain_body": f"Hi {profile['full_name']},\n\nWelcome to SuccessCore! We're thrilled to have you join our {profile['department']} team as {profile['role']}.\n\nYour manager, {profile.get('manager_name', 'your manager')}, will help you get settled in. Your first week will focus on getting to know the team, our tools, and our culture.\n\nWe believe in innovation, collaboration, and data-driven decisions. You're joining a team that values these principles deeply.\n\nIf you need anything, reach out to your manager, your onboarding buddy, or HR. We're all here to support you.\n\nWelcome aboard!\n\n— SuccessCore Team",
        }

    return message


async def task_onboarding_setup(task_id: str = "", progress_callback=None, employee_id: str = "", user_id: str = "") -> dict:
    try:
        if progress_callback:
            progress_callback("running", {"progress": 10, "step": "Starting onboarding pipeline"})

        from app.core.database import AsyncSessionGlobal
        async with AsyncSessionGlobal() as db:
            target_id = employee_id or user_id
            if not target_id:
                return {"status": "failed", "error": "No employee_id or user_id provided"}

            if progress_callback:
                progress_callback("running", {"progress": 30, "step": "Generating onboarding plan"})
            plan = await generate_onboarding_plan(target_id, db)

            if progress_callback:
                progress_callback("running", {"progress": 50, "step": "Assigning buddy"})
            buddy = await assign_onboarding_buddy(target_id, db)

            if progress_callback:
                progress_callback("running", {"progress": 70, "step": "Creating workflow"})
            workflow = await create_onboarding_workflow(target_id, plan, db)

            if progress_callback:
                progress_callback("running", {"progress": 90, "step": "Publishing events"})

            publish_event(ONBOARDING_COMPLETED, {
                "employee_id": target_id,
                "workflow_id": workflow.get("workflow_id"),
                "plan_summary": f"{plan.get('total_duration_weeks', 'N/A')} weeks, {workflow.get('total_steps', 0)} steps",
            }, tenant_id="acme_corp")

            if progress_callback:
                progress_callback("completed", {"progress": 100})

            return {
                "status": "completed",
                "employee_id": target_id,
                "plan": plan,
                "buddy": buddy,
                "workflow": workflow,
            }
    except Exception as e:
        logger.error(f"Onboarding pipeline failed for {employee_id or user_id}: {e}", exc_info=True)
        if progress_callback:
            progress_callback("failed", {"progress": 0, "error": str(e)})
        return {"status": "failed", "error": str(e)}


from app.core.task_queue import register_task
register_task("onboarding_setup", task_onboarding_setup)
