from logging.config import fileConfig

from sqlalchemy import pool, MetaData
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

import sys
import os
import asyncio

# Add app to python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.models.base import GlobalBase, Base
# Import ALL models to ensure they are registered with SQLAlchemy metadata
import app.models.tenant
import app.models.user
import app.models.scheduled_report
import app.models.employee_history
import app.models.calendar
import app.models.metadata
import app.models.it
import app.models.finance
import app.models.training
import app.models.admin
import app.models.rbac
import app.models.sales
import app.models.work
import app.models.ops
import app.models.intelligence
import app.models.hire
import app.models.pay
import app.models.legal
import app.models.grow
import app.models.notification
import app.models.announcement
import app.models.kudos
import app.models.workflow


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Dynamically set DB URL from config
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata
# We combine metadata for autogenerate to see both global and tenant-base tables
def get_metadata():
    metadata = MetaData()
    for m in [GlobalBase.metadata, Base.metadata]:
        for table in m.tables.values():
            table.tometadata(metadata)
    return metadata

target_metadata = get_metadata()

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


from sqlalchemy import text

def do_run_migrations(connection: Connection) -> None:
    schema = config.attributes.get("tenant_schema")
    x_args = context.get_x_argument(as_dictionary=True)
    if 'schema' in x_args:
        schema = x_args['schema']

    if schema:
        connection.execute(text(f"SET search_path TO {schema}"))

    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        include_schemas=True, # Important to see 'public' and others
        version_table_schema=schema if schema else None,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
