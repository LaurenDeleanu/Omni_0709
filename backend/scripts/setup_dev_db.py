import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import engine, AsyncSessionGlobal
from app.models.base import Base, GlobalBase
from app.models.user import User
import app.models
from datetime import datetime, timezone
from app.core.config import settings

async def setup_db():
    is_sqlite = "sqlite" in settings.SQLALCHEMY_DATABASE_URI

    print(f"Setting up database ({'SQLite' if is_sqlite else 'PostgreSQL'} mode)...")

    async with engine.begin() as conn:
        await conn.run_sync(GlobalBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created via metadata.create_all.")

    async with AsyncSessionGlobal() as session:
        print("Seeding mock employees...")
        now = datetime.now(timezone.utc)
        from app.core.auth import hash_password
        new_users = [
            User(id="u1", email="lauren.deleanu@gmail.com", role="hr_admin", full_name="Admin User",
                 hashed_password=hash_password("admin"), created_at=now, updated_at=now, department="Direccion"),
            User(id="u2", email="john.doe@acme.com", role="employee", full_name="John Doe",
                 created_at=now, updated_at=now, department="Ventas"),
            User(id="u3", email="jane.smith@acme.com", role="employee", full_name="Jane Smith",
                 created_at=now, updated_at=now, department="Tecnologia"),
        ]
        session.add_all(new_users)
        await session.commit()
        print("Data seeded successfully.")
        print(f"Login: lauren.deleanu@gmail.com / admin")

if __name__ == "__main__":
    asyncio.run(setup_db())
