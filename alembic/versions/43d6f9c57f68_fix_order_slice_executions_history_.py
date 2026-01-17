"""fix_order_slice_executions_history_trigger

Revision ID: 43d6f9c57f68
Revises: 9b5c604ad881
Create Date: 2026-01-17 18:49:38.159576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43d6f9c57f68'
down_revision: Union[str, Sequence[str], None] = '9b5c604ad881'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix order_slice_executions_history trigger to properly insert into history table."""

    # Drop and recreate the trigger function with correct column mapping
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slice_executions_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slice_executions_history (
                    operation, changed_at,
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, broker_order_id, broker_order_status,
                    filled_quantity, average_price, execution_result,
                    placement_attempts, last_attempt_at, last_attempt_error,
                    validation_started_at, placement_confirmed_at, last_broker_poll_at,
                    completed_at, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'DELETE', NOW(),
                    OLD.id, OLD.slice_id, OLD.attempt_id, OLD.executor_id,
                    OLD.executor_claimed_at, OLD.executor_timeout_at, OLD.last_heartbeat_at,
                    OLD.execution_status, OLD.broker_order_id, OLD.broker_order_status,
                    OLD.filled_quantity, OLD.average_price, OLD.execution_result,
                    OLD.placement_attempts, OLD.last_attempt_at, OLD.last_attempt_error,
                    OLD.validation_started_at, OLD.placement_confirmed_at, OLD.last_broker_poll_at,
                    OLD.completed_at, OLD.error_code, OLD.error_message,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slice_executions_history (
                    operation, changed_at,
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, broker_order_id, broker_order_status,
                    filled_quantity, average_price, execution_result,
                    placement_attempts, last_attempt_at, last_attempt_error,
                    validation_started_at, placement_confirmed_at, last_broker_poll_at,
                    completed_at, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'UPDATE', NOW(),
                    OLD.id, OLD.slice_id, OLD.attempt_id, OLD.executor_id,
                    OLD.executor_claimed_at, OLD.executor_timeout_at, OLD.last_heartbeat_at,
                    OLD.execution_status, OLD.broker_order_id, OLD.broker_order_status,
                    OLD.filled_quantity, OLD.average_price, OLD.execution_result,
                    OLD.placement_attempts, OLD.last_attempt_at, OLD.last_attempt_error,
                    OLD.validation_started_at, OLD.placement_confirmed_at, OLD.last_broker_poll_at,
                    OLD.completed_at, OLD.error_code, OLD.error_message,
                    OLD.request_id, OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slice_executions_history (
                    operation, changed_at,
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, broker_order_id, broker_order_status,
                    filled_quantity, average_price, execution_result,
                    placement_attempts, last_attempt_at, last_attempt_error,
                    validation_started_at, placement_confirmed_at, last_broker_poll_at,
                    completed_at, error_code, error_message,
                    request_id, created_at, updated_at
                ) VALUES (
                    'INSERT', NOW(),
                    NEW.id, NEW.slice_id, NEW.attempt_id, NEW.executor_id,
                    NEW.executor_claimed_at, NEW.executor_timeout_at, NEW.last_heartbeat_at,
                    NEW.execution_status, NEW.broker_order_id, NEW.broker_order_status,
                    NEW.filled_quantity, NEW.average_price, NEW.execution_result,
                    NEW.placement_attempts, NEW.last_attempt_at, NEW.last_attempt_error,
                    NEW.validation_started_at, NEW.placement_confirmed_at, NEW.last_broker_poll_at,
                    NEW.completed_at, NEW.error_code, NEW.error_message,
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
        CREATE OR REPLACE FUNCTION order_slice_executions_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slice_executions_history SELECT 'DELETE', NOW(), OLD.*;
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slice_executions_history SELECT 'UPDATE', NOW(), OLD.*;
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slice_executions_history SELECT 'INSERT', NOW(), NEW.*;
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
