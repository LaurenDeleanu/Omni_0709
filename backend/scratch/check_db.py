import asyncio, sys; sys.path.insert(0, '.')
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        tables = (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).all()
        print('Tables:', [t[0] for t in tables])
        users = (await conn.execute(text("SELECT email, hashed_password FROM users"))).all()
        print('Raw users:', users)
asyncio.run(check())
