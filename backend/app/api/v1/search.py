from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles
from app.models.user import User
from app.models.agent import Agent
from app.models.work import Project
from app.models.training import Course
from app.models.hire import JobPosting

router = APIRouter()


class SearchResult(BaseModel):
    id: str
    type: str
    title: str
    subtitle: str
    route: str

class SearchFacets(BaseModel):
    types: dict[str, int]
    departments: dict[str, int]

class SearchResponse(BaseModel):
    results: list[SearchResult]
    facets: SearchFacets

@router.get("", response_model=SearchResponse)
async def smart_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, le=20),
    use_semantic: bool = Query(False, description="Enable AI semantic search"),
    filter_type: Optional[str] = Query(None, description="Filter by result type"),
    filter_department: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
):
    query = f"%{q}%"
    results: list[SearchResult] = []
    
    facets = {"types": {}, "departments": {}}

    def _add_result(res: SearchResult, dept: Optional[str] = None):
        t = res.type
        d = dept or "Unknown"
        facets["types"][t] = facets["types"].get(t, 0) + 1
        facets["departments"][d] = facets["departments"].get(d, 0) + 1
        
        # Apply filters
        if filter_type and t != filter_type:
            return
        if filter_department and d != filter_department:
            return
            
        results.append(res)

    if use_semantic:
        from app.services.semantic_search import perform_semantic_search
        semantic_results = await perform_semantic_search(q, db, limit * 2)
        for r in semantic_results:
            _add_result(
                SearchResult(
                    id=r["id"],
                    type=r["type"],
                    title=r["title"],
                    subtitle=r["subtitle"],
                    route=r["route"]
                ),
                r.get("department") # Assume semantic search might return department in the future
            )
        return {"results": results[:limit], "facets": facets}

    # Fetch more than limit to build accurate facets
    users_res = await db.execute(
        select(User).where(or_(User.full_name.ilike(query), User.email.ilike(query), User.department.ilike(query))).limit(50)
    )
    for u in users_res.scalars().all():
        _add_result(SearchResult(id=u.id, type="employee", title=u.full_name or u.email, subtitle=u.department or "", route=f"/dashboard/employees/{u.id}"), u.department)

    agents_res = await db.execute(
        select(Agent).where(Agent.name.ilike(query)).limit(50)
    )
    for a in agents_res.scalars().all():
        _add_result(SearchResult(id=a.id, type="agent", title=a.name, subtitle=a.agent_type or "AI Agent", route=f"/dashboard/agent-studio"), "AI")

    projects_res = await db.execute(
        select(Project).where(Project.name.ilike(query)).limit(50)
    )
    for p in projects_res.scalars().all():
        _add_result(SearchResult(id=p.id, type="project", title=p.name, subtitle=p.status or "", route=f"/dashboard/work/{p.id}"), "Work")

    courses_res = await db.execute(
        select(Course).where(Course.title.ilike(query)).limit(50)
    )
    for c in courses_res.scalars().all():
        _add_result(SearchResult(id=c.id, type="course", title=c.title, subtitle="Training", route=f"/dashboard/training"), "Training")

    jobs_res = await db.execute(
        select(JobPosting).where(JobPosting.title.ilike(query)).limit(50)
    )
    for j in jobs_res.scalars().all():
        _add_result(SearchResult(id=j.id, type="job", title=j.title, subtitle=j.department or "", route=f"/dashboard/hire/{j.id}"), j.department)

    return {"results": results[:limit], "facets": facets}

