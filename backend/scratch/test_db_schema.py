import asyncio
from app.core.database import engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def test():
    tenant_schema = "tenant_acme_corp"
    tenant_engine = engine.execution_options(schema_translate_map={None: tenant_schema})
    session_maker = async_sessionmaker(
        bind=tenant_engine,
        class_=AsyncSession
    )
    async with session_maker() as db:
        bind = db.get_bind()
        print("bind type:", type(bind))
        # Let's see if we have _execution_options attribute
        if hasattr(bind, "_execution_options"):
            print("_execution_options:", bind._execution_options)
        else:
            print("No _execution_options attribute")
        
        # Let's inspect dispatch or other potential locations
        print("has attr execution_options:", hasattr(bind, "execution_options"))

if __name__ == "__main__":
    asyncio.run(test())
