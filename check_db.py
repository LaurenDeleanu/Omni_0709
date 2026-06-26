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
        print("Checking tables in tenant_acme_corp...")
        result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'tenant_acme_corp'"))
        tables = result.fetchall()
        print(f"Tables in tenant_acme_corp: {[t[0] for t in tables]}")
        
        print("\nChecking tables in public...")
        result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        pub_tables = result.fetchall()
        print(f"Tables in public: {[t[0] for t in pub_tables]}")

if __name__ == '__main__':
    asyncio.run(check_db())
