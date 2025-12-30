"""create order_slices table

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
    """Create order_slices table with history and triggers."""

    # Create order_slices table
    op.execute("""
        CREATE TABLE order_slices (
            id VARCHAR(64) PRIMARY KEY,
            order_id VARCHAR(64) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
            status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED'
                CHECK (status IN ('SCHEDULED', 'READY', 'EXECUTING', 'EXECUTED', 'FAILED', 'SKIPPED')),
            scheduled_at BIGINT NOT NULL,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at BIGINT NOT NULL DEFAULT unix_now_micros(),
            updated_at BIGINT NOT NULL DEFAULT unix_now_micros(),
            CONSTRAINT unique_order_sequence UNIQUE (order_id, sequence_number)
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX idx_order_slices_order_id ON order_slices(order_id)")
    op.execute("""
        CREATE INDEX idx_order_slices_scheduled
        ON order_slices(status, scheduled_at)
        WHERE status = 'SCHEDULED'
    """)
    
    # Create history table
    op.execute("""
        CREATE TABLE order_slices_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at BIGINT NOT NULL DEFAULT unix_now_micros(),
            id VARCHAR(64) NOT NULL,
            order_id VARCHAR(64) NOT NULL,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            scheduled_at BIGINT NOT NULL,
            trace_id VARCHAR(64) NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            trace_source VARCHAR(50) NOT NULL,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        )
    """)
    
    op.execute("CREATE INDEX idx_order_slices_history_id ON order_slices_history(id)")
    op.execute("CREATE INDEX idx_order_slices_history_order_id ON order_slices_history(order_id)")
    op.execute("CREATE INDEX idx_order_slices_history_changed_at ON order_slices_history(changed_at)")
    
    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slices_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.order_id, NEW.instrument, NEW.side, NEW.quantity,
                    NEW.sequence_number, NEW.status, NEW.scheduled_at,
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
        CREATE TRIGGER order_slices_history_insert
        AFTER INSERT ON order_slices
        FOR EACH ROW EXECUTE FUNCTION order_slices_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER order_slices_history_update
        AFTER UPDATE ON order_slices
        FOR EACH ROW EXECUTE FUNCTION order_slices_history_trigger()
    """)
    op.execute("""
        CREATE TRIGGER order_slices_history_delete
        AFTER DELETE ON order_slices
        FOR EACH ROW EXECUTE FUNCTION order_slices_history_trigger()
    """)

    # Create trigger for order_slices table to auto-update updated_at
    op.execute("""
        CREATE TRIGGER update_order_slices_updated_at
        BEFORE UPDATE ON order_slices
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop order_slices table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS update_order_slices_updated_at ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_delete ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_update ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_insert ON order_slices")
    op.execute("DROP FUNCTION IF EXISTS order_slices_history_trigger()")
    op.execute("DROP TABLE IF EXISTS order_slices_history")
    op.execute("DROP TABLE IF EXISTS order_slices")

