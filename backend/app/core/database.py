from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger("successcore.database")

connect_args = {}
if "sqlite" in settings.SQLALCHEMY_DATABASE_URI:
    connect_args = {"check_same_thread": False}
elif "neon.tech" in settings.SQLALCHEMY_DATABASE_URI or "supabase" in settings.SQLALCHEMY_DATABASE_URI:
    connect_args = {"ssl": "require"}

if "sqlite" not in settings.SQLALCHEMY_DATABASE_URI:
    connect_args["server_settings"] = {"application_name": "successcore"}

engine_kwargs = {
    "echo": False,
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if "sqlite" not in settings.SQLALCHEMY_DATABASE_URI:
    engine_kwargs.update({
        "pool_size": 15,
        "max_overflow": 25,
        "pool_timeout": 60,
        "pool_recycle": 120,
    })
else:
    engine_kwargs["pool_recycle"] = 1800

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    **engine_kwargs
)

AsyncSessionGlobal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


async def wait_for_db(max_retries: int = 10, delay: float = 2.0) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info(f"Database connection established (attempt {attempt})")
            return True
        except Exception as e:
            logger.warning(f"Database not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)
    logger.error("Database connection failed after max retries")
    return False

# Mapping of region to engine
_regional_engines = {}

def get_engine_for_region(region: str):
    """
    Returns the regional engine if configured, otherwise returns the default engine.
    Region config format via env var: DB_REGION_EU="postgresql+asyncpg://..."
    """
    if not region or region == "default":
        return engine
        
    if region in _regional_engines:
        return _regional_engines[region]
        
    import os
    region_uri = os.getenv(f"DB_REGION_{region.upper()}")
    if not region_uri:
        logger.warning(f"No DB URI configured for region {region}. Falling back to default.")
        _regional_engines[region] = engine
        return engine
        
    reg_kwargs = engine_kwargs.copy()
    if "sqlite" in region_uri:
        if "server_settings" in reg_kwargs.get("connect_args", {}):
            reg_kwargs["connect_args"].pop("server_settings", None)
            
    region_engine = create_async_engine(region_uri, **reg_kwargs)
    _regional_engines[region] = region_engine
    logger.info(f"Initialized new DB engine for region: {region}")
    return region_engine

