import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))

from backend.app.core.database import engine

async def check():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("SET search_path TO tenant_acme_corp"))
            res = await conn.execute(text("SELECT count(*) FROM notifications"))
            print("NOTIFICATIONS COUNT:", res.scalar())
        except Exception as e:
            print("ERROR NOTIFICATIONS:", e)

        try:
            res = await conn.execute(text("SELECT manager_id, vacation_allowance FROM users LIMIT 1"))
            print("USERS EXTENDED:", res.fetchone())
        except Exception as e:
            print("ERROR USERS:", e)

asyncio.run(check())
