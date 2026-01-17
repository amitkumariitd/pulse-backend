"""create_order_slice_broker_events_table

Revision ID: c395f610b883
Revises: 53b0b9b95498
Create Date: 2026-01-17 18:19:37.480520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c395f610b883'
down_revision: Union[str, Sequence[str], None] = '53b0b9b95498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_slice_broker_events table for audit trail of broker interactions."""

    # Create order_slice_broker_events table
    op.execute("""
        CREATE TABLE order_slice_broker_events (
            -- Identity
            id VARCHAR(64) PRIMARY KEY,
            execution_id VARCHAR(64) NOT NULL REFERENCES order_slice_executions(id) ON DELETE CASCADE,
            slice_id VARCHAR(64) NOT NULL REFERENCES order_slices(id) ON DELETE CASCADE,

            -- Event metadata
            event_sequence INTEGER NOT NULL CHECK (event_sequence > 0),
            event_type VARCHAR(30) NOT NULL
                CHECK (event_type IN ('PLACE_ORDER', 'STATUS_POLL', 'CANCEL_REQUEST')),
            attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),

            -- Execution context
            attempt_id VARCHAR(100) NOT NULL,
            executor_id VARCHAR(100) NOT NULL,

            -- Broker interaction
            broker_name VARCHAR(50) NOT NULL,
            broker_order_id VARCHAR(100),

            -- Request details
            request_method VARCHAR(10),
            request_endpoint VARCHAR(200),
            request_payload JSONB,

            -- Response details
            response_status_code INTEGER,
            response_body JSONB,
            response_time_ms INTEGER,

            -- Parsed broker data
            broker_status VARCHAR(50),
            broker_message TEXT,
            filled_quantity INTEGER,
            pending_quantity INTEGER,
            average_price DECIMAL(15, 4),

            -- Result
            is_success BOOLEAN NOT NULL,
            error_code VARCHAR(50),
            error_message TEXT,

            -- Timing
            event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Tracing
            request_id VARCHAR(64) NOT NULL,

            -- Timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT unique_execution_event_sequence UNIQUE (execution_id, event_sequence)
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX idx_broker_events_execution_id ON order_slice_broker_events(execution_id)")
    op.execute("CREATE INDEX idx_broker_events_slice_id ON order_slice_broker_events(slice_id)")
    op.execute("CREATE INDEX idx_broker_events_attempt_id ON order_slice_broker_events(attempt_id)")
    op.execute("CREATE INDEX idx_broker_events_attempt_num ON order_slice_broker_events(execution_id, attempt_number)")

    # Create history table
    op.execute("""
        CREATE TABLE order_slice_broker_events_history (
            history_id BIGSERIAL PRIMARY KEY,
            operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            id VARCHAR(64) NOT NULL,
            execution_id VARCHAR(64) NOT NULL,
            slice_id VARCHAR(64) NOT NULL,
            event_sequence INTEGER NOT NULL,
            event_type VARCHAR(30) NOT NULL,
            attempt_number INTEGER NOT NULL,
            attempt_id VARCHAR(100) NOT NULL,
            executor_id VARCHAR(100) NOT NULL,
            broker_name VARCHAR(50) NOT NULL,
            broker_order_id VARCHAR(100),
            request_method VARCHAR(10),
            request_endpoint VARCHAR(200),
            request_payload JSONB,
            response_status_code INTEGER,
            response_body JSONB,
            response_time_ms INTEGER,
            broker_status VARCHAR(50),
            broker_message TEXT,
            filled_quantity INTEGER,
            pending_quantity INTEGER,
            average_price DECIMAL(15, 4),
            is_success BOOLEAN NOT NULL,
            error_code VARCHAR(50),
            error_message TEXT,
            event_timestamp TIMESTAMPTZ NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Create trigger function for history
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slice_broker_events_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slice_broker_events_history SELECT 'DELETE', NOW(), OLD.*;
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slice_broker_events_history SELECT 'UPDATE', NOW(), OLD.*;
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slice_broker_events_history SELECT 'INSERT', NOW(), NEW.*;
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER order_slice_broker_events_history_insert
        AFTER INSERT ON order_slice_broker_events
        FOR EACH ROW EXECUTE FUNCTION order_slice_broker_events_history_trigger()
    """)

    op.execute("""
        CREATE TRIGGER order_slice_broker_events_history_update
        AFTER UPDATE ON order_slice_broker_events
        FOR EACH ROW EXECUTE FUNCTION order_slice_broker_events_history_trigger()
    """)

    op.execute("""
        CREATE TRIGGER order_slice_broker_events_history_delete
        AFTER DELETE ON order_slice_broker_events
        FOR EACH ROW EXECUTE FUNCTION order_slice_broker_events_history_trigger()
    """)


def downgrade() -> None:
    """Drop order_slice_broker_events table."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS order_slice_broker_events_history_delete ON order_slice_broker_events")
    op.execute("DROP TRIGGER IF EXISTS order_slice_broker_events_history_update ON order_slice_broker_events")
    op.execute("DROP TRIGGER IF EXISTS order_slice_broker_events_history_insert ON order_slice_broker_events")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS order_slice_broker_events_history_trigger()")

    # Drop history table
    op.execute("DROP TABLE IF EXISTS order_slice_broker_events_history")

    # Drop main table (indexes will be dropped automatically)
    op.execute("DROP TABLE IF EXISTS order_slice_broker_events")
