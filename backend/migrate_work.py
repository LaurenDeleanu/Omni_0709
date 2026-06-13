import asyncio
from app.core.database import engine
from app.models.base import Base
# We import all models so SQLAlchemy knows about them before creating tables
from app.models.work import Project, Task

async def main():
    async with engine.begin() as conn:
        print("Creando tablas del modulo Project & Task Management en PostgreSQL...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tablas creadas con exito.")

if __name__ == "__main__":
    asyncio.run(main())
