import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, delete
from app.models.user import User, SkillProfile
from app.models.training import Course, CourseEnrollment

logger = logging.getLogger("successcore.skills")

SKILL_KEYWORDS = {
    "Python": ["python", "django", "flask", "fastapi", "pytest", "numpy", "pandas"],
    "JavaScript": ["javascript", "typescript", "node", "react", "vue", "angular", "next"],
    "Cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "lambda"],
    "Data": ["sql", "postgresql", "mongodb", "redis", "spark", "kafka", "etl", "tableau"],
    "DevOps": ["ci/cd", "jenkins", "github actions", "argocd", "ansible", "prometheus"],
    "Leadership": ["management", "leadership", "strategy", "agile", "scrum", "pmo"],
    "HR": ["recruitment", "payroll", "benefits", "onboarding", "compliance", "l&d"],
    "Finance": ["accounting", "budgeting", "forecasting", "audit", "tax", "sap"],
    "Design": ["figma", "ui/ux", "adobe", "sketch", "prototyping", "wireframing"],
    "Mobile": ["ios", "android", "swift", "kotlin", "flutter", "react native"],
}

# Role requirement profiles (required skill name and level 1-5)
ROLE_REQUIREMENTS = {
    "employee": {
        "Engineering": {"Python": 2, "JavaScript": 2, "Cloud": 1, "Data": 2},
        "Product": {"Leadership": 2, "Design": 2, "Data": 2},
        "Sales": {"Leadership": 2, "HR": 1},
        "Finance": {"Finance": 3, "Data": 2},
        "HR": {"HR": 3, "Leadership": 2},
        "default": {"Leadership": 1}
    },
    "manager": {
        "default": {"Leadership": 3}
    },
    "hr_admin": {
        "default": {"HR": 4, "Leadership": 3, "Finance": 2}
    }
}


async def seed_skills_from_metadata(db: AsyncSession):
    """
    Scans active users and seeds their SkillProfile table based on role & department keywords if empty.
    """
    profile_check = await db.execute(select(SkillProfile).limit(1))
    if profile_check.scalars().first():
        return # Already seeded
        
    logger.info("SkillProfile table is empty. Seeding skills from user metadata...")
    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()
    
    import uuid
    for user in users:
        text_to_scan = f"{user.full_name or ''} {user.department or ''} {user.role or ''}"
        for skill_name, keywords in SKILL_KEYWORDS.items():
            level = 1
            matched = False
            for kw in keywords:
                if kw.lower() in text_to_scan.lower():
                    matched = True
                    # Higher role/tenure defaults to higher skill levels
                    if user.role in ["manager", "hr_admin", "sys_admin"]:
                        level = 3
                    else:
                        level = 2
                    break
            if matched:
                prof = SkillProfile(
                    id=uuid.uuid4().hex,
                    user_id=user.id,
                    skill_name=skill_name,
                    level=level,
                    source="auto_seed"
                )
                db.add(prof)
    await db.commit()


async def get_skills_matrix(db: AsyncSession) -> dict:
    """
    Generates a company-wide skills matrix and identifies general skill gaps.
    """
    await seed_skills_from_metadata(db)
    
    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()
    
    skills_res = await db.execute(select(SkillProfile))
    skills = skills_res.scalars().all()
    
    # Map user id -> list of (skill_name, level)
    user_skills_map = {}
    global_skills = {}
    for s in skills:
        if s.user_id not in user_skills_map:
            user_skills_map[s.user_id] = []
        user_skills_map[s.user_id].append((s.skill_name, s.level))
        global_skills[s.skill_name] = global_skills.get(s.skill_name, 0) + 1
        
    employees = []
    for user in users:
        u_skills = user_skills_map.get(user.id, [])
        employees.append({
            "user_id": user.id,
            "name": user.full_name or user.email,
            "department": user.department,
            "role": user.role,
            "skills": sorted(u_skills, key=lambda x: x[1], reverse=True)
        })
        
    # Find gaps (skills defined in SKILL_KEYWORDS but possessed by nobody)
    skill_gaps = {}
    for category in SKILL_KEYWORDS:
        count = global_skills.get(category, 0)
        if count == 0:
            skill_gaps[category] = {
                "matches": 0,
                "recommendation": f"Critical Gap: No employees possess '{category}' skills. Schedule training courses."
            }
            
    return {
        "total_employees": len(users),
        "skills_distribution": dict(sorted(global_skills.items(), key=lambda x: x[1], reverse=True)),
        "skill_gaps": skill_gaps,
        "employees": employees[:100]
    }


async def extract_skills_from_text(text: str, user_id: str, source: str, db: AsyncSession) -> List[str]:
    """
    Extracts skills from text (resumes, reviews, text completions) using keyword rules and saves them.
    """
    import uuid
    extracted = []
    text_lower = text.lower()
    
    # Simple rule-based extraction
    for skill_name, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                extracted.append(skill_name)
                break
                
    if not extracted:
        return []
        
    # Check current skills for the user
    curr_stmt = select(SkillProfile).where(SkillProfile.user_id == user_id)
    curr_res = await db.execute(curr_stmt)
    curr_profiles = {p.skill_name: p for p in curr_res.scalars().all()}
    
    for skill in extracted:
        level = 2 # standard level extracted from text
        if source == "course_completion":
            level = 3
            
        if skill in curr_profiles:
            profile = curr_profiles[skill]
            # Upgrade level if new source suggests higher/updated level
            if level > profile.level:
                profile.level = level
                profile.source = source
                profile.updated_at = datetime.now(timezone.utc)
        else:
            new_profile = SkillProfile(
                id=uuid.uuid4().hex,
                user_id=user_id,
                skill_name=skill,
                level=level,
                source=source
            )
            db.add(new_profile)
            
    await db.commit()
    return extracted


async def get_skills_gap_analysis(user_id: str, db: AsyncSession) -> dict:
    """
    Performs skills gap analysis for a single user by comparing their SkillProfile against role requirements.
    """
    user = await db.get(User, user_id)
    if not user:
        return {"error": "User not found"}
        
    # Find requirements
    dept = user.department or "default"
    role = user.role or "employee"
    
    requirements = {}
    if role in ROLE_REQUIREMENTS:
        role_reqs = ROLE_REQUIREMENTS[role]
        if dept in role_reqs:
            requirements = role_reqs[dept]
        else:
            requirements = role_reqs.get("default", {})
    else:
        requirements = ROLE_REQUIREMENTS["employee"].get("default", {})
        
    # Get user skills
    skills_stmt = select(SkillProfile).where(SkillProfile.user_id == user_id)
    skills_res = await db.execute(skills_stmt)
    user_skills = {s.skill_name: s.level for s in skills_res.scalars().all()}
    
    gaps = {}
    for req_skill, req_level in requirements.items():
        current_level = user_skills.get(req_skill, 0)
        if current_level < req_level:
            gaps[req_skill] = {
                "required_level": req_level,
                "current_level": current_level,
                "gap": req_level - current_level
            }
            
    return {
        "user_id": user_id,
        "name": user.full_name or user.email,
        "department": dept,
        "role": role,
        "requirements": requirements,
        "current_skills": user_skills,
        "gaps": gaps,
        "has_gaps": len(gaps) > 0
    }


async def recommend_learning_path(user_id: str, db: AsyncSession) -> List[dict]:
    """
    Recommends training courses to help close a user's skills gap.
    """
    gap_analysis = await get_skills_gap_analysis(user_id, db)
    gaps = gap_analysis.get("gaps", {})
    
    if not gaps:
        return []
        
    recommendations = []
    for gap_skill, gap_info in gaps.items():
        # Search for courses that match the skill keywords
        keywords = SKILL_KEYWORDS.get(gap_skill, [gap_skill])
        conditions = [Course.title.ilike(f"%{kw}%") for kw in keywords] + \
                     [Course.description.ilike(f"%{kw}%") for kw in keywords]
                     
        courses_stmt = select(Course).where(or_(*conditions)).where(Course.is_fundae_eligible == True)
        courses_res = await db.execute(courses_stmt)
        courses = courses_res.scalars().all()
        
        for course in courses:
            recommendations.append({
                "skill_name": gap_skill,
                "gap_details": gap_info,
                "course_id": course.id,
                "course_title": course.title,
                "duration_hours": course.min_duration_hours,
                "description": course.description
            })
            
    return recommendations
