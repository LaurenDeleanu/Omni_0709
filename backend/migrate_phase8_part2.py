import asyncio
import os
import sys
from dotenv import load_dotenv

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.core.database import engine
from app.models.base import Base
# Importar todos los modelos necesarios para que SQLAlchemy los reconozca
from app.models.finance import GeneralShift

async def main():
    dialect = engine.dialect.name
    print(f"Dialecto detectado: {dialect}")
    
    # Crear tablas en SQLite/PostgreSQL
    if dialect == "postgresql":
        tenant_engine = engine.execution_options(schema_translate_map={None: "tenant_acme_corp"})
        async with tenant_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tablas creadas en el esquema PostgreSQL (tenant_acme_corp)")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tablas creadas con éxito en SQLite")

if __name__ == "__main__":
    asyncio.run(main())
