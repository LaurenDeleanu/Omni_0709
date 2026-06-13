import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def update_admin():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    engine = create_async_engine(dsn, echo=True)
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE tenant_acme_corp.users SET is_super_admin = TRUE WHERE id = 'admin'"))
        print("Updated admin user")

if __name__ == "__main__":
    asyncio.run(update_admin())
