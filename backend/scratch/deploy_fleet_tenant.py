import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.services.agent_fleet import deploy_agent_fleet

async def deploy():
    schema = "tenant_acme_corp"
    tenant_engine = engine.execution_options(schema_translate_map={None: schema})
    AsyncSessionTenant = async_sessionmaker(bind=tenant_engine, class_=AsyncSession, autocommit=False, autoflush=False)
    async with AsyncSessionTenant() as db:
        result = await deploy_agent_fleet(db)
        print(f"Created: {len(result['created'])} | Updated: {len(result['updated'])}")
        for a in result["created"] + result["updated"]:
            print(f"  - {a}")

asyncio.run(deploy())
