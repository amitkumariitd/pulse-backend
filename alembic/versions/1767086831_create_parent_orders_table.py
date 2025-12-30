"""create parent_orders table

Revision ID: 1767086831
Revises: 
Create Date: 2024-12-30

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1767086831'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create parent_orders table with history and triggers."""
    
    # Create parent_orders table
    op.execute("""
        CREATE TABLE parent_orders (
            id VARCHAR(64) PRIMARY KEY,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            total_quantity INTEGER NOT NULL CHECK (total_quantity > 0),
            num_splits INTEGER NOT NULL CHECK (num_splits > 0),
            duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
            randomize BOOLEAN NOT NULL DEFAULT FALSE,
            order_unique_key VARCHAR(255) NOT NULL UNIQUE,
            order_queue_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                CHECK (order_queue_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'SKIPPED')),
            order_queue_skip_reason TEXT,
            total_child_orders INTEGER,
            executed_child_orders INTEGER DEFAULT 0,
            failed_child_orders INTEGER DEFAULT 0,
            skipped_child_orders INTEGER DEFAULT 0,
            filled_quantity INTEGER DEFAULT 0,
            split_completed_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX idx_parent_orders_trace_id ON parent_orders(trace_id)")
    op.execute("CREATE INDEX idx_parent_orders_request_id ON parent_orders(request_id)")
    op.execute("CREATE INDEX idx_parent_orders_order_queue_status ON parent_orders(order_queue_status)")
    op.execute("""
        CREATE INDEX idx_parent_orders_status_created 
        ON parent_orders(order_queue_status, created_at) 
        WHERE order_queue_status IN ('PENDING', 'IN_PROGRESS')
    """)
    
    # Create history table
    op.execute("""
        CREATE TABLE parent_orders_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
    
    op.execute("CREATE INDEX idx_parent_orders_history_id ON parent_orders_history(id)")
    op.execute("CREATE INDEX idx_parent_orders_history_changed_at ON parent_orders_history(changed_at)")
    
    # Create trigger function
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

    # Create triggers
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


def downgrade() -> None:
    """Drop parent_orders table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS parent_orders_history_delete ON parent_orders")
    op.execute("DROP TRIGGER IF EXISTS parent_orders_history_update ON parent_orders")
    op.execute("DROP TRIGGER IF EXISTS parent_orders_history_insert ON parent_orders")
    op.execute("DROP FUNCTION IF EXISTS parent_orders_history_trigger()")
    op.execute("DROP TABLE IF EXISTS parent_orders_history")
    op.execute("DROP TABLE IF EXISTS parent_orders")

