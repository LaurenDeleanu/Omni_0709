import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.core.database import engine
from app.models.base import Base, GlobalBase
import app.models

async def main():
    dialect = engine.dialect.name
    print(f"Dialecto: {dialect}")
    
    if dialect == "postgresql":
        # Create global tables in public schema
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(GlobalBase.metadata.create_all)
            print("Tablas globales creadas en esquema público (public)")
            
        # Create tenant-specific tables in the tenant schema
        tenant_engine = engine.execution_options(schema_translate_map={None: "tenant_acme_corp"})
        async with tenant_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tablas de inquilino creadas/actualizadas en tenant_acme_corp")
    else:
        # SQLite
        async with engine.begin() as conn:
            await conn.run_sync(GlobalBase.metadata.create_all)
            await conn.run_sync(Base.metadata.create_all)
            print("Todas las tablas creadas/actualizadas en SQLite")

if __name__ == "__main__":
    asyncio.run(main())
