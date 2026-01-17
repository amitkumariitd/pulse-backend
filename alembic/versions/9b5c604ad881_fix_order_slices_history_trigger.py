"""fix_order_slices_history_trigger

Revision ID: 9b5c604ad881
Revises: c395f610b883
Create Date: 2026-01-17 18:47:26.629485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b5c604ad881'
down_revision: Union[str, Sequence[str], None] = 'c395f610b883'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix order_slices_history trigger to match updated schema."""

    # Drop and recreate the trigger function with updated columns
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slices_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at, request_id,
                    created_at, updated_at,
                    order_type, limit_price, product_type, validity,
                    filled_quantity, average_price
                ) VALUES (
                    'DELETE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at, OLD.request_id,
                    OLD.created_at, OLD.updated_at,
                    OLD.order_type, OLD.limit_price, OLD.product_type, OLD.validity,
                    OLD.filled_quantity, OLD.average_price
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at, request_id,
                    created_at, updated_at,
                    order_type, limit_price, product_type, validity,
                    filled_quantity, average_price
                ) VALUES (
                    'UPDATE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at, OLD.request_id,
                    OLD.created_at, OLD.updated_at,
                    OLD.order_type, OLD.limit_price, OLD.product_type, OLD.validity,
                    OLD.filled_quantity, OLD.average_price
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at, request_id,
                    created_at, updated_at,
                    order_type, limit_price, product_type, validity,
                    filled_quantity, average_price
                ) VALUES (
                    'INSERT', NEW.id, NEW.order_id, NEW.instrument, NEW.side, NEW.quantity,
                    NEW.sequence_number, NEW.status, NEW.scheduled_at, NEW.request_id,
                    NEW.created_at, NEW.updated_at,
                    NEW.order_type, NEW.limit_price, NEW.product_type, NEW.validity,
                    NEW.filled_quantity, NEW.average_price
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Restore old trigger function with origin_* columns."""

    op.execute("""
        CREATE OR REPLACE FUNCTION order_slices_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    origin_trace_id, origin_trace_source, origin_request_id, origin_request_source, request_id,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.origin_trace_id, OLD.origin_trace_source, OLD.origin_request_id, OLD.origin_request_source, OLD.request_id,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    origin_trace_id, origin_trace_source, origin_request_id, origin_request_source, request_id,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.origin_trace_id, OLD.origin_trace_source, OLD.origin_request_id, OLD.origin_request_source, OLD.request_id,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    origin_trace_id, origin_trace_source, origin_request_id, origin_request_source, request_id,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.order_id, NEW.instrument, NEW.side, NEW.quantity,
                    NEW.sequence_number, NEW.status, NEW.scheduled_at,
                    NEW.origin_trace_id, NEW.origin_trace_source, NEW.origin_request_id, NEW.origin_request_source, NEW.request_id,
                    NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
