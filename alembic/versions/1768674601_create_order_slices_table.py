"""create_order_slices_table

Revision ID: 1768674601
Revises: 1768674600
Create Date: 2026-01-18 00:00:01

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1768674601'
down_revision: Union[str, Sequence[str], None] = '1768674600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_slices table with history and triggers."""

    # Create order_slices table (NOT async-initiating)
    op.execute("""
        CREATE TABLE order_slices (
            id VARCHAR(64) PRIMARY KEY,
            order_id VARCHAR(64) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING', 'EXECUTING', 'COMPLETED', 'CANCELLED', 'SKIPPED')),
            scheduled_at TIMESTAMPTZ NOT NULL,
            order_type VARCHAR(20) DEFAULT 'MARKET' CHECK (order_type IN ('MARKET', 'LIMIT')),
            limit_price DECIMAL(15, 4),
            product_type VARCHAR(20) DEFAULT 'CNC',
            validity VARCHAR(10) DEFAULT 'DAY',
            filled_quantity INTEGER DEFAULT 0 CHECK (filled_quantity >= 0),
            average_price DECIMAL(15, 4),
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT unique_order_sequence UNIQUE (order_id, sequence_number)
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX idx_order_slices_order_id ON order_slices(order_id)")
    op.execute("""
        CREATE INDEX idx_order_slices_status_scheduled
        ON order_slices(status, scheduled_at)
        WHERE status = 'PENDING'
    """)

    # Create history table
    op.execute("""
        CREATE TABLE order_slices_history (
            history_id SERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            id VARCHAR(64) NOT NULL,
            order_id VARCHAR(64) NOT NULL,
            instrument VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            scheduled_at TIMESTAMPTZ NOT NULL,
            order_type VARCHAR(20),
            limit_price DECIMAL(15, 4),
            product_type VARCHAR(20),
            validity VARCHAR(10),
            filled_quantity INTEGER,
            average_price DECIMAL(15, 4),
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    op.execute("CREATE INDEX idx_order_slices_history_id ON order_slices_history(id)")
    op.execute("CREATE INDEX idx_order_slices_history_changed_at ON order_slices_history(changed_at)")

    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slices_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slices_history (
                    operation, changed_at,
                    id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    order_type, limit_price, product_type, validity,
                    filled_quantity, average_price,
                    request_id, created_at, updated_at
                ) VALUES (
                    'DELETE', NOW(),
                    OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.order_type, OLD.limit_price, OLD.product_type, OLD.validity,
                    OLD.filled_quantity, OLD.average_price,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slices_history (
                    operation, changed_at,
                    id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    order_type, limit_price, product_type, validity,
                    filled_quantity, average_price,
                    request_id, created_at, updated_at
                ) VALUES (
                    'UPDATE', NOW(),
                    OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.order_type, OLD.limit_price, OLD.product_type, OLD.validity,
                    OLD.filled_quantity, OLD.average_price,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slices_history (
                    operation, changed_at,
                    id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    order_type, limit_price, product_type, validity,
                    filled_quantity, average_price,
                    request_id, created_at, updated_at
                ) VALUES (
                    'INSERT', NOW(),
                    NEW.id, NEW.order_id, NEW.instrument, NEW.side, NEW.quantity,
                    NEW.sequence_number, NEW.status, NEW.scheduled_at,
                    NEW.order_type, NEW.limit_price, NEW.product_type, NEW.validity,
                    NEW.filled_quantity, NEW.average_price,
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
        CREATE TRIGGER order_slices_history_trigger
        AFTER INSERT OR UPDATE OR DELETE ON order_slices
        FOR EACH ROW EXECUTE FUNCTION order_slices_history_trigger()
    """)


def downgrade() -> None:
    """Drop order_slices table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_trigger ON order_slices")
    op.execute("DROP FUNCTION IF EXISTS order_slices_history_trigger()")
    op.execute("DROP TABLE IF EXISTS order_slices_history")
    op.execute("DROP TABLE IF EXISTS order_slices")

