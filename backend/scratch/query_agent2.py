import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import text

async def check():
    schema = "tenant_acme_corp"
    tenant_engine = engine.execution_options(schema_translate_map={None: schema})
    async with tenant_engine.connect() as conn:
        # Try with quotes and exact case
        for query in ["SELECT * FROM agents LIMIT 1", 'SELECT * FROM "agents" LIMIT 1', 'SELECT * FROM "Agents" LIMIT 1']:
            try:
                r = await conn.execute(text(query))
                rows = r.fetchall()
                cols = r.keys()
                print(f"Query '{query}' OK: {len(rows)} rows, cols={cols}")
            except Exception as e:
                print(f"Query '{query}' FAILED: {type(e).__name__}: {str(e)[:100]}")
        
        # List exact table names including quotes
        names = await conn.execute(text(
            f"SELECT schemaname, tablename, quote_ident(tablename) FROM pg_tables WHERE schemaname = 'tenant_acme_corp' AND tablename ILIKE '%agent%'"
        ))
        for row in names.fetchall():
            print(f"  {row[0]}.{row[1]} (quoted: {row[2]})")

asyncio.run(check())
