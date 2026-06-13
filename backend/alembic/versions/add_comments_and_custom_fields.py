"""add comments table and custom_fields to users

Revision ID: add_comments_and_custom_fields
Revises: idx_performance_v1
Create Date: 2026-06-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "add_comments_and_custom_fields"
down_revision: Union[str, None] = "idx_performance_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("author_name", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_entity", "comments", ["entity_type", "entity_id"], if_not_exists=True)
    op.create_index("ix_comments_parent", "comments", ["parent_id"], if_not_exists=True)

    op.add_column("users", sa.Column("custom_fields", sa.JSON(), nullable=False, server_default="{}"))

    op.add_column("knowledge_chunks", sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("knowledge_chunks", "metadata")
    op.drop_column("users", "custom_fields")
    op.drop_index("ix_comments_parent", table_name="comments", if_exists=True)
    op.drop_index("ix_comments_entity", table_name="comments", if_exists=True)
    op.drop_table("comments")
