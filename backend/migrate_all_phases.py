import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.models.base import Base

# Import all models to register them with SQLAlchemy Base
import app.models
import app.models.push
import app.models.integration

async def main():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to: {dsn}")
    
    engine = create_async_engine(dsn, echo=True)
    dialect = engine.dialect.name
    print(f"Dialect detected: {dialect}")
    
    # 1. Create standard tables in default/public schema
    print("=== Creating tables in default/public schema ===")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Standard public tables created/verified.")

    # 2. Create tables in tenant_acme_corp schema (PostgreSQL specific)
    if dialect == "postgresql":
        print("=== Creating tables in tenant_acme_corp schema ===")
        tenant_engine = engine.execution_options(schema_translate_map={None: "tenant_acme_corp"})
        async with tenant_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Standard tenant tables created/verified.")

    # 3. Apply ALTER TABLE statements to add missing columns safely
    async with engine.begin() as conn:
        print("=== Applying specific migrations and schema patches ===")
        
        # public schema modifications (for users)
        public_user_alters = [
            ("timezone", "VARCHAR(100) DEFAULT 'Europe/Madrid'"),
            ("currency", "VARCHAR(3) DEFAULT 'EUR'"),
            ("locale", "VARCHAR(10) DEFAULT 'es'"),
            ("manager_id", "VARCHAR(255)"),
            ("vacation_allowance", "INTEGER DEFAULT 30")
        ]
        for col, col_type in public_user_alters:
            try:
                await conn.execute(text(f"ALTER TABLE public.users ADD COLUMN IF NOT EXISTS {col} {col_type};"))
                print(f"Column public.users.{col} added or verified.")
            except Exception as e:
                print(f"Failed to add public.users.{col} (non-fatal): {e}")

        # tenant schema modifications (PostgreSQL specific)
        if dialect == "postgresql":
            # tenant_acme_corp.users
            tenant_user_alters = [
                ("timezone", "VARCHAR(100) DEFAULT 'Europe/Madrid'"),
                ("currency", "VARCHAR(3) DEFAULT 'EUR'"),
                ("locale", "VARCHAR(10) DEFAULT 'es'"),
                ("manager_id", "VARCHAR(255)"),
                ("vacation_allowance", "INTEGER DEFAULT 30"),
                ("phone_number", "VARCHAR(50)"),
                ("address", "VARCHAR(255)"),
                ("iban", "VARCHAR(100)"),
                ("social_security_number", "VARCHAR(50)"),
                ("emergency_contact", "VARCHAR(255)"),
                ("contract_type", "VARCHAR(100) DEFAULT 'Indefinido'"),
                ("hire_date", "TIMESTAMP WITH TIME ZONE")
            ]
            for col, col_type in tenant_user_alters:
                try:
                    await conn.execute(text(f"ALTER TABLE tenant_acme_corp.users ADD COLUMN IF NOT EXISTS {col} {col_type};"))
                    print(f"Column tenant_acme_corp.users.{col} added or verified.")
                except Exception as e:
                    print(f"Failed to add tenant_acme_corp.users.{col} (non-fatal): {e}")

            # tenant_acme_corp.vacation_requests
            vacation_alters = [
                ("absence_type", "VARCHAR(50) DEFAULT 'vacation'"),
                ("document_path", "VARCHAR(255)")
            ]
            for col, col_type in vacation_alters:
                try:
                    await conn.execute(text(f"ALTER TABLE tenant_acme_corp.vacation_requests ADD COLUMN IF NOT EXISTS {col} {col_type};"))
                    print(f"Column tenant_acme_corp.vacation_requests.{col} added or verified.")
                except Exception as e:
                    print(f"Failed to add tenant_acme_corp.vacation_requests.{col} (non-fatal): {e}")

            # tenant_acme_corp.pay_cycles
            try:
                await conn.execute(text("ALTER TABLE tenant_acme_corp.pay_cycles ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;"))
                print("Column tenant_acme_corp.pay_cycles.currency added or verified.")
            except Exception as e:
                print(f"Failed to add pay_cycles.currency (non-fatal): {e}")

            # tenant_acme_corp.pay_payslips
            try:
                await conn.execute(text("ALTER TABLE tenant_acme_corp.pay_payslips ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;"))
                print("Column tenant_acme_corp.pay_payslips.currency added or verified.")
            except Exception as e:
                print(f"Failed to add pay_payslips.currency (non-fatal): {e}")
                
        else:
            # SQLite fallback modifications
            sqlite_user_alters = [
                ("timezone", "VARCHAR(100) DEFAULT 'Europe/Madrid'"),
                ("currency", "VARCHAR(3) DEFAULT 'EUR'"),
                ("locale", "VARCHAR(10) DEFAULT 'es'"),
                ("manager_id", "VARCHAR(255)"),
                ("vacation_allowance", "INTEGER DEFAULT 30"),
                ("phone_number", "VARCHAR(50)"),
                ("address", "VARCHAR(255)"),
                ("iban", "VARCHAR(100)"),
                ("social_security_number", "VARCHAR(50)"),
                ("emergency_contact", "VARCHAR(255)"),
                ("contract_type", "VARCHAR(100) DEFAULT 'Indefinido'"),
                ("hire_date", "TIMESTAMP")
            ]
            for col, col_type in sqlite_user_alters:
                try:
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type};"))
                    print(f"Column users.{col} added or verified (SQLite).")
                except Exception as e:
                    print(f"Failed to add users.{col} (non-fatal SQLite): {e}")

            sqlite_vacation_alters = [
                ("absence_type", "VARCHAR(50) DEFAULT 'vacation'"),
                ("document_path", "VARCHAR(255)")
            ]
            for col, col_type in sqlite_vacation_alters:
                try:
                    await conn.execute(text(f"ALTER TABLE vacation_requests ADD COLUMN {col} {col_type};"))
                    print(f"Column vacation_requests.{col} added or verified (SQLite).")
                except Exception as e:
                    print(f"Failed to add vacation_requests.{col} (non-fatal SQLite): {e}")

            try:
                await conn.execute(text("ALTER TABLE pay_cycles ADD COLUMN currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;"))
                print("Column pay_cycles.currency added or verified (SQLite).")
            except Exception as e:
                print(f"Failed to add pay_cycles.currency (non-fatal SQLite): {e}")

            try:
                await conn.execute(text("ALTER TABLE pay_payslips ADD COLUMN currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;"))
                print("Column pay_payslips.currency added or verified (SQLite).")
            except Exception as e:
                print(f"Failed to add pay_payslips.currency (non-fatal SQLite): {e}")

    print("=== Database migrations completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(main())
