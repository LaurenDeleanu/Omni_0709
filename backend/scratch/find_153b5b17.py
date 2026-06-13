import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy import text

async def check():
    schema = "tenant_acme_corp"
    te = engine.execution_options(schema_translate_map={None: schema})
    async with te.connect() as conn:
        # Search sales_clients
        try:
            r = await conn.execute(text("SELECT * FROM sales_clients WHERE id LIKE '153b5b17%'"))
            rows = r.fetchall()
            if rows:
                cols = r.keys()
                print("Found in sales_clients:")
                for row in rows:
                    print(dict(zip(cols, row)))
            else:
                print("Not found in sales_clients")
        except Exception as e:
            print(f"Error sales_clients: {e}")

        # Search sales_leads
        try:
            r = await conn.execute(text("SELECT * FROM sales_leads WHERE id LIKE '153b5b17%'"))
            rows = r.fetchall()
            if rows:
                cols = r.keys()
                print("\nFound in sales_leads:")
                for row in rows:
                    print(dict(zip(cols, row)))
            else:
                print("\nNot found in sales_leads")
        except Exception as e:
            print(f"Error sales_leads: {e}")

        # Search all tables with an id column
        try:
            r = await conn.execute(text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = 'tenant_acme_corp' AND column_name = 'id'"
            ))
            tables_with_id = [t[0] for t in r.fetchall()]
            print(f"\nTables with id col: {len(tables_with_id)}")
        except Exception as e:
            print(f"Info schema error: {e}")

asyncio.run(check())
