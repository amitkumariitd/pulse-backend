"""create_order_slice_executions_table

Revision ID: 53b0b9b95498
Revises: 723955a9c433
Create Date: 2026-01-17 18:18:51.100316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53b0b9b95498'
down_revision: Union[str, Sequence[str], None] = '723955a9c433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_slice_executions table for tracking execution details."""

    # Create order_slice_executions table
    op.execute("""
        CREATE TABLE order_slice_executions (
            -- Identity (one execution per slice)
            id VARCHAR(64) PRIMARY KEY,
            slice_id VARCHAR(64) NOT NULL UNIQUE REFERENCES order_slices(id) ON DELETE CASCADE,

            -- Ownership and concurrency control
            attempt_id VARCHAR(100) NOT NULL UNIQUE,
            executor_id VARCHAR(100) NOT NULL,
            executor_claimed_at TIMESTAMPTZ NOT NULL,
            executor_timeout_at TIMESTAMPTZ NOT NULL,
            last_heartbeat_at TIMESTAMPTZ NOT NULL,

            -- Execution status
            execution_status VARCHAR(20) NOT NULL DEFAULT 'CLAIMED'
                CHECK (execution_status IN (
                    'CLAIMED',
                    'PLACED',
                    'COMPLETED',
                    'SKIPPED'
                )),

            -- Broker interaction
            broker_order_id VARCHAR(100),
            broker_order_status VARCHAR(20)
                CHECK (broker_order_status IS NULL OR broker_order_status IN (
                    'PENDING',
                    'OPEN',
                    'PARTIALLY_FILLED',
                    'COMPLETE',
                    'CANCELLED',
                    'REJECTED',
                    'EXPIRED'
                )),

            -- Execution result
            filled_quantity INTEGER DEFAULT 0 CHECK (filled_quantity >= 0),
            average_price DECIMAL(15, 4),
            execution_result VARCHAR(30)
                CHECK (execution_result IS NULL OR execution_result IN (
                    'SUCCESS',
                    'PARTIAL_SUCCESS',
                    'BROKER_REJECTED',
                    'VALIDATION_FAILED',
                    'EXECUTOR_TIMEOUT'
                )),

            -- Retry tracking (for technical failures within this execution)
            placement_attempts INTEGER DEFAULT 0 CHECK (placement_attempts >= 0),
            last_attempt_at TIMESTAMPTZ,
            last_attempt_error VARCHAR(50),

            -- Timing
            validation_started_at TIMESTAMPTZ,
            placement_confirmed_at TIMESTAMPTZ,
            last_broker_poll_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,

            -- Error tracking
            error_code VARCHAR(50),
            error_message TEXT,

            -- Tracing
            request_id VARCHAR(64) NOT NULL,

            -- Timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX idx_executions_slice_id ON order_slice_executions(slice_id)")
    op.execute("CREATE INDEX idx_executions_executor_id ON order_slice_executions(executor_id)")
    op.execute("CREATE INDEX idx_executions_status ON order_slice_executions(execution_status)")
    op.execute("""
        CREATE INDEX idx_executions_active ON order_slice_executions(executor_timeout_at)
        WHERE execution_status IN ('CLAIMED', 'PLACED')
    """)

    # Create history table
    op.execute("""
        CREATE TABLE order_slice_executions_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            id VARCHAR(64) NOT NULL,
            slice_id VARCHAR(64) NOT NULL,
            attempt_id VARCHAR(100) NOT NULL,
            executor_id VARCHAR(100) NOT NULL,
            executor_claimed_at TIMESTAMPTZ NOT NULL,
            executor_timeout_at TIMESTAMPTZ NOT NULL,
            last_heartbeat_at TIMESTAMPTZ NOT NULL,
            execution_status VARCHAR(20) NOT NULL,
            broker_order_id VARCHAR(100),
            broker_order_status VARCHAR(20),
            filled_quantity INTEGER,
            average_price DECIMAL(15, 4),
            execution_result VARCHAR(30),
            placement_attempts INTEGER,
            last_attempt_at TIMESTAMPTZ,
            last_attempt_error VARCHAR(50),
            validation_started_at TIMESTAMPTZ,
            placement_confirmed_at TIMESTAMPTZ,
            last_broker_poll_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            error_code VARCHAR(50),
            error_message TEXT,
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Create trigger function for history
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slice_executions_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slice_executions_history SELECT 'DELETE', NOW(), OLD.*;
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slice_executions_history SELECT 'UPDATE', NOW(), OLD.*;
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slice_executions_history SELECT 'INSERT', NOW(), NEW.*;
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER order_slice_executions_history_insert
        AFTER INSERT ON order_slice_executions
        FOR EACH ROW EXECUTE FUNCTION order_slice_executions_history_trigger()
    """)

    op.execute("""
        CREATE TRIGGER order_slice_executions_history_update
        AFTER UPDATE ON order_slice_executions
        FOR EACH ROW EXECUTE FUNCTION order_slice_executions_history_trigger()
    """)

    op.execute("""
        CREATE TRIGGER order_slice_executions_history_delete
        AFTER DELETE ON order_slice_executions
        FOR EACH ROW EXECUTE FUNCTION order_slice_executions_history_trigger()
    """)


def downgrade() -> None:
    """Drop order_slice_executions table."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS order_slice_executions_history_delete ON order_slice_executions")
    op.execute("DROP TRIGGER IF EXISTS order_slice_executions_history_update ON order_slice_executions")
    op.execute("DROP TRIGGER IF EXISTS order_slice_executions_history_insert ON order_slice_executions")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS order_slice_executions_history_trigger()")

    # Drop history table
    op.execute("DROP TABLE IF EXISTS order_slice_executions_history")

    # Drop main table (indexes will be dropped automatically)
    op.execute("DROP TABLE IF EXISTS order_slice_executions")
