"""
Example: Alembic migration for creating orders table with history

This shows the complete migration including:
- Main table creation
- Indexes
- History table creation
- Trigger function
- Triggers

Usage:
    alembic revision -m "create orders table"
    # Copy this code into the generated migration file
    alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Create main table
    op.execute("""
        CREATE TABLE orders (
            id VARCHAR(64) PRIMARY KEY,
            instrument VARCHAR(50) NOT NULL,
            quantity INTEGER NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT')),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            tracing_source VARCHAR(50) NOT NULL,
            request_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes for main table
    op.execute("CREATE INDEX idx_orders_trace_id ON orders(trace_id)")
    op.execute("CREATE INDEX idx_orders_created_at ON orders(created_at)")
    op.execute("CREATE INDEX idx_orders_status ON orders(status)")

    # Create history table
    op.execute("""
        CREATE TABLE orders_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            id VARCHAR(64) NOT NULL,
            instrument VARCHAR(50) NOT NULL,
            quantity INTEGER NOT NULL,
            side VARCHAR(10) NOT NULL,
            order_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            tracing_source VARCHAR(50) NOT NULL,
            request_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Create indexes for history table
    op.execute("CREATE INDEX idx_orders_history_id ON orders_history(id)")
    op.execute("CREATE INDEX idx_orders_history_changed_at ON orders_history(changed_at)")

    # Cluster history table on changed_at for efficient time-based queries
    op.execute("CLUSTER orders_history USING idx_orders_history_changed_at")

    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION orders_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO orders_history (
                    operation, changed_at,
                    id, instrument, quantity, side, order_type, status,
                    trace_id, request_id, tracing_source, request_source,
                    created_at, updated_at
                )
                VALUES (
                    'DELETE', NOW(),
                    OLD.id, OLD.instrument, OLD.quantity, OLD.side, OLD.order_type, OLD.status,
                    OLD.trace_id, OLD.request_id, OLD.tracing_source, OLD.request_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO orders_history (
                    operation, changed_at,
                    id, instrument, quantity, side, order_type, status,
                    trace_id, request_id, tracing_source, request_source,
                    created_at, updated_at
                )
                VALUES (
                    'UPDATE', NOW(),
                    OLD.id, OLD.instrument, OLD.quantity, OLD.side, OLD.order_type, OLD.status,
                    OLD.trace_id, OLD.request_id, OLD.tracing_source, OLD.request_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO orders_history (
                    operation, changed_at,
                    id, instrument, quantity, side, order_type, status,
                    trace_id, request_id, tracing_source, request_source,
                    created_at, updated_at
                )
                VALUES (
                    'INSERT', NOW(),
                    NEW.id, NEW.instrument, NEW.quantity, NEW.side, NEW.order_type, NEW.status,
                    NEW.trace_id, NEW.request_id, NEW.tracing_source, NEW.request_source,
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
            FOR EACH ROW
            EXECUTE FUNCTION orders_history_trigger()
    """)

    op.execute("""
        CREATE TRIGGER orders_history_update
            AFTER UPDATE ON orders
            FOR EACH ROW
            EXECUTE FUNCTION orders_history_trigger()
    """)

    op.execute("""
        CREATE TRIGGER orders_history_delete
            AFTER DELETE ON orders
            FOR EACH ROW
            EXECUTE FUNCTION orders_history_trigger()
    """)





def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS orders_history_delete ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_update ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_insert ON orders")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS orders_history_trigger()")

    # Drop history table
    op.execute("DROP TABLE IF EXISTS orders_history")

    # Drop main table
    op.execute("DROP TABLE IF EXISTS orders")
