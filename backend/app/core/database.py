from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.core.config import settings
import asyncio
import logging
import os

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


# ── Read Replica Support ──────────────────────────────────────────────────────
# Separate read (ro) from write (rw) paths for analytics and heavy queries.
# Falls back to primary if READ_REPLICA_URL is not configured.

_read_replica_engine = None
_read_replica_sessionmaker = None


def _get_read_replica_engine():
    global _read_replica_engine
    if _read_replica_engine is not None:
        return _read_replica_engine

    replica_url = os.getenv("READ_REPLICA_URL", "")
    if not replica_url:
        logger.info("No READ_REPLICA_URL configured — analytics will use primary DB")
        _read_replica_engine = engine  # fall back to primary
        return _read_replica_engine

    rp_kwargs = engine_kwargs.copy()
    rp_kwargs["pool_size"] = 5
    rp_kwargs["max_overflow"] = 10
    _read_replica_engine = create_async_engine(replica_url, **rp_kwargs)
    logger.info("Read replica engine initialized")
    return _read_replica_engine


def get_read_sessionmaker() -> async_sessionmaker:
    global _read_replica_sessionmaker
    if _read_replica_sessionmaker is None:
        rp_engine = _get_read_replica_engine()
        _read_replica_sessionmaker = async_sessionmaker(
            bind=rp_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _read_replica_sessionmaker


async def get_read_db():
    """Dependency — yields a read-only session from the replica (or primary fallback)."""
    maker = get_read_sessionmaker()
    async with maker() as session:
        try:
            yield session
        finally:
            await session.close()

