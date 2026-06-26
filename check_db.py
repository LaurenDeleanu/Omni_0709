import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check_db():
    database_url = "postgresql+asyncpg://neondb_owner:npg_u3vzJ2CrBMsk@ep-weathered-voice-alocerh4-pooler.c-3.eu-central-1.aws.neon.tech/neondb?ssl=require"
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("Checking failed agent run trace...")
        result = await session.execute(text("SELECT execution_trace, output_result FROM agent_execution_runs WHERE id = '5acc0c9f59bc448088f53059f90f462b'"))
        row = result.fetchone()
        if row:
            print(f"Failed Run Trace: {row[0]}")
            print(f"Output Result: {row[1]}")
            
        print("\nChecking audit_logs for errors...")
        result = await session.execute(text("SELECT id, action, details, created_at FROM audit_logs WHERE details::text ILIKE '%error%' OR details::text ILIKE '%failed%' ORDER BY created_at DESC LIMIT 5"))
        audit_rows = result.fetchall()
        for r in audit_rows:
            print(f"Audit Error: {r.action} - {r.details}")
        
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(check_db())
