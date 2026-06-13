"""add_metadata_table

Revision ID: cedbdecaecce
Revises: 0a1913327c5e
Create Date: 2026-05-24 15:59:27.925701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cedbdecaecce'
down_revision: Union[str, Sequence[str], None] = '0a1913327c5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('page_metadata',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('module_name', sa.String(length=50), nullable=False),
        sa.Column('page_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('schema_data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module_name', 'page_name', name='uix_module_page')
    )
    op.create_index(op.f('ix_page_metadata_module_name'), 'page_metadata', ['module_name'], unique=False)
    op.create_index(op.f('ix_page_metadata_page_name'), 'page_metadata', ['page_name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_page_metadata_page_name'), table_name='page_metadata')
    op.drop_index(op.f('ix_page_metadata_module_name'), table_name='page_metadata')
    op.drop_table('page_metadata')
