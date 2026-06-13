"""TimescaleDB hypertable migration

Revision ID: timescaledb_hypertables
Revises: add_comments_and_custom_fields
Create Date: 2026-06-07
"""
from typing import Sequence, Union
from alembic import op

revision: str = "timescaledb_hypertables"
down_revision: Union[str, None] = "add_comments_and_custom_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    op.execute("""
        SELECT create_hypertable('agent_execution_runs', 'created_at',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE)
    """)

    op.execute("""
        SELECT create_hypertable('time_logs', 'clock_in',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE)
    """)

    op.execute("""
        SELECT create_hypertable('expense_claims', 'created_at',
            chunk_time_interval => INTERVAL '30 days',
            if_not_exists => TRUE)
    """)

    op.execute("""
        SELECT create_hypertable('kudos', 'created_at',
            chunk_time_interval => INTERVAL '30 days',
            if_not_exists => TRUE)
    """)

    op.execute("""
        SELECT add_retention_policy('agent_execution_runs', INTERVAL '90 days',
            if_not_exists => TRUE)
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS agent_hourly_stats
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', created_at) AS bucket,
            agent_id,
            COUNT(*) AS run_count,
            SUM(cost_usd) AS total_cost,
            AVG(latency_ms) AS avg_latency
        FROM agent_execution_runs
        GROUP BY bucket, agent_id
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS agent_hourly_stats")
    op.execute("SELECT remove_retention_policy('agent_execution_runs', if_exists => TRUE)")
    op.execute("SELECT remove_retention_policy('kudos', if_exists => TRUE)")
    op.execute("SELECT remove_retention_policy('expense_claims', if_exists => TRUE)")
    op.execute("SELECT remove_retention_policy('time_logs', if_exists => TRUE)")
