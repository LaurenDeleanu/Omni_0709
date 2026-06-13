import asyncio
import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath("."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def upgrade_schema():
    # Construct the DSN
    dsn = settings.SQLALCHEMY_DATABASE_URI
    
    print(f"Connecting to {dsn}")
    engine = create_async_engine(dsn, echo=True)
    
    async with engine.begin() as conn:
        print("Adding columns to users table...")
        
        # Add is_super_admin column if it doesn't exist
        try:
            await conn.execute(text("ALTER TABLE tenant_acme_corp.users ADD COLUMN is_super_admin BOOLEAN DEFAULT FALSE;"))
            print("Added is_super_admin")
        except Exception as e:
            print(f"Column is_super_admin may already exist: {e}")
            
        # Add role_id column if it doesn't exist
        try:
            await conn.execute(text("ALTER TABLE tenant_acme_corp.users ADD COLUMN role_id VARCHAR(36);"))
            print("Added role_id")
        except Exception as e:
            print(f"Column role_id may already exist: {e}")
            
        print("Creating RBAC tables...")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.roles (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.permissions (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description VARCHAR(255),
            module VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.role_permissions (
            id VARCHAR(36) PRIMARY KEY,
            role_id VARCHAR(36) NOT NULL,
            permission_id VARCHAR(36) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(role_id) REFERENCES tenant_acme_corp.roles(id) ON DELETE CASCADE,
            FOREIGN KEY(permission_id) REFERENCES tenant_acme_corp.permissions(id) ON DELETE CASCADE,
            UNIQUE(role_id, permission_id)
        );
        """))
        
        print("Done upgrading tenant_acme_corp schema.")

if __name__ == "__main__":
    asyncio.run(upgrade_schema())
