import sys
import os
import asyncio
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.core.database import engine

async def run_migration():
    async with engine.begin() as conn:
        # 1. Update public.users
        print("Añadiendo campos i18n a public.users...")
        await conn.execute(text("""
            ALTER TABLE public.users 
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) DEFAULT 'Europe/Madrid',
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR',
            ADD COLUMN IF NOT EXISTS locale VARCHAR(10) DEFAULT 'es';
        """))

        # 2. Update tenant_acme_corp.users
        print("Añadiendo campos i18n a tenant_acme_corp.users...")
        await conn.execute(text("""
            ALTER TABLE tenant_acme_corp.users 
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) DEFAULT 'Europe/Madrid',
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR',
            ADD COLUMN IF NOT EXISTS locale VARCHAR(10) DEFAULT 'es';
        """))
        
        # 3. Update tenant_acme_corp.pay_cycles
        print("Añadiendo currency a tenant_acme_corp.pay_cycles...")
        await conn.execute(text("""
            ALTER TABLE tenant_acme_corp.pay_cycles 
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;
        """))
        
        # 4. Update tenant_acme_corp.pay_payslips
        print("Añadiendo currency a tenant_acme_corp.pay_payslips...")
        await conn.execute(text("""
            ALTER TABLE tenant_acme_corp.pay_payslips 
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;
        """))
        
        print("Migración Fase 7 (i18n) completada con éxito.")

if __name__ == "__main__":
    asyncio.run(run_migration())
