import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

# Add current folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.core.database import engine
from app.models.base import Base

# Import all new models
import app.models.notification
import app.models.announcement
import app.models.kudos
import app.models.workflow

async def main():
    async with engine.begin() as conn:
        dialect = engine.dialect.name
        print(f"Dialecto de la base de datos detectado: {dialect}")
        
        if dialect == "postgresql":
            print("Estableciendo search_path a 'tenant_acme_corp' para multi-tenancy...")
            await conn.execute(text("SET search_path TO tenant_acme_corp"))
            
        print("Añadiendo nuevas columnas a la tabla users si no existen...")
        # Intentar añadir columnas
        for query in [
            "ALTER TABLE users ADD COLUMN manager_id VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN vacation_allowance INTEGER DEFAULT 30"
        ]:
            try:
                await conn.execute(text(query))
                print(f"Ejecutado con éxito: {query}")
            except Exception as e:
                print(f"Ignorado o ya existente: {e}")
                
        print("Creando nuevas tablas de la Fase 2 en el esquema correspondiente...")
        
        if dialect == "postgresql":
            # Usar schema_translate_map en la misma conexión
            t_conn = await conn.execution_options(schema_translate_map={None: "tenant_acme_corp"})
            await t_conn.run_sync(Base.metadata.create_all)
        else:
            await conn.run_sync(Base.metadata.create_all)
            
        print("Migración de base de datos de la Fase 2 completada con éxito.")

if __name__ == "__main__":
    asyncio.run(main())
