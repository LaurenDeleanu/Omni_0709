"""Script de diagnóstico: lista schemas y tablas de la BD."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def main():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, future=True)
    async with engine.begin() as conn:
        # All schemas
        r = await conn.execute(text(
            "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
        ))
        schemas = [row[0] for row in r.fetchall()]
        print("SCHEMAS en la BD:", schemas)

        # For each non-system schema show tables
        skip = {'pg_catalog', 'information_schema', 'pg_toast'}
        for schema in schemas:
            if schema in skip or schema.startswith('pg_'):
                continue
            r2 = await conn.execute(text(
                f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema}' ORDER BY table_name"
            ))
            tables = [t[0] for t in r2.fetchall()]
            print(f"  [{schema}] tablas: {tables}")

            # Count rows in users table if it exists
            if 'users' in tables:
                r3 = await conn.execute(text(f'SELECT COUNT(*) FROM "{schema}".users'))
                count = r3.scalar()
                print(f"    -> users count: {count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
