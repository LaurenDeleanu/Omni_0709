"""add roles column to users

Revision ID: add_roles_column_to_users
Revises: add_invoices_and_currency_rates
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "add_roles_column_to_users"
down_revision: Union[str, None] = "add_invoices_and_currency_rates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL to add the column conditionally, avoiding DuplicateColumnError 
    # if it was manually added to the public schema previously.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS roles JSON DEFAULT '[\"employee\"]' NOT NULL")


def downgrade() -> None:
    op.drop_column("users", "roles")
