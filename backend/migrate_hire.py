import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.models.hire import JobPosting, Candidate, Interview, CandidatePool, CandidatePoolEntry

async def create_hire_tables():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    engine = create_async_engine(dsn, echo=True)
    async with engine.begin() as conn:
        print("Creating hire tables...")
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.hire_jobs (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR(150) NOT NULL,
            department VARCHAR(100),
            location VARCHAR(100),
            employment_type VARCHAR(50),
            description TEXT,
            status VARCHAR(50) DEFAULT 'open',
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE
        );
        """))

        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.hire_candidates (
            id VARCHAR(36) PRIMARY KEY,
            job_id VARCHAR(36) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            resume_url VARCHAR(500),
            linkedin_url VARCHAR(255),
            portfolio_url VARCHAR(255),
            stage VARCHAR(50) DEFAULT 'applied',
            source VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY(job_id) REFERENCES tenant_acme_corp.hire_jobs(id) ON DELETE CASCADE
        );
        """))

        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.hire_interviews (
            id VARCHAR(36) PRIMARY KEY,
            candidate_id VARCHAR(36) NOT NULL,
            interviewer_id VARCHAR(36),
            scheduled_at TIMESTAMP WITH TIME ZONE,
            duration_minutes INTEGER DEFAULT 60,
            interview_type VARCHAR(50),
            feedback_notes TEXT,
            score FLOAT,
            created_at TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY(candidate_id) REFERENCES tenant_acme_corp.hire_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY(interviewer_id) REFERENCES tenant_acme_corp.users(id)
        );
        """))
        print("Done creating hire tables.")
        
        print("Creating talent CRM tables & fields...")
        await conn.execute(text("""
        ALTER TABLE tenant_acme_corp.hire_candidates 
        ADD COLUMN IF NOT EXISTS tags TEXT;
        """))
        await conn.execute(text("""
        ALTER TABLE tenant_acme_corp.hire_candidates 
        ADD COLUMN IF NOT EXISTS last_contacted_at TIMESTAMP WITH TIME ZONE;
        """))
        await conn.execute(text("""
        ALTER TABLE tenant_acme_corp.hire_candidates 
        ADD COLUMN IF NOT EXISTS engagement_score DOUBLE PRECISION DEFAULT 0.0;
        """))
        await conn.execute(text("""
        ALTER TABLE tenant_acme_corp.hire_candidates 
        ADD COLUMN IF NOT EXISTS source_detail VARCHAR(200);
        """))
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.hire_candidate_pools (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            created_by_id VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """))
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.hire_candidate_pool_entries (
            id VARCHAR(36) PRIMARY KEY,
            pool_id VARCHAR(36) NOT NULL,
            candidate_id VARCHAR(36) NOT NULL,
            notes TEXT,
            engagement_score DOUBLE PRECISION DEFAULT 0.0,
            added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(pool_id) REFERENCES tenant_acme_corp.hire_candidate_pools(id) ON DELETE CASCADE,
            FOREIGN KEY(candidate_id) REFERENCES tenant_acme_corp.hire_candidates(id) ON DELETE CASCADE,
            UNIQUE(pool_id, candidate_id)
        );
        """))
        print("Done creating talent CRM tables.")

if __name__ == "__main__":
    asyncio.run(create_hire_tables())
