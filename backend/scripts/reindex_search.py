#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text, delete

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reindex_search")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.models.user import User
from app.models.agent import Agent
from app.models.work import Project
from app.models.training import Course
from app.models.hire import JobPosting
from app.models.search_index import SearchIndexEntry
from app.services.search_indexer import index_entity

async def reindex_schema(db: AsyncSession, schema_name: str):
    logger.info("Reindexing search index for schema %s...", schema_name)
    
    # 1. Clear existing search index entries
    await db.execute(delete(SearchIndexEntry))
    await db.flush()
    
    # 2. Reindex Users (Employees)
    res = await db.execute(select(User))
    users = res.scalars().all()
    logger.info("Indexing %d users...", len(users))
    for u in users:
        content = f"Employee name: {u.full_name or ''}\nEmail: {u.email or ''}\nDepartment: {u.department or ''}\nRole: {u.role or ''}"
        await index_entity(
            db=db,
            entity_id=u.id,
            entity_type="employee",
            title=u.full_name or u.email or "Unnamed Employee",
            subtitle=u.department or u.role or "Staff",
            content=content,
            route=f"/dashboard/employees/{u.id}"
        )
        
    # 3. Reindex Agents
    res = await db.execute(select(Agent))
    agents = res.scalars().all()
    logger.info("Indexing %d agents...", len(agents))
    for a in agents:
        content = f"AI Agent: {a.name}\nType: {a.agent_type}\nModel: {a.ai_model or ''}\nPrompt: {a.ai_system_prompt or ''}"
        await index_entity(
            db=db,
            entity_id=a.id,
            entity_type="agent",
            title=a.name,
            subtitle=a.agent_type or "AI Assistant",
            content=content,
            route=f"/dashboard/agent-studio/{a.id}"
        )
        
    # 4. Reindex Projects
    res = await db.execute(select(Project))
    projects = res.scalars().all()
    logger.info("Indexing %d projects...", len(projects))
    for p in projects:
        content = f"Project: {p.name}\nDescription: {p.description or ''}\nStatus: {p.status or ''}"
        await index_entity(
            db=db,
            entity_id=p.id,
            entity_type="project",
            title=p.name,
            subtitle=p.status or "Planning",
            content=content,
            route=f"/dashboard/work/projects/{p.id}"
        )
        
    # 5. Reindex Courses
    res = await db.execute(select(Course))
    courses = res.scalars().all()
    logger.info("Indexing %d courses...", len(courses))
    for c in courses:
        content = f"Training Course: {c.title}\nDescription: {c.description or ''}\nCategory: {c.category or ''}"
        await index_entity(
            db=db,
            entity_id=c.id,
            entity_type="course",
            title=c.title,
            subtitle=c.category or "Training",
            content=content,
            route=f"/dashboard/training/courses/{c.id}"
        )
        
    # 6. Reindex JobPostings
    res = await db.execute(select(JobPosting))
    jobs = res.scalars().all()
    logger.info("Indexing %d job postings...", len(jobs))
    for j in jobs:
        content = f"Job Posting: {j.title}\nDescription: {j.description or ''}\nDepartment: {j.department or ''}\nStatus: {j.status or ''}"
        await index_entity(
            db=db,
            entity_id=j.id,
            entity_type="job",
            title=j.title,
            subtitle=j.department or "Recruitment",
            content=content,
            route=f"/dashboard/hire/{j.id}"
        )
        
    await db.commit()
    logger.info("Reindexing complete for schema %s", schema_name)

async def main():
    load_dotenv()
    
    dsn = settings.SQLALCHEMY_DATABASE_URI
    if "postgresql" in dsn and "asyncpg" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://")
        
    engine = create_async_engine(dsn, echo=False)
    is_sqlite = "sqlite" in dsn
    
    async with AsyncSession(engine) as db:
        if is_sqlite:
            # SQLite: just reindex the single default database
            await reindex_schema(db, "sqlite_default")
        else:
            # PostgreSQL: fetch all active tenants
            logger.info("Fetching tenants from public schema...")
            res = await db.execute(text("SELECT id, is_active FROM public.tenants"))
            tenants = res.fetchall()
            
            for tenant_id, is_active in tenants:
                if is_active:
                    schema_name = f"tenant_{tenant_id}"
                    logger.info("Switching connection context to schema: %s", schema_name)
                    await db.execute(text(f"SET search_path TO {schema_name}"))
                    try:
                        await reindex_schema(db, schema_name)
                    except Exception as e:
                        logger.error("Failed to reindex schema %s: %s", schema_name, e, exc_info=True)
                        await db.rollback()
                        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
