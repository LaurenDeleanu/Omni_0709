import asyncio
import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.database import engine

async def run_migration():
    print("Running DDL migration to add 'enabled_modules' to 'tenants' table...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS enabled_modules JSON;"))
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration error (could be SQLite or permissions): {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_migration())
