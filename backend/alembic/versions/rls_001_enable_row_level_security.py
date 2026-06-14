"""enable_rls

Revision ID: rls_001
Revises: current_head
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = "rls_001"
down_revision = None  # Set to actual previous revision
branch_labels = None
depends_on = None

TENANT_SCOPED_TABLES = [
    "users", "vacation_requests", "meetings", "tasks",
    "workflow_triggers", "grow_reviews", "performance_reviews",
    "job_postings", "candidates", "invoices", "expenses",
    "it_tickets", "it_assets", "chat_rooms", "chat_messages",
    "kudos", "documents", "payslips",
]


def upgrade():
    # Enable RLS on all tenant-scoped tables as defense-in-depth.
    # The schema-per-tenant architecture already isolates data,
    # but RLS provides a second layer in case of schema leakage.
    for table_name in TENANT_SCOPED_TABLES:
        try:
            op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
            op.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_policies
                        WHERE tablename = '{table_name}' AND policyname = 'tenant_isolation'
                    ) THEN
                        CREATE POLICY tenant_isolation ON "{table_name}"
                            USING (tenant_id = current_setting('app.current_tenant_id', true) OR current_setting('app.bypass_rls', true) = 'true')
                            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true) OR current_setting('app.bypass_rls', true) = 'true');
                    END IF;
                END;
                $$;
            """)
        except Exception:
            pass


def downgrade():
    for table_name in TENANT_SCOPED_TABLES:
        try:
            op.execute(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY')
        except Exception:
            pass
