"""add_origin_columns_to_order_slices

Revision ID: e3841da23689
Revises: 059c0b8ba88c
Create Date: 2026-01-17 18:54:14.776604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3841da23689'
down_revision: Union[str, Sequence[str], None] = '059c0b8ba88c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add origin tracing columns to order_slices table."""

    # Add origin columns to order_slices
    op.execute("""
        ALTER TABLE order_slices
        ADD COLUMN origin_trace_id VARCHAR(64) NOT NULL DEFAULT 'migration_default',
        ADD COLUMN origin_trace_source VARCHAR(100) NOT NULL DEFAULT 'migration_default',
        ADD COLUMN origin_request_id VARCHAR(64) NOT NULL DEFAULT 'migration_default',
        ADD COLUMN origin_request_source VARCHAR(100) NOT NULL DEFAULT 'migration_default'
    """)

    # Remove defaults after adding columns
    op.execute("""
        ALTER TABLE order_slices
        ALTER COLUMN origin_trace_id DROP DEFAULT,
        ALTER COLUMN origin_trace_source DROP DEFAULT,
        ALTER COLUMN origin_request_id DROP DEFAULT,
        ALTER COLUMN origin_request_source DROP DEFAULT
    """)

    # Add origin columns to order_slices_history
    op.execute("""
        ALTER TABLE order_slices_history
        ADD COLUMN origin_trace_id VARCHAR(64) NOT NULL DEFAULT 'migration_default',
        ADD COLUMN origin_trace_source VARCHAR(100) NOT NULL DEFAULT 'migration_default',
        ADD COLUMN origin_request_id VARCHAR(64) NOT NULL DEFAULT 'migration_default',
        ADD COLUMN origin_request_source VARCHAR(100) NOT NULL DEFAULT 'migration_default'
    """)

    # Remove defaults from history table
    op.execute("""
        ALTER TABLE order_slices_history
        ALTER COLUMN origin_trace_id DROP DEFAULT,
        ALTER COLUMN origin_trace_source DROP DEFAULT,
        ALTER COLUMN origin_request_id DROP DEFAULT,
        ALTER COLUMN origin_request_source DROP DEFAULT
    """)


def downgrade() -> None:
    """Remove origin tracing columns from order_slices table."""

    op.execute("""
        ALTER TABLE order_slices
        DROP COLUMN origin_trace_id,
        DROP COLUMN origin_trace_source,
        DROP COLUMN origin_request_id,
        DROP COLUMN origin_request_source
    """)

    op.execute("""
        ALTER TABLE order_slices_history
        DROP COLUMN origin_trace_id,
        DROP COLUMN origin_trace_source,
        DROP COLUMN origin_request_id,
        DROP COLUMN origin_request_source
    """)
