"""create child_orders table

Revision ID: 1767086939
Revises: 1767086831
Create Date: 2024-12-30

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1767086939'
down_revision: Union[str, Sequence[str], None] = '1767086831'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create child_orders table with history and triggers."""
    
    # Create child_orders table
    op.execute("""
        CREATE TABLE child_orders (
            id VARCHAR(64) PRIMARY KEY,
            parent_order_id VARCHAR(64) NOT NULL REFERENCES parent_orders(id) ON DELETE CASCADE,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
            status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED'
                CHECK (status IN ('SCHEDULED', 'READY', 'EXECUTING', 'EXECUTED', 'FAILED', 'SKIPPED')),
            scheduled_at TIMESTAMPTZ NOT NULL,
            execution_started_at TIMESTAMPTZ,
            executed_at TIMESTAMPTZ,
            broker_order_id VARCHAR(255),
            broker_status VARCHAR(50),
            execution_price DECIMAL(18, 4),
            execution_quantity INTEGER,
            failure_reason TEXT,
            retry_count INTEGER DEFAULT 0,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT unique_parent_sequence UNIQUE (parent_order_id, sequence_number)
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX idx_child_orders_parent_order_id ON child_orders(parent_order_id)")
    op.execute("CREATE INDEX idx_child_orders_trace_id ON child_orders(trace_id)")
    op.execute("CREATE INDEX idx_child_orders_request_id ON child_orders(request_id)")
    op.execute("""
        CREATE INDEX idx_child_orders_scheduled 
        ON child_orders(status, scheduled_at) 
        WHERE status = 'SCHEDULED'
    """)
    
    # Create history table
    op.execute("""
        CREATE TABLE child_orders_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
    
    op.execute("CREATE INDEX idx_child_orders_history_id ON child_orders_history(id)")
    op.execute("CREATE INDEX idx_child_orders_history_parent_order_id ON child_orders_history(parent_order_id)")
    op.execute("CREATE INDEX idx_child_orders_history_changed_at ON child_orders_history(changed_at)")
    
    # Create trigger function
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

    # Create triggers
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
    """Drop child_orders table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS child_orders_history_delete ON child_orders")
    op.execute("DROP TRIGGER IF EXISTS child_orders_history_update ON child_orders")
    op.execute("DROP TRIGGER IF EXISTS child_orders_history_insert ON child_orders")
    op.execute("DROP FUNCTION IF EXISTS child_orders_history_trigger()")
    op.execute("DROP TABLE IF EXISTS child_orders_history")
    op.execute("DROP TABLE IF EXISTS child_orders")

