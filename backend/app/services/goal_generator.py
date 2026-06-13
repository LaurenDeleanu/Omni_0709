import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.grow import Objective, KeyResult, PerformanceReview
from app.models.training import CourseEnrollment, Course
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

GOAL_TTL = 1800


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return json.loads(raw)


async def _call_llm(system_prompt: str, user_message: str, db: AsyncSession, temperature: float = 0.3) -> dict:
    from app.services.llm_router import get_llm_client
    client, _ = await get_llm_client("gpt-4o-mini", None, db)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=2000,
    )
    raw = response.choices[0].message.content or "{}"
    return _parse_json(raw)


async def _fetch_department_okrs(db: AsyncSession, department: str) -> list:
    result = await db.execute(
        select(User.id).where(User.department == department, User.is_active == True)
    )
    dept_user_ids = [r[0] for r in result.all()]
    if not dept_user_ids:
        return []
    result = await db.execute(
        select(Objective)
        .options(selectinload(Objective.key_results))
        .where(Objective.owner_id.in_(dept_user_ids))
    )
    return result.scalars().all()


async def _fetch_company_okrs(db: AsyncSession) -> list:
    result = await db.execute(
        select(Objective).options(selectinload(Objective.key_results))
    )
    all_obj = result.scalars().all()
    result = await db.execute(select(User).where(User.is_active == True))
    active_users = {u.id: u for u in result.scalars().all()}

    depts = set(u.department for u in active_users.values() if u.department)
    company_obj = []
    for obj in all_obj:
        if obj.owner_id not in active_users:
            company_obj.append(obj)
            continue
        owner = active_users.get(obj.owner_id)
        if owner and owner.role in ("admin", "super_admin", "ceo", "cfo"):
            company_obj.append(obj)
    return company_obj


async def _fetch_employee_goals(db: AsyncSession, employee_id: str) -> list:
    result = await db.execute(
        select(Objective)
        .options(selectinload(Objective.key_results))
        .where(Objective.owner_id == employee_id)
    )
    return result.scalars().all()


async def _get_skill_gaps(db: AsyncSession, employee_id: str) -> dict:
    result = await db.execute(
        select(PerformanceReview)
        .options(selectinload(PerformanceReview.responses))
        .where(PerformanceReview.employee_id == employee_id)
    )
    reviews = result.scalars().all()
    gaps = []
    for r in reviews:
        if r.self_evaluation and r.self_evaluation.get("skill_gaps"):
            gaps.extend(r.self_evaluation["skill_gaps"])
        if r.manager_evaluation and r.manager_evaluation.get("skill_gaps"):
            gaps.extend(r.manager_evaluation["skill_gaps"])
        for resp in r.responses:
            if resp.feedback and resp.feedback.get("skill_gaps"):
                gaps.extend(resp.feedback["skill_gaps"])
    result = await db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == employee_id)
    )
    enrollments = result.scalars().all()
    courses = []
    for e in enrollments:
        c = (await db.execute(select(Course).where(Course.id == e.course_id))).scalar_one_or_none()
        if c:
            courses.append({"id": c.id, "title": c.title, "status": e.status})
    return {"skill_gaps": list(set(gaps)), "courses_enrolled": courses}


async def generate_smart_goals(employee_id: str, db: AsyncSession, count: int = 3) -> dict:
    cache_key = f"smart_goals:{employee_id}:{count}"
    r = await get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    user_result = await db.execute(select(User).where(User.id == employee_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": f"Employee {employee_id} not found"}

    dept_okrs = await _fetch_department_okrs(db, user.department or "")
    company_okrs = await _fetch_company_okrs(db)

    dept_summary = []
    for obj in dept_okrs:
        krs = [{"title": kr.title, "target": kr.target_value, "unit": kr.unit} for kr in (obj.key_results or [])]
        dept_summary.append({"title": obj.title, "description": obj.description, "status": obj.status, "key_results": krs})

    company_summary = []
    for obj in company_okrs[:5]:
        krs = [{"title": kr.title, "target": kr.target_value, "unit": kr.unit} for kr in (obj.key_results or [])]
        company_summary.append({"title": obj.title, "description": obj.description, "status": obj.status, "key_results": krs})

    user_profile = {
        "full_name": user.full_name,
        "role": user.role,
        "department": user.department,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
    }

    system_prompt = (
        "You are a strategic HR coach specialized in creating SMART goals. "
        "Generate goals that are Specific, Measurable, Achievable, Relevant, and Time-bound. "
        "Each goal must align with the company strategy and department OKRs provided. "
        "Return ONLY valid JSON — no markdown, no commentary.\n\n"
        "JSON schema:\n"
        '{"goals": [{\n'
        '  "title": "concise SMART goal",\n'
        '  "description": "detailed explanation of the goal and why it matters",\n'
        '  "key_results": [{"title": "...", "target_value": number, "unit": "%|eur|units|calls|customers", "current_value": 0}],\n'
        '  "alignment": "which company/department OKR this supports",\n'
        '  "difficulty": "easy|medium|hard|stretch",\n'
        '  "estimated_completion_weeks": number,\n'
        '  "suggested_review_cadence": "weekly|biweekly|monthly"\n'
        '}],\n'
        '"alignment_explanation": "narrative explanation of how these goals cascade from company strategy down to this role"}\n\n'
        "Generate exactly the requested number of goals."
    )

    user_message = (
        f"Employee profile: {json.dumps(user_profile, ensure_ascii=False)}\n\n"
        f"Company-level OKRs: {json.dumps(company_summary, ensure_ascii=False)}\n\n"
        f"Department OKRs for {user.department}: {json.dumps(dept_summary, ensure_ascii=False)}\n\n"
        f"Generate {count} SMART goals for this employee that align with the above strategy."
    )

    try:
        result = await _call_llm(system_prompt, user_message, db)
        await r.setex(cache_key, GOAL_TTL, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        logger.error(f"SMART goal generation failed: {e}")
        return {"error": f"Goal generation failed: {str(e)}"}


async def generate_team_objectives(team_id: str, quarter: str, db: AsyncSession) -> dict:
    cache_key = f"team_objectives:{team_id}:{quarter}"
    r = await get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(select(User).where(User.department == team_id, User.is_active == True))
    members = result.scalars().all()
    if not members:
        return {"error": f"No active members found for team/department '{team_id}'"}

    team_profile = {
        "team": team_id,
        "quarter": quarter,
        "headcount": len(members),
        "roles": list(set(u.role for u in members if u.role)),
    }

    company_okrs = await _fetch_company_okrs(db)
    company_summary = []
    for obj in company_okrs[:5]:
        krs = [{"title": kr.title, "target": kr.target_value, "unit": kr.unit} for kr in (obj.key_results or [])]
        company_summary.append({"title": obj.title, "description": obj.description, "key_results": krs})

    system_prompt = (
        "You are a strategic planning coach. Generate quarterly team-level objectives "
        "that cascade from the company strategy. Each objective must have measurable key results. "
        "Return ONLY valid JSON.\n\n"
        '{"team_objectives": [{\n'
        '  "title": "team-level objective title",\n'
        '  "description": "detailed explanation",\n'
        '  "key_results": [{"title": "...", "target_value": number, "unit": "%|eur|units|customers", "current_value": 0}],\n'
        '  "priority": "high|medium|low",\n'
        '  "aligns_to": "which company OKR this supports",\n'
        '  "estimated_completion_weeks": number\n'
        '}],\n'
        '"strategy_cascade": "explanation of how these team objectives derive from company strategy",\n'
        '"quarter": "the quarter string passed in"\n}'
    )

    user_message = (
        f"Team profile: {json.dumps(team_profile, ensure_ascii=False)}\n\n"
        f"Company-level OKRs: {json.dumps(company_summary, ensure_ascii=False)}\n\n"
        f"Generate 3-5 quarterly team objectives for {quarter}."
    )

    try:
        result = await _call_llm(system_prompt, user_message, db)
        await r.setex(cache_key, GOAL_TTL, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        logger.error(f"Team objective generation failed: {e}")
        return {"error": f"Team objective generation failed: {str(e)}"}


async def align_goals_with_company_strategy(employee_id: str, db: AsyncSession) -> dict:
    cache_key = f"goal_alignment:{employee_id}"
    r = await get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    user_result = await db.execute(select(User).where(User.id == employee_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": f"Employee {employee_id} not found"}

    company_okrs = await _fetch_company_okrs(db)
    dept_okrs = await _fetch_department_okrs(db, user.department or "")
    employee_goals = await _fetch_employee_goals(db, employee_id)

    company_tree = []
    for obj in company_okrs[:5]:
        krs = [{"title": kr.title, "target": kr.target_value, "unit": kr.unit, "current": kr.current_value} for kr in (obj.key_results or [])]
        company_tree.append({"level": "company", "id": obj.id, "title": obj.title, "description": obj.description, "key_results": krs})

    dept_tree = []
    for obj in dept_okrs[:5]:
        krs = [{"title": kr.title, "target": kr.target_value, "unit": kr.unit, "current": kr.current_value} for kr in (obj.key_results or [])]
        dept_tree.append({"level": "department", "id": obj.id, "title": obj.title, "description": obj.description, "key_results": krs})

    emp_goals_list = []
    for obj in employee_goals:
        krs = [{"title": kr.title, "target": kr.target_value, "unit": kr.unit, "current": kr.current_value} for kr in (obj.key_results or [])]
        emp_goals_list.append({"level": "individual", "id": obj.id, "title": obj.title, "description": obj.description, "status": obj.status, "key_results": krs})

    system_prompt = (
        "You are an HR alignment analyst. Given company OKRs, department OKRs, and individual employee goals, "
        "analyze how well the individual's goals align with the company strategy. "
        "Identify goals that are misaligned and suggest realignment. "
        "Return ONLY valid JSON.\n\n"
        '{"alignment_map": [{"employee_goal": "goal title", "supports_dept_okr": "dept OKR title or null", "supports_company_okr": "company OKR title or null", "alignment_strength": "strong|moderate|weak|none"}],\n'
        '"misaligned_goals": [{"title": "goal title", "reason": "why it is misaligned", "realignment_suggestion": "suggested reframe"}],\n'
        '"goal_tree": {"company_okrs": [...], "department_okrs": [...], "individual_goals": [...]},\n'
        '"summary": "narrative summary of alignment analysis"\n}'
    )

    user_message = (
        f"Employee: {user.full_name} ({user.role}, {user.department})\n\n"
        f"Company OKRs: {json.dumps(company_tree, ensure_ascii=False)}\n\n"
        f"Department OKRs: {json.dumps(dept_tree, ensure_ascii=False)}\n\n"
        f"Individual goals: {json.dumps(emp_goals_list, ensure_ascii=False)}\n\n"
        f"Analyze alignment and return the goal tree."
    )

    try:
        result = await _call_llm(system_prompt, user_message, db)
        result["goal_tree"] = {
            "company_okrs": company_tree,
            "department_okrs": dept_tree,
            "individual_goals": emp_goals_list,
        }
        await r.setex(cache_key, GOAL_TTL, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        logger.error(f"Goal alignment analysis failed: {e}")
        return {
            "alignment_map": [],
            "misaligned_goals": [],
            "goal_tree": {
                "company_okrs": company_tree,
                "department_okrs": dept_tree,
                "individual_goals": emp_goals_list,
            },
            "summary": f"Alignment analysis failed: {str(e)}",
        }


async def generate_career_development_goals(employee_id: str, db: AsyncSession) -> dict:
    cache_key = f"dev_goals:{employee_id}"
    r = await get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    user_result = await db.execute(select(User).where(User.id == employee_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": f"Employee {employee_id} not found"}

    skill_data = await _get_skill_gaps(db, employee_id)

    user_profile = {
        "full_name": user.full_name,
        "role": user.role,
        "department": user.department,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
    }

    system_prompt = (
        "You are a career development coach. Generate learning & development goals "
        "based on an employee's role, skill gaps identified in performance reviews, and industry trends. "
        "These are separate from performance goals. Include recommended learning resources from the training catalog if available. "
        "Return ONLY valid JSON.\n\n"
        '{"development_goals": [{\n'
        '  "title": "development goal title",\n'
        '  "description": "why this skill matters for career growth",\n'
        '  "category": "technical|leadership|soft_skills|certification|industry_knowledge",\n'
        '  "skill_gap_addressed": "which gap this targets",\n'
        '  "learning_resources": [{"type": "course|book|certification|mentorship", "title": "...", "recommendation": "..."}],\n'
        '  "estimated_completion_weeks": number,\n'
        '  "suggested_courses": ["course titles from the training catalog that match"]\n'
        '}]}'
    )

    user_message = (
        f"Employee profile: {json.dumps(user_profile, ensure_ascii=False)}\n\n"
        f"Skill gaps from reviews: {json.dumps(skill_data['skill_gaps'], ensure_ascii=False)}\n"
        f"Training courses enrolled: {json.dumps(skill_data['courses_enrolled'], ensure_ascii=False)}\n\n"
        f"Generate 2-3 career development goals for this employee."
    )

    try:
        result = await _call_llm(system_prompt, user_message, db)
        await r.setex(cache_key, GOAL_TTL, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        logger.error(f"Career development goal generation failed: {e}")
        return {"error": f"Development goal generation failed: {str(e)}"}


async def suggest_goal_adjustments(employee_id: str, db: AsyncSession) -> dict:
    cache_key = f"goal_adjustments:{employee_id}"
    r = await get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    user_result = await db.execute(select(User).where(User.id == employee_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": f"Employee {employee_id} not found"}

    employee_goals = await _fetch_employee_goals(db, employee_id)
    if not employee_goals:
        return {"adjustments": [], "message": "No existing goals found for this employee."}

    goals_data = []
    for obj in employee_goals:
        krs = []
        for kr in (obj.key_results or []):
            progress_pct = round((kr.current_value / max(kr.target_value, 1)) * 100, 1)
            krs.append({
                "title": kr.title,
                "target_value": kr.target_value,
                "current_value": kr.current_value,
                "unit": kr.unit,
                "progress_pct": progress_pct,
                "id": kr.id,
            })
        goals_data.append({
            "id": obj.id,
            "title": obj.title,
            "description": obj.description,
            "status": obj.status,
            "key_results": krs,
        })

    system_prompt = (
        "You are an agile performance coach conducting a mid-quarter goal review. "
        "Analyze goal progress and suggest adjustments. Be tactical and specific. "
        "Return ONLY valid JSON.\n\n"
        '{"adjustments": [{\n'
        '  "goal_title": "title of the goal being adjusted",\n'
        '  "type": "stretch_up|adjust_down|add_key_result|remove_key_result",\n'
        '  "reason": "data-driven reason for the adjustment",\n'
        '  "recommendation": "specific action to take",\n'
        '  "priority": "critical|high|medium|low",\n'
        '  "details": {"from": "optional - current value", "to": "optional - suggested new value"}\n'
        '}],\n'
        '"summary": "overall assessment of goal progress and key trends"\n}'
    )

    user_message = (
        f"Employee: {user.full_name} ({user.role}, {user.department})\n\n"
        f"Current goals and progress: {json.dumps(goals_data, ensure_ascii=False)}\n\n"
        f"Analyze each goal and suggest adjustments."
    )

    try:
        result = await _call_llm(system_prompt, user_message, db)
        await r.setex(cache_key, GOAL_TTL, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        logger.error(f"Goal adjustment suggestion failed: {e}")
        return {"error": f"Goal adjustment failed: {str(e)}"}
