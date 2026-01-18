"""create_orders_table

Revision ID: 1768674600
Revises:
Create Date: 2026-01-18 00:00:00

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1768674600'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create orders table with history and triggers."""

    # Create orders table (async-initiating)
    op.execute("""
        CREATE TABLE orders (
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
            split_completed_at TIMESTAMPTZ,
            origin_trace_id VARCHAR(64) NOT NULL,
            origin_trace_source VARCHAR(100) NOT NULL,
            origin_request_id VARCHAR(64) NOT NULL,
            origin_request_source VARCHAR(100) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX idx_orders_origin_trace_id ON orders(origin_trace_id)")
    op.execute("CREATE INDEX idx_orders_order_queue_status ON orders(order_queue_status)")
    op.execute("""
        CREATE INDEX idx_orders_queue_pending
        ON orders(order_queue_status, created_at)
        WHERE order_queue_status = 'PENDING'
    """)

    # Create history table
    op.execute("""
        CREATE TABLE orders_history (
            history_id SERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL,
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
            split_completed_at TIMESTAMPTZ,
            origin_trace_id VARCHAR(64) NOT NULL,
            origin_trace_source VARCHAR(100) NOT NULL,
            origin_request_id VARCHAR(64) NOT NULL,
            origin_request_source VARCHAR(100) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    op.execute("CREATE INDEX idx_orders_history_id ON orders_history(id)")
    op.execute("CREATE INDEX idx_orders_history_changed_at ON orders_history(changed_at)")

    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION orders_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO orders_history (
                    operation, changed_at,
                    id, instrument, side, total_quantity, num_splits, duration_minutes,
                    randomize, order_unique_key, order_queue_status, order_queue_skip_reason,
                    split_completed_at, origin_trace_id, origin_trace_source,
                    origin_request_id, origin_request_source, request_id, created_at, updated_at
                ) VALUES (
                    'DELETE', NOW(),
                    OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits, OLD.duration_minutes,
                    OLD.randomize, OLD.order_unique_key, OLD.order_queue_status, OLD.order_queue_skip_reason,
                    OLD.split_completed_at, OLD.origin_trace_id, OLD.origin_trace_source,
                    OLD.origin_request_id, OLD.origin_request_source, OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO orders_history (
                    operation, changed_at,
                    id, instrument, side, total_quantity, num_splits, duration_minutes,
                    randomize, order_unique_key, order_queue_status, order_queue_skip_reason,
                    split_completed_at, origin_trace_id, origin_trace_source,
                    origin_request_id, origin_request_source, request_id, created_at, updated_at
                ) VALUES (
                    'UPDATE', NOW(),
                    OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits, OLD.duration_minutes,
                    OLD.randomize, OLD.order_unique_key, OLD.order_queue_status, OLD.order_queue_skip_reason,
                    OLD.split_completed_at, OLD.origin_trace_id, OLD.origin_trace_source,
                    OLD.origin_request_id, OLD.origin_request_source, OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO orders_history (
                    operation, changed_at,
                    id, instrument, side, total_quantity, num_splits, duration_minutes,
                    randomize, order_unique_key, order_queue_status, order_queue_skip_reason,
                    split_completed_at, origin_trace_id, origin_trace_source,
                    origin_request_id, origin_request_source, request_id, created_at, updated_at
                ) VALUES (
                    'INSERT', NOW(),
                    NEW.id, NEW.instrument, NEW.side, NEW.total_quantity, NEW.num_splits, NEW.duration_minutes,
                    NEW.randomize, NEW.order_unique_key, NEW.order_queue_status, NEW.order_queue_skip_reason,
                    NEW.split_completed_at, NEW.origin_trace_id, NEW.origin_trace_source,
                    NEW.origin_request_id, NEW.origin_request_source, NEW.request_id, NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)




    # Create triggers
    op.execute("""
        CREATE TRIGGER orders_history_trigger
        AFTER INSERT OR UPDATE OR DELETE ON orders
        FOR EACH ROW EXECUTE FUNCTION orders_history_trigger()
    """)


def downgrade() -> None:
    """Drop orders table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS orders_history_trigger ON orders")
    op.execute("DROP FUNCTION IF EXISTS orders_history_trigger()")
    op.execute("DROP TABLE IF EXISTS orders_history")
    op.execute("DROP TABLE IF EXISTS orders")
