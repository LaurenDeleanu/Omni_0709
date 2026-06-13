import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.schema import CreateColumn
from app.core.config import settings
from app.models.base import Base, GlobalBase
import app.models
import app.models.push
import app.models.integration

async def main():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to: {dsn}")
    
    engine = create_async_engine(dsn, echo=False)
    dialect = engine.dialect
    is_postgres = "postgresql" in dsn
    
    async def run_alter_query(alter_query):
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text(alter_query))

    async with engine.connect() as conn:
        async def check_and_add_columns(schema_name, metadata):
            for table_name, table in metadata.tables.items():
                full_table_name = f"{schema_name}.{table.name}" if schema_name else table.name
                
                # Check if table exists in DB first
                try:
                    if is_postgres:
                        res = await conn.execute(text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = :schema AND table_name = :table)"
                        ), {"schema": schema_name or "public", "table": table.name})
                        exists = res.scalar()
                    else:
                        res = await conn.execute(text(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=:table"
                        ), {"table": table.name})
                        exists = res.scalar() is not None
                except Exception as e:
                    print(f"Error checking table existence for {full_table_name}: {e}")
                    continue
                
                if not exists:
                    continue
                
                # Get existing columns in DB
                try:
                    if is_postgres:
                        res = await conn.execute(text(
                            "SELECT column_name FROM information_schema.columns WHERE table_schema = :schema AND table_name = :table"
                        ), {"schema": schema_name or "public", "table": table.name})
                        existing_cols = {row[0] for row in res.fetchall()}
                    else:
                        res = await conn.execute(text(f"PRAGMA table_info({table.name})"))
                        existing_cols = {row[1] for row in res.fetchall()}
                except Exception as e:
                    print(f"Error reading columns for {full_table_name}: {e}")
                    continue
                
                # For each column in model, check if it exists in DB
                for column in table.columns:
                    if column.name not in existing_cols:
                        print(f"Column {column.name} is missing in DB table {full_table_name}!")
                        # Compile DDL for the column
                        compiled_col = CreateColumn(column).compile(dialect=dialect)
                        col_def = str(compiled_col)
                        
                        # In ALTER TABLE, we don't want UNIQUE or PRIMARY KEY constraints
                        col_def_clean = col_def.replace("PRIMARY KEY", "").replace("UNIQUE", "")
                        
                        # Handle NOT NULL default values for columns added to existing tables
                        if not column.nullable and "DEFAULT" not in col_def_clean.upper():
                            type_str = col_def_clean.upper()
                            if "JSON" in type_str:
                                col_def_clean += " DEFAULT '{}'"
                            elif "VARCHAR" in type_str or "TEXT" in type_str:
                                col_def_clean += " DEFAULT ''"
                            elif "INT" in type_str or "NUMERIC" in type_str or "FLOAT" in type_str or "DOUBLE" in type_str or "REAL" in type_str:
                                col_def_clean += " DEFAULT 0"
                            elif "BOOL" in type_str:
                                col_def_clean += " DEFAULT FALSE"
                            elif "TIMESTAMP" in type_str or "DATE" in type_str:
                                col_def_clean += " DEFAULT CURRENT_TIMESTAMP"
                        
                        alter_query = f"ALTER TABLE {full_table_name} ADD COLUMN {col_def_clean};"
                        print(f"Executing: {alter_query}")
                        
                        try:
                            await run_alter_query(alter_query)
                            print(f"Successfully added column {column.name} to {full_table_name}")
                        except Exception as e:
                            print(f"Error executing alter for {column.name} on {full_table_name}: {e}")

        # Run check for public schema
        print("Checking public schema tables...")
        await check_and_add_columns("public", GlobalBase.metadata)
        await check_and_add_columns("public", Base.metadata)
        
        # Run check for tenant_acme_corp schema if Postgres
        if is_postgres:
            print("Checking tenant_acme_corp schema tables...")
            await check_and_add_columns("tenant_acme_corp", Base.metadata)

if __name__ == "__main__":
    asyncio.run(main())
