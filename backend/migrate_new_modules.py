import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def upgrade_schema():
    dsn = settings.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to {dsn}")
    engine = create_async_engine(dsn, echo=True)
    
    async with engine.begin() as conn:
        print("=== Creating Grow tables ===")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.grow_objectives (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR NOT NULL,
            description VARCHAR,
            owner_id VARCHAR(36),
            status VARCHAR DEFAULT 'draft',
            progress FLOAT DEFAULT 0.0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        print("Created grow_objectives")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.grow_key_results (
            id VARCHAR(36) PRIMARY KEY,
            objective_id VARCHAR(36) NOT NULL,
            title VARCHAR NOT NULL,
            target_value FLOAT DEFAULT 100.0,
            current_value FLOAT DEFAULT 0.0,
            unit VARCHAR DEFAULT 'percent',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(objective_id) REFERENCES tenant_acme_corp.grow_objectives(id) ON DELETE CASCADE
        );
        """))
        print("Created grow_key_results")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.grow_performance_reviews (
            id VARCHAR(36) PRIMARY KEY,
            employee_id VARCHAR(36) NOT NULL,
            manager_id VARCHAR(36),
            period VARCHAR,
            rating FLOAT,
            strengths VARCHAR,
            areas_for_improvement VARCHAR,
            goals VARCHAR,
            status VARCHAR DEFAULT 'draft',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        print("Created grow_performance_reviews")
        
        print("\n=== Creating Ops tables ===")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.ops_assets (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            location VARCHAR,
            status VARCHAR DEFAULT 'available',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        print("Created ops_assets")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.ops_bookings (
            id VARCHAR(36) PRIMARY KEY,
            asset_id VARCHAR(36) NOT NULL,
            employee_id VARCHAR(36) NOT NULL,
            start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            end_time TIMESTAMP WITH TIME ZONE NOT NULL,
            status VARCHAR DEFAULT 'confirmed',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(asset_id) REFERENCES tenant_acme_corp.ops_assets(id) ON DELETE CASCADE,
            FOREIGN KEY(employee_id) REFERENCES tenant_acme_corp.users(id)
        );
        """))
        print("Created ops_bookings")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.ops_visitors (
            id VARCHAR(36) PRIMARY KEY,
            visitor_name VARCHAR NOT NULL,
            company VARCHAR,
            host_id VARCHAR(36) NOT NULL,
            expected_arrival TIMESTAMP WITH TIME ZONE NOT NULL,
            check_in_time TIMESTAMP WITH TIME ZONE,
            check_out_time TIMESTAMP WITH TIME ZONE,
            status VARCHAR DEFAULT 'expected',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(host_id) REFERENCES tenant_acme_corp.users(id)
        );
        """))
        print("Created ops_visitors")
        
        print("\n=== Creating Intelligence tables ===")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.intel_dashboards (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR NOT NULL,
            description VARCHAR,
            owner_id VARCHAR(36),
            is_public BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES tenant_acme_corp.users(id)
        );
        """))
        print("Created intel_dashboards")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.intel_widgets (
            id VARCHAR(36) PRIMARY KEY,
            dashboard_id VARCHAR(36) NOT NULL,
            title VARCHAR NOT NULL,
            widget_type VARCHAR NOT NULL,
            data_source VARCHAR NOT NULL,
            config JSON,
            layout_x INTEGER DEFAULT 0,
            layout_y INTEGER DEFAULT 0,
            layout_w INTEGER DEFAULT 1,
            layout_h INTEGER DEFAULT 1,
            FOREIGN KEY(dashboard_id) REFERENCES tenant_acme_corp.intel_dashboards(id) ON DELETE CASCADE
        );
        """))
        print("Created intel_widgets")
        
        print("\n=== Creating Work Kanban/Wiki tables (if missing) ===")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.work_kanban_boards (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL,
            name VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        print("Created work_kanban_boards")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.work_board_columns (
            id VARCHAR(36) PRIMARY KEY,
            board_id VARCHAR(36) NOT NULL,
            name VARCHAR NOT NULL,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(board_id) REFERENCES tenant_acme_corp.work_kanban_boards(id) ON DELETE CASCADE
        );
        """))
        print("Created work_board_columns")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.work_sprints (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL,
            name VARCHAR NOT NULL,
            start_date TIMESTAMP WITH TIME ZONE,
            end_date TIMESTAMP WITH TIME ZONE,
            status VARCHAR DEFAULT 'planning',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        print("Created work_sprints")
        
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tenant_acme_corp.work_wiki_pages (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36),
            title VARCHAR NOT NULL,
            content TEXT,
            author_id VARCHAR(36),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """))
        print("Created work_wiki_pages")
        
        # Add missing columns to work_tasks if they don't exist
        for col_sql in [
            "ALTER TABLE tenant_acme_corp.work_tasks ADD COLUMN IF NOT EXISTS column_id VARCHAR(36);",
            "ALTER TABLE tenant_acme_corp.work_tasks ADD COLUMN IF NOT EXISTS sprint_id VARCHAR(36);",
            "ALTER TABLE tenant_acme_corp.work_tasks ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0;",
        ]:
            try:
                await conn.execute(text(col_sql))
            except Exception as e:
                print(f"Column may already exist: {e}")

        print("\n=== All tables created successfully! ===")

if __name__ == "__main__":
    asyncio.run(upgrade_schema())
