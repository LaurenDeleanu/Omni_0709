import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import select

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.core.database import engine, AsyncSessionGlobal
from app.models.base import Base
# Importar todos los modelos necesarios
from app.models.user import User
from app.models.finance import TimeLog, BreakLog, WorkSchedule

async def main():
    dialect = engine.dialect.name
    print(f"Dialecto detectado: {dialect}")
    
    # 1. Crear tablas en SQLite/PostgreSQL
    if dialect == "postgresql":
        tenant_engine = engine.execution_options(schema_translate_map={None: "tenant_acme_corp"})
        async with tenant_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tablas creadas en el esquema PostgreSQL (tenant_acme_corp)")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tablas creadas con éxito en SQLite")

    # 2. Conectar al tenant_db (utilizando el translation map de esquemas para PostgreSQL)
    if dialect == "postgresql":
        tenant_engine = engine.execution_options(schema_translate_map={None: "tenant_acme_corp"})
    else:
        tenant_engine = engine

    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    AsyncSessionTenant = async_sessionmaker(
        bind=tenant_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )

    async with AsyncSessionTenant() as db:
        try:
            # Obtener todos los usuarios
            users_res = await db.execute(select(User))
            users = users_res.scalars().all()
            print(f"Encontrados {len(users)} usuarios en el sistema.")
            
            # Obtener en bloque todos los user_id que ya tienen algún horario
            existing_scheds_res = await db.execute(select(WorkSchedule.user_id))
            users_with_schedules = set(existing_scheds_res.scalars().all())
            
            # Para cada usuario, crear horario por defecto de Lunes a Viernes (0 a 4) de 09:00 a 18:00 si no existe
            seeded_count = 0
            for u in users:
                if u.id not in users_with_schedules:
                    # Crear horario Lunes a Viernes
                    for day in range(5): # 0 = Lunes, 4 = Viernes
                        new_sched = WorkSchedule(
                            user_id=u.id,
                            day_of_week=day,
                            start_time="09:00",
                            end_time="18:00",
                            flexible=False
                        )
                        db.add(new_sched)
                    seeded_count += 1
            
            if seeded_count > 0:
                await db.commit()
                print(f"Se han asignado horarios de Lunes a Viernes (09:00 - 18:00) a {seeded_count} empleados.")
            else:
                print("Todos los empleados ya tienen un horario configurado.")
                
        except Exception as e:
            print(f"Error seeding schedules: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(main())
