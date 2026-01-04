"""create orders table

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
    """Create orders table with history and triggers."""

    # Create orders table
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
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX idx_orders_order_queue_status ON orders(order_queue_status)")
    op.execute("""
        CREATE INDEX idx_orders_status_created
        ON orders(order_queue_status, created_at)
        WHERE order_queue_status IN ('PENDING', 'IN_PROGRESS')
    """)
    
    # Create history table
    op.execute("""
        CREATE TABLE orders_history (
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
            split_completed_at TIMESTAMPTZ,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
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
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, split_completed_at,
                    trace_id, request_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits,
                    OLD.duration_minutes, OLD.randomize, OLD.order_unique_key, OLD.order_queue_status,
                    OLD.order_queue_skip_reason, OLD.split_completed_at,
                    OLD.trace_id, OLD.request_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, split_completed_at,
                    trace_id, request_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits,
                    OLD.duration_minutes, OLD.randomize, OLD.order_unique_key, OLD.order_queue_status,
                    OLD.order_queue_skip_reason, OLD.split_completed_at,
                    OLD.trace_id, OLD.request_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, split_completed_at,
                    trace_id, request_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.instrument, NEW.side, NEW.total_quantity, NEW.num_splits,
                    NEW.duration_minutes, NEW.randomize, NEW.order_unique_key, NEW.order_queue_status,
                    NEW.order_queue_skip_reason, NEW.split_completed_at,
                    NEW.trace_id, NEW.request_id, NEW.trace_source,
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
        CREATE TRIGGER orders_history_insert
        AFTER INSERT ON orders
        FOR EACH ROW EXECUTE FUNCTION orders_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER orders_history_update
        AFTER UPDATE ON orders
        FOR EACH ROW EXECUTE FUNCTION orders_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER orders_history_delete
        AFTER DELETE ON orders
        FOR EACH ROW EXECUTE FUNCTION orders_history_trigger()
    """)

    # Create trigger function to auto-update updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Create trigger for orders table
    op.execute("""
        CREATE TRIGGER update_orders_updated_at
        BEFORE UPDATE ON orders
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop orders table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS update_orders_updated_at ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_delete ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_update ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_insert ON orders")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.execute("DROP FUNCTION IF EXISTS orders_history_trigger()")
    op.execute("DROP TABLE IF EXISTS orders_history")
    op.execute("DROP TABLE IF EXISTS orders")

