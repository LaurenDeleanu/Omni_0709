"""materialized_views_v1

Revision ID: materialized_views_v1
Revises: timescaledb_hypertables
Create Date: 2026-06-07

Creates 4 materialized views for BI dashboards:
  - mv_employee_headcount
  - mv_monthly_payroll
  - mv_hiring_funnel
  - mv_training_completion
Plus a refresh_all_matviews() function.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'materialized_views_v1'
down_revision: Union[str, Sequence[str], None] = 'timescaledb_hypertables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE MATERIALIZED VIEW mv_employee_headcount AS
        SELECT
            COALESCE(department, 'Unassigned') AS department,
            role,
            COUNT(*) FILTER (WHERE is_active = true)  AS active_count,
            COUNT(*) FILTER (WHERE is_active = false) AS inactive_count,
            COUNT(*)                                   AS total_count
        FROM users
        GROUP BY department, role
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_mv_employee_headcount_dept_role
        ON mv_employee_headcount (department, role)
    """)
    op.execute("""
        CREATE INDEX ix_mv_employee_headcount_dept
        ON mv_employee_headcount (department)
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW mv_monthly_payroll AS
        SELECT
            date_trunc('month', pp.created_at) AS month,
            pp.currency,
            SUM(pp.gross_salary)               AS total_gross,
            SUM(pp.net_salary)                 AS total_net,
            SUM(pp.deductions)                 AS total_deductions,
            COUNT(*)                           AS payslip_count
        FROM pay_payslips pp
        GROUP BY date_trunc('month', pp.created_at), pp.currency
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_mv_monthly_payroll_month_curr
        ON mv_monthly_payroll (month, currency)
    """)
    op.execute("""
        CREATE INDEX ix_mv_monthly_payroll_month
        ON mv_monthly_payroll (month)
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW mv_hiring_funnel AS
        SELECT
            job_id,
            stage,
            COUNT(*) AS candidate_count
        FROM hire_candidates
        GROUP BY job_id, stage
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_mv_hiring_funnel_job_stage
        ON mv_hiring_funnel (job_id, stage)
    """)
    op.execute("""
        CREATE INDEX ix_mv_hiring_funnel_stage
        ON mv_hiring_funnel (stage)
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW mv_training_completion AS
        SELECT
            course_id,
            COUNT(*)                                             AS total_enrollments,
            COUNT(*) FILTER (WHERE status = 'completed')         AS completed_count,
            CASE WHEN COUNT(*) > 0 THEN
                ROUND(COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*), 2)
            ELSE 0 END                                           AS completion_rate,
            AVG(COALESCE(score, 0))                              AS avg_score,
            AVG(time_spent_seconds)                              AS avg_time_spent_seconds
        FROM course_enrollments
        GROUP BY course_id
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_mv_training_completion_course
        ON mv_training_completion (course_id)
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_all_matviews()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_employee_headcount;
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_payroll;
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hiring_funnel;
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_training_completion;
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS refresh_all_matviews()")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_training_completion")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_hiring_funnel")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_monthly_payroll")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_employee_headcount")
