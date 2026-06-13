import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy import text

async def fix():
    async with engine.connect() as conn:
        await conn.execute(text("INSERT INTO tenant_acme_corp.sales_clients (id, company_name, primary_contact_name, primary_contact_email, primary_contact_phone, created_at) SELECT id, company_name, primary_contact_name, primary_contact_email, primary_contact_phone, created_at FROM public.sales_clients WHERE id = '153b5b1749d54b169681'"))
        await conn.commit()
        print("Copied sacorp to tenant schema")
        
        r = await conn.execute(text("SELECT id, company_name, primary_contact_name FROM tenant_acme_corp.sales_clients ORDER BY created_at"))
        print("Tenant clients:")
        for row in r.fetchall():
            print(f"  id={row[0]} company={row[1]} contact={row[2]}")

asyncio.run(fix())
