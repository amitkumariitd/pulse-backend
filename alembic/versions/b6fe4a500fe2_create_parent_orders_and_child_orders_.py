"""create parent_orders and child_orders tables

Revision ID: b6fe4a500fe2
Revises: 
Create Date: 2025-12-29 22:50:16.486902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6fe4a500fe2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ========================================
    # 1. Create parent_orders table
    # ========================================
    op.execute("""
        CREATE TABLE parent_orders (
            -- Primary key
            id VARCHAR(64) PRIMARY KEY,

            -- Business columns
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            total_quantity INTEGER NOT NULL CHECK (total_quantity > 0),
            num_splits INTEGER NOT NULL CHECK (num_splits >= 2 AND num_splits <= 100),
            duration_minutes INTEGER NOT NULL CHECK (duration_minutes >= 1 AND duration_minutes <= 1440),
            randomize BOOLEAN NOT NULL DEFAULT true,
            order_unique_key VARCHAR(255) NOT NULL UNIQUE,

            -- Order queue tracking (splitting lifecycle)
            order_queue_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                CHECK (order_queue_status IN ('PENDING', 'IN_PROGRESS', 'DONE', 'SKIPPED')),
            order_queue_skip_reason TEXT,

            -- Execution metrics (derived from child orders)
            total_child_orders INTEGER DEFAULT 0,
            executed_child_orders INTEGER DEFAULT 0,
            failed_child_orders INTEGER DEFAULT 0,
            skipped_child_orders INTEGER DEFAULT 0,
            filled_quantity INTEGER DEFAULT 0,

            -- Timing
            split_completed_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,

            -- Tracing columns (async-initiating table)
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,

            -- Standard timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes for parent_orders
    op.execute("CREATE INDEX idx_parent_orders_trace_id ON parent_orders(trace_id)")
    op.execute("CREATE INDEX idx_parent_orders_request_id ON parent_orders(request_id)")
    op.execute("CREATE INDEX idx_parent_orders_order_unique_key ON parent_orders(order_unique_key)")
    op.execute("""
        CREATE INDEX idx_parent_orders_status_created
        ON parent_orders(order_queue_status, created_at)
        WHERE order_queue_status IN ('PENDING', 'IN_PROGRESS')
    """)

    # ========================================
    # 2. Create parent_orders_history table
    # ========================================
    op.execute("""
        CREATE TABLE parent_orders_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- All columns from parent_orders
            id VARCHAR(64) NOT NULL,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL,
            total_quantity INTEGER NOT NULL,
            num_splits INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL,
            randomize BOOLEAN NOT NULL,
            order_unique_key VARCHAR(255) NOT NULL,
            order_queue_status VARCHAR(20) NOT NULL,
            order_queue_skip_reason TEXT,
            total_child_orders INTEGER,
            executed_child_orders INTEGER,
            failed_child_orders INTEGER,
            skipped_child_orders INTEGER,
            filled_quantity INTEGER,
            split_completed_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Create indexes for history table
    op.execute("CREATE INDEX idx_parent_orders_history_id ON parent_orders_history(id)")
    op.execute("CREATE INDEX idx_parent_orders_history_changed_at ON parent_orders_history(changed_at)")

    # ========================================
    # 3. Create trigger function for parent_orders_history
    # ========================================
    op.execute("""
        CREATE OR REPLACE FUNCTION parent_orders_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO parent_orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, total_child_orders, executed_child_orders,
                    failed_child_orders, skipped_child_orders, filled_quantity,
                    split_completed_at, expires_at, completed_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits,
                    OLD.duration_minutes, OLD.randomize, OLD.order_unique_key, OLD.order_queue_status,
                    OLD.order_queue_skip_reason, OLD.total_child_orders, OLD.executed_child_orders,
                    OLD.failed_child_orders, OLD.skipped_child_orders, OLD.filled_quantity,
                    OLD.split_completed_at, OLD.expires_at, OLD.completed_at,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO parent_orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, total_child_orders, executed_child_orders,
                    failed_child_orders, skipped_child_orders, filled_quantity,
                    split_completed_at, expires_at, completed_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits,
                    OLD.duration_minutes, OLD.randomize, OLD.order_unique_key, OLD.order_queue_status,
                    OLD.order_queue_skip_reason, OLD.total_child_orders, OLD.executed_child_orders,
                    OLD.failed_child_orders, OLD.skipped_child_orders, OLD.filled_quantity,
                    OLD.split_completed_at, OLD.expires_at, OLD.completed_at,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO parent_orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, total_child_orders, executed_child_orders,
                    failed_child_orders, skipped_child_orders, filled_quantity,
                    split_completed_at, expires_at, completed_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.instrument, NEW.side, NEW.total_quantity, NEW.num_splits,
                    NEW.duration_minutes, NEW.randomize, NEW.order_unique_key, NEW.order_queue_status,
                    NEW.order_queue_skip_reason, NEW.total_child_orders, NEW.executed_child_orders,
                    NEW.failed_child_orders, NEW.skipped_child_orders, NEW.filled_quantity,
                    NEW.split_completed_at, NEW.expires_at, NEW.completed_at,
                    NEW.trace_id, NEW.request_id, NEW.span_id, NEW.trace_source,
                    NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers for parent_orders
    op.execute("""
        CREATE TRIGGER parent_orders_history_insert
        AFTER INSERT ON parent_orders
        FOR EACH ROW EXECUTE FUNCTION parent_orders_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER parent_orders_history_update
        AFTER UPDATE ON parent_orders
        FOR EACH ROW EXECUTE FUNCTION parent_orders_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER parent_orders_history_delete
        AFTER DELETE ON parent_orders
        FOR EACH ROW EXECUTE FUNCTION parent_orders_history_trigger()
    """)

    # ========================================
    # 4. Create child_orders table
    # ========================================
    op.execute("""
        CREATE TABLE child_orders (
            -- Primary key
            id VARCHAR(64) PRIMARY KEY,

            -- Parent reference
            parent_order_id VARCHAR(64) NOT NULL REFERENCES parent_orders(id) ON DELETE CASCADE,

            -- Business columns (inherited from parent)
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),

            -- Execution status
            status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED'
                CHECK (status IN ('SCHEDULED', 'READY', 'EXECUTING', 'EXECUTED', 'FAILED', 'SKIPPED')),

            -- Scheduling
            scheduled_at TIMESTAMPTZ NOT NULL,
            execution_started_at TIMESTAMPTZ,
            executed_at TIMESTAMPTZ,

            -- Broker integration
            broker_order_id VARCHAR(255),
            broker_status VARCHAR(50),
            execution_price DECIMAL(18, 4),
            execution_quantity INTEGER,

            -- Error tracking
            failure_reason TEXT,
            retry_count INTEGER DEFAULT 0,

            -- Tracing columns (async-initiating table)
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,

            -- Standard timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Unique constraint: prevent duplicate sequence numbers per parent
            CONSTRAINT unique_parent_sequence UNIQUE (parent_order_id, sequence_number)
        )
    """)

    # Create indexes for child_orders
    op.execute("CREATE INDEX idx_child_orders_parent_order_id ON child_orders(parent_order_id)")
    op.execute("CREATE INDEX idx_child_orders_trace_id ON child_orders(trace_id)")
    op.execute("CREATE INDEX idx_child_orders_request_id ON child_orders(request_id)")
    op.execute("""
        CREATE INDEX idx_child_orders_scheduled
        ON child_orders(status, scheduled_at)
        WHERE status = 'SCHEDULED'
    """)

    # ========================================
    # 5. Create child_orders_history table
    # ========================================
    op.execute("""
        CREATE TABLE child_orders_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- All columns from child_orders
            id VARCHAR(64) NOT NULL,
            parent_order_id VARCHAR(64) NOT NULL,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            scheduled_at TIMESTAMPTZ NOT NULL,
            execution_started_at TIMESTAMPTZ,
            executed_at TIMESTAMPTZ,
            broker_order_id VARCHAR(255),
            broker_status VARCHAR(50),
            execution_price DECIMAL(18, 4),
            execution_quantity INTEGER,
            failure_reason TEXT,
            retry_count INTEGER,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Create indexes for history table
    op.execute("CREATE INDEX idx_child_orders_history_id ON child_orders_history(id)")
    op.execute("CREATE INDEX idx_child_orders_history_parent_order_id ON child_orders_history(parent_order_id)")
    op.execute("CREATE INDEX idx_child_orders_history_changed_at ON child_orders_history(changed_at)")

    # ========================================
    # 6. Create trigger function for child_orders_history
    # ========================================
    op.execute("""
        CREATE OR REPLACE FUNCTION child_orders_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO child_orders_history (
                    operation, id, parent_order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at, execution_started_at,
                    executed_at, broker_order_id, broker_status, execution_price,
                    execution_quantity, failure_reason, retry_count,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.parent_order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at, OLD.execution_started_at,
                    OLD.executed_at, OLD.broker_order_id, OLD.broker_status, OLD.execution_price,
                    OLD.execution_quantity, OLD.failure_reason, OLD.retry_count,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO child_orders_history (
                    operation, id, parent_order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at, execution_started_at,
                    executed_at, broker_order_id, broker_status, execution_price,
                    execution_quantity, failure_reason, retry_count,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.parent_order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at, OLD.execution_started_at,
                    OLD.executed_at, OLD.broker_order_id, OLD.broker_status, OLD.execution_price,
                    OLD.execution_quantity, OLD.failure_reason, OLD.retry_count,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO child_orders_history (
                    operation, id, parent_order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at, execution_started_at,
                    executed_at, broker_order_id, broker_status, execution_price,
                    execution_quantity, failure_reason, retry_count,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.parent_order_id, NEW.instrument, NEW.side, NEW.quantity,
                    NEW.sequence_number, NEW.status, NEW.scheduled_at, NEW.execution_started_at,
                    NEW.executed_at, NEW.broker_order_id, NEW.broker_status, NEW.execution_price,
                    NEW.execution_quantity, NEW.failure_reason, NEW.retry_count,
                    NEW.trace_id, NEW.request_id, NEW.span_id, NEW.trace_source,
                    NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers for child_orders
    op.execute("""
        CREATE TRIGGER child_orders_history_insert
        AFTER INSERT ON child_orders
        FOR EACH ROW EXECUTE FUNCTION child_orders_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER child_orders_history_update
        AFTER UPDATE ON child_orders
        FOR EACH ROW EXECUTE FUNCTION child_orders_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER child_orders_history_delete
        AFTER DELETE ON child_orders
        FOR EACH ROW EXECUTE FUNCTION child_orders_history_trigger()
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop child_orders triggers
    op.execute("DROP TRIGGER IF EXISTS child_orders_history_delete ON child_orders")
    op.execute("DROP TRIGGER IF EXISTS child_orders_history_update ON child_orders")
    op.execute("DROP TRIGGER IF EXISTS child_orders_history_insert ON child_orders")

    # Drop child_orders trigger function
    op.execute("DROP FUNCTION IF EXISTS child_orders_history_trigger()")

    # Drop child_orders history table
    op.execute("DROP TABLE IF EXISTS child_orders_history")

    # Drop child_orders table
    op.execute("DROP TABLE IF EXISTS child_orders")

    # Drop parent_orders triggers
    op.execute("DROP TRIGGER IF EXISTS parent_orders_history_delete ON parent_orders")
    op.execute("DROP TRIGGER IF EXISTS parent_orders_history_update ON parent_orders")
    op.execute("DROP TRIGGER IF EXISTS parent_orders_history_insert ON parent_orders")

    # Drop parent_orders trigger function
    op.execute("DROP FUNCTION IF EXISTS parent_orders_history_trigger()")

    # Drop parent_orders history table
    op.execute("DROP TABLE IF EXISTS parent_orders_history")

    # Drop parent_orders table
    op.execute("DROP TABLE IF EXISTS parent_orders")
