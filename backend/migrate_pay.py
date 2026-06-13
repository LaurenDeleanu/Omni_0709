import asyncio
from dotenv import load_dotenv
load_dotenv("backend/.env")
from app.core.database import engine
from app.models.base import Base
# We import all models so SQLAlchemy knows about them before creating tables
from app.models.pay import PayrollCycle, Payslip, Bonus

async def main():
    async with engine.begin() as conn:
        print("Creando tablas del modulo Pay (Payroll & Benefits) en PostgreSQL...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tablas creadas con exito.")

if __name__ == "__main__":
    asyncio.run(main())
