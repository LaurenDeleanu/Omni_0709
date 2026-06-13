import asyncio
import os
import sys
from dotenv import dotenv_values
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def upgrade_schema():
    env = dotenv_values("backend/.env")
    dsn = env.get("DATABASE_URL")
    if not dsn:
        print("No DATABASE_URL in .env")
        return
        
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    elif dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    if "?" in dsn:
        dsn = dsn.split("?")[0]
        
    print(f"Connecting to DB...")
    engine = create_async_engine(dsn, echo=True)
    
    async with engine.begin() as conn:
        print("Adding columns to users table...")
        
        try:
            await conn.execute(text("ALTER TABLE tenant_acme_corp.users ADD COLUMN base_salary FLOAT DEFAULT 50000.0;"))
            print("Added base_salary")
        except Exception as e:
            print(f"Column base_salary may already exist: {e}")
            
        try:
            await conn.execute(text("ALTER TABLE tenant_acme_corp.users ADD COLUMN country VARCHAR(50) DEFAULT 'ES';"))
            print("Added country")
        except Exception as e:
            print(f"Column country may already exist: {e}")
            
        print("Done upgrading tenant_acme_corp schema.")

if __name__ == "__main__":
    asyncio.run(upgrade_schema())
