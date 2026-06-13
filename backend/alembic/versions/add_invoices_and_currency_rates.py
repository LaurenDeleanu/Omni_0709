"""add_invoices_and_currency_rates

Revision ID: add_invoices_and_currency_rates
Revises: materialized_views_v1
Create Date: 2026-06-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_invoices_and_currency_rates'
down_revision: Union[str, None] = 'materialized_views_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("type", sa.String(10), server_default="payable"),
        sa.Column("vendor_client", sa.String(200), server_default=""),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("amount", sa.Float(), server_default="0.0"),
        sa.Column("tax_amount", sa.Float(), server_default="0.0"),
        sa.Column("total_amount", sa.Float(), server_default="0.0"),
        sa.Column("currency", sa.String(3), server_default="EUR"),
        sa.Column("exchange_rate", sa.Float(), server_default="1.0"),
        sa.Column("base_amount", sa.Float(), server_default="0.0"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("issue_date", sa.DateTime(), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("paid_date", sa.DateTime(), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("tenant_id", sa.String(50), server_default="default"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_table(
        "currency_rates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("rate_to_eur", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("currency_rates")
    op.drop_table("invoices")
