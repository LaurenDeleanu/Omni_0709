import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy import text

async def fix():
    schema = "tenant_acme_corp"
    te = engine.execution_options(schema_translate_map={None: schema})
    async with te.connect() as conn:
        rows = await conn.execute(text("SELECT id, company_name, created_at FROM sales_clients"))
        for r in rows.fetchall():
            print(f"{r[0]} | {r[1]} | created_at={r[2]}")
        
        # Fix missing created_at
        await conn.execute(text("UPDATE sales_clients SET created_at = NOW() WHERE created_at IS NULL"))
        await conn.commit()
        print("\nFixed NULL created_at values")
        
        rows2 = await conn.execute(text("SELECT COUNT(*) FROM sales_clients"))
        print(f"Total clients: {rows2.fetchone()[0]}")

asyncio.run(fix())
