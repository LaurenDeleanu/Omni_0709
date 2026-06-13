import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def main():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        # Check tables in tenant_acme_corp
        res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'tenant_acme_corp'"
        ))
        tables = [row[0] for row in res.fetchall()]
        print(f"Tables in tenant_acme_corp: {tables}")
        
        # Check columns of agent_execution_runs in tenant_acme_corp
        res = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'tenant_acme_corp' AND table_name = 'agent_execution_runs'"
        ))
        cols = [row[0] for row in res.fetchall()]
        print(f"Columns in tenant_acme_corp.agent_execution_runs: {cols}")

if __name__ == "__main__":
    asyncio.run(main())
