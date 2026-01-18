"""create_order_slice_executions_table

Revision ID: 1768674602
Revises: 1768674601
Create Date: 2026-01-18 00:00:02

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1768674602'
down_revision: Union[str, Sequence[str], None] = '1768674601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_slice_executions table with history and triggers."""

    # Create order_slice_executions table (NOT async-initiating)
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

    # Create trigger function with explicit column lists
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slice_executions_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slice_executions_history (
                    operation, changed_at,
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, broker_order_id, broker_order_status,
                    filled_quantity, average_price, execution_result,
                    placement_attempts, last_attempt_at, last_attempt_error,
                    validation_started_at, placement_confirmed_at, last_broker_poll_at,
                    completed_at, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'DELETE', NOW(),
                    OLD.id, OLD.slice_id, OLD.attempt_id, OLD.executor_id,
                    OLD.executor_claimed_at, OLD.executor_timeout_at, OLD.last_heartbeat_at,
                    OLD.execution_status, OLD.broker_order_id, OLD.broker_order_status,
                    OLD.filled_quantity, OLD.average_price, OLD.execution_result,
                    OLD.placement_attempts, OLD.last_attempt_at, OLD.last_attempt_error,
                    OLD.validation_started_at, OLD.placement_confirmed_at, OLD.last_broker_poll_at,
                    OLD.completed_at, OLD.error_code, OLD.error_message,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slice_executions_history (
                    operation, changed_at,
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, broker_order_id, broker_order_status,
                    filled_quantity, average_price, execution_result,
                    placement_attempts, last_attempt_at, last_attempt_error,
                    validation_started_at, placement_confirmed_at, last_broker_poll_at,
                    completed_at, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'UPDATE', NOW(),
                    OLD.id, OLD.slice_id, OLD.attempt_id, OLD.executor_id,
                    OLD.executor_claimed_at, OLD.executor_timeout_at, OLD.last_heartbeat_at,
                    OLD.execution_status, OLD.broker_order_id, OLD.broker_order_status,
                    OLD.filled_quantity, OLD.average_price, OLD.execution_result,
                    OLD.placement_attempts, OLD.last_attempt_at, OLD.last_attempt_error,
                    OLD.validation_started_at, OLD.placement_confirmed_at, OLD.last_broker_poll_at,
                    OLD.completed_at, OLD.error_code, OLD.error_message,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slice_executions_history (
                    operation, changed_at,
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, broker_order_id, broker_order_status,
                    filled_quantity, average_price, execution_result,
                    placement_attempts, last_attempt_at, last_attempt_error,
                    validation_started_at, placement_confirmed_at, last_broker_poll_at,
                    completed_at, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'INSERT', NOW(),
                    NEW.id, NEW.slice_id, NEW.attempt_id, NEW.executor_id,
                    NEW.executor_claimed_at, NEW.executor_timeout_at, NEW.last_heartbeat_at,
                    NEW.execution_status, NEW.broker_order_id, NEW.broker_order_status,
                    NEW.filled_quantity, NEW.average_price, NEW.execution_result,
                    NEW.placement_attempts, NEW.last_attempt_at, NEW.last_attempt_error,
                    NEW.validation_started_at, NEW.placement_confirmed_at, NEW.last_broker_poll_at,
                    NEW.completed_at, NEW.error_code, NEW.error_message,
                    NEW.request_id, NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER order_slice_executions_history_trigger
        AFTER INSERT OR UPDATE OR DELETE ON order_slice_executions
        FOR EACH ROW EXECUTE FUNCTION order_slice_executions_history_trigger()
    """)


def downgrade() -> None:
    """Drop order_slice_executions table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS order_slice_executions_history_trigger ON order_slice_executions")
    op.execute("DROP FUNCTION IF EXISTS order_slice_executions_history_trigger()")
    op.execute("DROP TABLE IF EXISTS order_slice_executions_history")
    op.execute("DROP TABLE IF EXISTS order_slice_executions")

