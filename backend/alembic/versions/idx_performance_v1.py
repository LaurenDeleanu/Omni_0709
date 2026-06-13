"""add performance indexes

Revision ID: idx_performance_v1
Revises: cedbdecaecce
Create Date: 2026-06-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "idx_performance_v1"
down_revision: Union[str, None] = "cedbdecaecce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_department", "users", ["department"], if_not_exists=True)
    op.create_index("ix_users_role", "users", ["role"], if_not_exists=True)
    op.create_index("ix_users_is_active", "users", ["is_active"], if_not_exists=True)

    op.create_index("ix_vacation_requests_status", "vacation_requests", ["status"], if_not_exists=True)
    op.create_index("ix_vacation_requests_user_status", "vacation_requests", ["user_id", "status"], if_not_exists=True)

    op.create_index("ix_tasks_status", "tasks", ["status"], if_not_exists=True)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], if_not_exists=True)
    op.create_index("ix_tasks_assigned_status", "tasks", ["assigned_to", "status"], if_not_exists=True)

    op.create_index("ix_expense_claims_status", "expense_claims", ["status"], if_not_exists=True)
    op.create_index("ix_expense_claims_user_status", "expense_claims", ["user_id", "status"], if_not_exists=True)

    op.create_index("ix_time_logs_user_clock_in", "time_logs", ["user_id", "clock_in"], if_not_exists=True)

    op.create_index("ix_it_tickets_status", "it_tickets", ["status"], if_not_exists=True)
    op.create_index("ix_it_tickets_priority", "it_tickets", ["priority"], if_not_exists=True)

    op.create_index("ix_it_assets_status", "it_assets", ["status"], if_not_exists=True)
    op.create_index("ix_it_assets_assigned_to", "it_assets", ["assigned_to_id"], if_not_exists=True)

    op.create_index("ix_course_enrollments_status", "course_enrollments", ["status"], if_not_exists=True)
    op.create_index("ix_course_enrollments_user_status", "course_enrollments", ["user_id", "status"], if_not_exists=True)

    op.create_index("ix_hire_jobs_status", "hire_jobs", ["status"], if_not_exists=True)
    op.create_index("ix_hire_candidates_stage", "hire_candidates", ["stage"], if_not_exists=True)
    op.create_index("ix_hire_candidates_job_stage", "hire_candidates", ["job_id", "stage"], if_not_exists=True)

    op.create_index("ix_pay_cycles_status", "pay_cycles", ["status"], if_not_exists=True)
    op.create_index("ix_pay_payslips_cycle_status", "pay_payslips", ["cycle_id", "status"], if_not_exists=True)

    op.create_index("ix_legal_contracts_status", "legal_contracts", ["status"], if_not_exists=True)
    op.create_index("ix_legal_whistleblower_reports_status", "legal_whistleblower_reports", ["status"], if_not_exists=True)

    op.create_index("ix_grow_objectives_status", "grow_objectives", ["status"], if_not_exists=True)
    op.create_index("ix_grow_objectives_owner", "grow_objectives", ["owner_id"], if_not_exists=True)

    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"], if_not_exists=True)

    op.create_index("ix_notifications_user_read_created", "notifications", ["user_id", "is_read", "created_at"], if_not_exists=True)

    op.create_index("ix_kudos_receiver_created", "kudos", ["receiver_id", "created_at"], if_not_exists=True)
    op.create_index("ix_kudos_sender", "kudos", ["sender_id"], if_not_exists=True)

    op.create_index("ix_agent_execution_runs_agent_created", "agent_execution_runs", ["agent_id", "created_at"], if_not_exists=True)
    op.create_index("ix_agent_execution_runs_status", "agent_execution_runs", ["status"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_agent_execution_runs_status", table_name="agent_execution_runs", if_exists=True)
    op.drop_index("ix_agent_execution_runs_agent_created", table_name="agent_execution_runs", if_exists=True)
    op.drop_index("ix_kudos_sender", table_name="kudos", if_exists=True)
    op.drop_index("ix_kudos_receiver_created", table_name="kudos", if_exists=True)
    op.drop_index("ix_notifications_user_read_created", table_name="notifications", if_exists=True)
    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs", if_exists=True)
    op.drop_index("ix_grow_objectives_owner", table_name="grow_objectives", if_exists=True)
    op.drop_index("ix_grow_objectives_status", table_name="grow_objectives", if_exists=True)
    op.drop_index("ix_legal_whistleblower_reports_status", table_name="legal_whistleblower_reports", if_exists=True)
    op.drop_index("ix_legal_contracts_status", table_name="legal_contracts", if_exists=True)
    op.drop_index("ix_pay_payslips_cycle_status", table_name="pay_payslips", if_exists=True)
    op.drop_index("ix_pay_cycles_status", table_name="pay_cycles", if_exists=True)
    op.drop_index("ix_hire_candidates_job_stage", table_name="hire_candidates", if_exists=True)
    op.drop_index("ix_hire_candidates_stage", table_name="hire_candidates", if_exists=True)
    op.drop_index("ix_hire_jobs_status", table_name="hire_jobs", if_exists=True)
    op.drop_index("ix_course_enrollments_user_status", table_name="course_enrollments", if_exists=True)
    op.drop_index("ix_course_enrollments_status", table_name="course_enrollments", if_exists=True)
    op.drop_index("ix_it_assets_assigned_to", table_name="it_assets", if_exists=True)
    op.drop_index("ix_it_assets_status", table_name="it_assets", if_exists=True)
    op.drop_index("ix_it_tickets_priority", table_name="it_tickets", if_exists=True)
    op.drop_index("ix_it_tickets_status", table_name="it_tickets", if_exists=True)
    op.drop_index("ix_time_logs_user_clock_in", table_name="time_logs", if_exists=True)
    op.drop_index("ix_expense_claims_user_status", table_name="expense_claims", if_exists=True)
    op.drop_index("ix_expense_claims_status", table_name="expense_claims", if_exists=True)
    op.drop_index("ix_tasks_assigned_status", table_name="tasks", if_exists=True)
    op.drop_index("ix_tasks_priority", table_name="tasks", if_exists=True)
    op.drop_index("ix_tasks_status", table_name="tasks", if_exists=True)
    op.drop_index("ix_vacation_requests_user_status", table_name="vacation_requests", if_exists=True)
    op.drop_index("ix_vacation_requests_status", table_name="vacation_requests", if_exists=True)
    op.drop_index("ix_users_is_active", table_name="users", if_exists=True)
    op.drop_index("ix_users_role", table_name="users", if_exists=True)
    op.drop_index("ix_users_department", table_name="users", if_exists=True)
