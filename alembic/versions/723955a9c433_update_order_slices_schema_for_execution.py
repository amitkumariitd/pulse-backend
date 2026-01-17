"""update_order_slices_schema_for_execution

Revision ID: 723955a9c433
Revises: 1767086939
Create Date: 2026-01-17 18:18:00.130008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '723955a9c433'
down_revision: Union[str, Sequence[str], None] = '1767086939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support order slice execution.

    Changes:
    1. Update status values: SCHEDULED -> PENDING, EXECUTED -> COMPLETED, FAILED -> removed
    2. Add order parameters: order_type, limit_price, product_type, validity
    3. Add execution results: filled_quantity, average_price
    4. Remove origin_* columns (not an async-initiating table)
    """

    # Step 1: Drop old status constraint first
    op.execute("ALTER TABLE order_slices DROP CONSTRAINT IF EXISTS order_slices_status_check")

    # Step 2: Update existing status values to new schema
    # SCHEDULED -> PENDING
    op.execute("UPDATE order_slices SET status = 'PENDING' WHERE status = 'SCHEDULED'")
    # READY -> PENDING (both mean ready to execute)
    op.execute("UPDATE order_slices SET status = 'PENDING' WHERE status = 'READY'")
    # EXECUTED -> COMPLETED
    op.execute("UPDATE order_slices SET status = 'COMPLETED' WHERE status = 'EXECUTED'")
    # FAILED -> COMPLETED (execution finished, check execution table for result)
    op.execute("UPDATE order_slices SET status = 'COMPLETED' WHERE status = 'FAILED'")

    # Step 3: Add new status constraint
    op.execute("""
        ALTER TABLE order_slices
        ADD CONSTRAINT order_slices_status_check
        CHECK (status IN ('PENDING', 'EXECUTING', 'COMPLETED', 'CANCELLED', 'SKIPPED'))
    """)

    # Step 4: Add new columns
    op.execute("""
        ALTER TABLE order_slices
        ADD COLUMN order_type VARCHAR(20) DEFAULT 'MARKET' CHECK (order_type IN ('MARKET', 'LIMIT')),
        ADD COLUMN limit_price DECIMAL(15, 4),
        ADD COLUMN product_type VARCHAR(20) DEFAULT 'CNC',
        ADD COLUMN validity VARCHAR(10) DEFAULT 'DAY',
        ADD COLUMN filled_quantity INTEGER DEFAULT 0 CHECK (filled_quantity >= 0),
        ADD COLUMN average_price DECIMAL(15, 4)
    """)

    # Step 5: Drop origin_* columns (not an async-initiating table)
    op.execute("ALTER TABLE order_slices DROP COLUMN IF EXISTS origin_trace_id")
    op.execute("ALTER TABLE order_slices DROP COLUMN IF EXISTS origin_trace_source")
    op.execute("ALTER TABLE order_slices DROP COLUMN IF EXISTS origin_request_id")
    op.execute("ALTER TABLE order_slices DROP COLUMN IF EXISTS origin_request_source")

    # Step 6: Drop old index and create new one
    op.execute("DROP INDEX IF EXISTS idx_order_slices_scheduled")
    op.execute("""
        CREATE INDEX idx_order_slices_status_scheduled
        ON order_slices(status, scheduled_at)
        WHERE status = 'PENDING'
    """)

    # Step 7: Update history table to match
    op.execute("""
        ALTER TABLE order_slices_history
        ADD COLUMN order_type VARCHAR(20),
        ADD COLUMN limit_price DECIMAL(15, 4),
        ADD COLUMN product_type VARCHAR(20),
        ADD COLUMN validity VARCHAR(10),
        ADD COLUMN filled_quantity INTEGER,
        ADD COLUMN average_price DECIMAL(15, 4)
    """)

    op.execute("ALTER TABLE order_slices_history DROP COLUMN IF EXISTS origin_trace_id")
    op.execute("ALTER TABLE order_slices_history DROP COLUMN IF EXISTS origin_trace_source")
    op.execute("ALTER TABLE order_slices_history DROP COLUMN IF EXISTS origin_request_id")
    op.execute("ALTER TABLE order_slices_history DROP COLUMN IF EXISTS origin_request_source")


def downgrade() -> None:
    """Downgrade schema."""

    # Step 1: Add back origin_* columns
    op.execute("""
        ALTER TABLE order_slices
        ADD COLUMN origin_trace_id VARCHAR(64),
        ADD COLUMN origin_trace_source VARCHAR(100),
        ADD COLUMN origin_request_id VARCHAR(64),
        ADD COLUMN origin_request_source VARCHAR(100)
    """)

    # Step 2: Revert status values
    op.execute("UPDATE order_slices SET status = 'SCHEDULED' WHERE status = 'PENDING'")
    op.execute("UPDATE order_slices SET status = 'EXECUTED' WHERE status = 'COMPLETED'")

    # Step 3: Drop new status constraint and restore old one
    op.execute("ALTER TABLE order_slices DROP CONSTRAINT IF EXISTS order_slices_status_check")
    op.execute("""
        ALTER TABLE order_slices
        ADD CONSTRAINT order_slices_status_check
        CHECK (status IN ('SCHEDULED', 'READY', 'EXECUTING', 'EXECUTED', 'FAILED', 'SKIPPED'))
    """)

    # Step 4: Drop new columns
    op.execute("""
        ALTER TABLE order_slices
        DROP COLUMN IF EXISTS order_type,
        DROP COLUMN IF EXISTS limit_price,
        DROP COLUMN IF EXISTS product_type,
        DROP COLUMN IF EXISTS validity,
        DROP COLUMN IF EXISTS filled_quantity,
        DROP COLUMN IF EXISTS average_price
    """)

    # Step 5: Restore old index
    op.execute("DROP INDEX IF EXISTS idx_order_slices_status_scheduled")
    op.execute("""
        CREATE INDEX idx_order_slices_scheduled
        ON order_slices(status, scheduled_at)
        WHERE status = 'SCHEDULED'
    """)

    # Step 6: Update history table
    op.execute("""
        ALTER TABLE order_slices_history
        ADD COLUMN origin_trace_id VARCHAR(64),
        ADD COLUMN origin_trace_source VARCHAR(100),
        ADD COLUMN origin_request_id VARCHAR(64),
        ADD COLUMN origin_request_source VARCHAR(100)
    """)

    op.execute("""
        ALTER TABLE order_slices_history
        DROP COLUMN IF EXISTS order_type,
        DROP COLUMN IF EXISTS limit_price,
        DROP COLUMN IF EXISTS product_type,
        DROP COLUMN IF EXISTS validity,
        DROP COLUMN IF EXISTS filled_quantity,
        DROP COLUMN IF EXISTS average_price
    """)
