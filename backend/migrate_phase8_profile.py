import asyncio
import os
import sys
from dotenv import load_dotenv

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def main():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to {dsn}")
    
    engine = create_async_engine(dsn, echo=True)
    dialect = engine.dialect.name
    print(f"Dialect detected: {dialect}")
    
    async with engine.begin() as conn:
        schema_prefix = "tenant_acme_corp." if dialect == "postgresql" else ""
        
        # 1. Add User columns
        user_columns = [
            ("phone_number", "VARCHAR(50)"),
            ("address", "VARCHAR(255)"),
            ("iban", "VARCHAR(100)"),
            ("social_security_number", "VARCHAR(50)"),
            ("emergency_contact", "VARCHAR(255)"),
            ("contract_type", "VARCHAR(100) DEFAULT 'Indefinido'"),
            ("hire_date", "TIMESTAMP WITH TIME ZONE" if dialect == "postgresql" else "TIMESTAMP")
        ]
        
        for col_name, col_type in user_columns:
            try:
                await conn.execute(text(f"ALTER TABLE {schema_prefix}users ADD COLUMN {col_name} {col_type};"))
                print(f"Added column {col_name} to users table.")
            except Exception as e:
                print(f"Column {col_name} might already exist: {e}")
                
        # 2. Add VacationRequest columns
        vacation_columns = [
            ("absence_type", "VARCHAR(50) DEFAULT 'vacation'"),
            ("document_path", "VARCHAR(255)")
        ]
        
        for col_name, col_type in vacation_columns:
            try:
                await conn.execute(text(f"ALTER TABLE {schema_prefix}vacation_requests ADD COLUMN {col_name} {col_type};"))
                print(f"Added column {col_name} to vacation_requests table.")
            except Exception as e:
                print(f"Column {col_name} might already exist: {e}")
                
        # 3. Create profile_change_requests table
        print("Creating profile_change_requests table...")
        if dialect == "postgresql":
            await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS tenant_acme_corp.profile_change_requests (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                field_name VARCHAR(50) NOT NULL,
                old_value VARCHAR(255),
                new_value VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP WITH TIME ZONE,
                reviewed_by VARCHAR(36),
                FOREIGN KEY(user_id) REFERENCES tenant_acme_corp.users(id) ON DELETE CASCADE
            );
            """))
            print("Table profile_change_requests created in PostgreSQL schema.")
        else:
            await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS profile_change_requests (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                field_name VARCHAR(50) NOT NULL,
                old_value VARCHAR(255),
                new_value VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by VARCHAR(36),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """))
            print("Table profile_change_requests created in SQLite.")
            
    print("Migration finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
