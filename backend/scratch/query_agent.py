import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import text

async def check():
    # Check public schema
    async with engine.connect() as conn:
        tables = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
        pub_tables = [t[0] for t in tables.fetchall()]
        print(f"Tables in public: {len(pub_tables)}")
        for t in pub_tables:
            print(f"  {t}")
        
        if "agents" in pub_tables:
            agents = await conn.execute(text("SELECT id, name, agent_type, ai_model, agent_settings FROM agents"))
            for a in agents.fetchall():
                print(f"\nAgent: id={a[0]}")
                print(f"  name={a[1]}, type={a[2]}, model={a[3]}")
                print(f"  settings={a[4]}")
            
            target = await conn.execute(text("SELECT id, name, agent_type, ai_model, agent_settings FROM agents WHERE id LIKE '153b5b17%'"))
            rows = target.fetchall()
            if rows:
                row = rows[0]
                print(f"\n=== TARGET AGENT ===")
                print(f"ID: {row[0]}")
                print(f"Name: {row[1]}")
                print(f"Type: {row[2]}")
                print(f"Model: {row[3]}")
                print(f"Settings: {row[4]}")
            else:
                print("\nAgent 153b5b17* NOT in public schema either")
        else:
            print("\nNo 'agents' table in public schema!")

        # Also check all schemas
        schemas = await conn.execute(text("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'"))
        print(f"\nSchemas: {[s[0] for s in schemas.fetchall()]}")

asyncio.run(check())
