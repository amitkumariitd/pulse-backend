"""fix_broker_events_history_trigger

Revision ID: 059c0b8ba88c
Revises: 43d6f9c57f68
Create Date: 2026-01-17 18:51:02.453841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '059c0b8ba88c'
down_revision: Union[str, Sequence[str], None] = '43d6f9c57f68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix order_slice_broker_events_history trigger to properly insert into history table."""

    # Drop and recreate the trigger function with correct column mapping
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


def downgrade() -> None:
    """Restore old trigger function."""

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
