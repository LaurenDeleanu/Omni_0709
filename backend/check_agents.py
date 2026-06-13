import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

async def main():
    dsn = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT id, name FROM agents'))
        print(res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
