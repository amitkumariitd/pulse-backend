"""create_order_slice_broker_events_table

Revision ID: 1768674603
Revises: 1768674602
Create Date: 2026-01-18 00:00:03

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1768674603'
down_revision: Union[str, Sequence[str], None] = '1768674602'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_slice_broker_events table with history and triggers."""

    # Create order_slice_broker_events table (NOT async-initiating)
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
            event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
            event_timestamp TIMESTAMPTZ NOT NULL,
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
            request_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Create trigger function with explicit column lists
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slice_broker_events_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slice_broker_events_history (
                    operation, changed_at,
                    id, execution_id, slice_id, event_sequence, event_type, event_timestamp,
                    attempt_number, attempt_id, executor_id, broker_name,
                    broker_order_id, request_method, request_endpoint, request_payload,
                    response_status_code, response_body, response_time_ms,
                    broker_status, broker_message, filled_quantity, pending_quantity,
                    average_price, is_success, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'DELETE', NOW(),
                    OLD.id, OLD.execution_id, OLD.slice_id, OLD.event_sequence, OLD.event_type, OLD.event_timestamp,
                    OLD.attempt_number, OLD.attempt_id, OLD.executor_id, OLD.broker_name,
                    OLD.broker_order_id, OLD.request_method, OLD.request_endpoint, OLD.request_payload,
                    OLD.response_status_code, OLD.response_body, OLD.response_time_ms,
                    OLD.broker_status, OLD.broker_message, OLD.filled_quantity, OLD.pending_quantity,
                    OLD.average_price, OLD.is_success, OLD.error_code, OLD.error_message,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slice_broker_events_history (
                    operation, changed_at,
                    id, execution_id, slice_id, event_sequence, event_type, event_timestamp,
                    attempt_number, attempt_id, executor_id, broker_name,
                    broker_order_id, request_method, request_endpoint, request_payload,
                    response_status_code, response_body, response_time_ms,
                    broker_status, broker_message, filled_quantity, pending_quantity,
                    average_price, is_success, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'UPDATE', NOW(),
                    OLD.id, OLD.execution_id, OLD.slice_id, OLD.event_sequence, OLD.event_type, OLD.event_timestamp,
                    OLD.attempt_number, OLD.attempt_id, OLD.executor_id, OLD.broker_name,
                    OLD.broker_order_id, OLD.request_method, OLD.request_endpoint, OLD.request_payload,
                    OLD.response_status_code, OLD.response_body, OLD.response_time_ms,
                    OLD.broker_status, OLD.broker_message, OLD.filled_quantity, OLD.pending_quantity,
                    OLD.average_price, OLD.is_success, OLD.error_code, OLD.error_message,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slice_broker_events_history (
                    operation, changed_at,
                    id, execution_id, slice_id, event_sequence, event_type, event_timestamp,
                    attempt_number, attempt_id, executor_id, broker_name,
                    broker_order_id, request_method, request_endpoint, request_payload,
                    response_status_code, response_body, response_time_ms,
                    broker_status, broker_message, filled_quantity, pending_quantity,
                    average_price, is_success, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'INSERT', NOW(),
                    NEW.id, NEW.execution_id, NEW.slice_id, NEW.event_sequence, NEW.event_type, NEW.event_timestamp,
                    NEW.attempt_number, NEW.attempt_id, NEW.executor_id, NEW.broker_name,
                    NEW.broker_order_id, NEW.request_method, NEW.request_endpoint, NEW.request_payload,
                    NEW.response_status_code, NEW.response_body, NEW.response_time_ms,
                    NEW.broker_status, NEW.broker_message, NEW.filled_quantity, NEW.pending_quantity,
                    NEW.average_price, NEW.is_success, NEW.error_code, NEW.error_message,
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
        CREATE TRIGGER order_slice_broker_events_history_trigger
        AFTER INSERT OR UPDATE OR DELETE ON order_slice_broker_events
        FOR EACH ROW EXECUTE FUNCTION order_slice_broker_events_history_trigger()
    """)


def downgrade() -> None:
    """Drop order_slice_broker_events table, history, and triggers."""
    op.execute("DROP TRIGGER IF EXISTS order_slice_broker_events_history_trigger ON order_slice_broker_events")
    op.execute("DROP FUNCTION IF EXISTS order_slice_broker_events_history_trigger()")
    op.execute("DROP TABLE IF EXISTS order_slice_broker_events_history")
    op.execute("DROP TABLE IF EXISTS order_slice_broker_events")

