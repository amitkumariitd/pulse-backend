"""remove span_id columns

Revision ID: 1767537848
Revises: 1767086939
Create Date: 2026-01-04

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1767537848'
down_revision: Union[str, Sequence[str], None] = '1767086939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove span_id columns from orders and order_slices tables.

    Note: span_source is kept in RequestContext for logging but not stored in DB.
    Only span_id is removed from database schema.
    """

    # Drop triggers first (they reference the columns)
    op.execute("DROP TRIGGER IF EXISTS orders_history_insert ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_update ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_delete ON orders")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_insert ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_update ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_delete ON order_slices")

    # Drop span_id columns from main tables
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS span_id")
    op.execute("ALTER TABLE order_slices DROP COLUMN IF EXISTS span_id")

    # Drop span_id columns from history tables
    op.execute("ALTER TABLE orders_history DROP COLUMN IF EXISTS span_id")
    op.execute("ALTER TABLE order_slices_history DROP COLUMN IF EXISTS span_id")

    # Recreate orders history trigger function (without span_id)
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

    # Recreate order_slices history trigger function (without span_id)
    op.execute("""
        CREATE OR REPLACE FUNCTION order_slices_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    trace_id, request_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.trace_id, OLD.request_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    trace_id, request_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.order_id, OLD.instrument, OLD.side, OLD.quantity,
                    OLD.sequence_number, OLD.status, OLD.scheduled_at,
                    OLD.trace_id, OLD.request_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO order_slices_history (
                    operation, id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    trace_id, request_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.order_id, NEW.instrument, NEW.side, NEW.quantity,
                    NEW.sequence_number, NEW.status, NEW.scheduled_at,
                    NEW.trace_id, NEW.request_id, NEW.trace_source,
                    NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)




    # Recreate triggers for orders
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

    # Recreate triggers for order_slices
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


def downgrade() -> None:
    """Add span_id columns back to orders and order_slices tables."""

    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS orders_history_insert ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_update ON orders")
    op.execute("DROP TRIGGER IF EXISTS orders_history_delete ON orders")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_insert ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_update ON order_slices")
    op.execute("DROP TRIGGER IF EXISTS order_slices_history_delete ON order_slices")

    # Add span_id columns back to main tables
    op.execute("ALTER TABLE orders ADD COLUMN span_id VARCHAR(16) NOT NULL DEFAULT 's00000000'")
    op.execute("ALTER TABLE order_slices ADD COLUMN span_id VARCHAR(16) NOT NULL DEFAULT 's00000000'")

    # Add span_id columns back to history tables
    op.execute("ALTER TABLE orders_history ADD COLUMN span_id VARCHAR(16) NOT NULL DEFAULT 's00000000'")
    op.execute("ALTER TABLE order_slices_history ADD COLUMN span_id VARCHAR(16) NOT NULL DEFAULT 's00000000'")


    # Recreate orders history trigger function (with span_id)
    op.execute("""
        CREATE OR REPLACE FUNCTION orders_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, split_completed_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'DELETE', OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits,
                    OLD.duration_minutes, OLD.randomize, OLD.order_unique_key, OLD.order_queue_status,
                    OLD.order_queue_skip_reason, OLD.split_completed_at,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, split_completed_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'UPDATE', OLD.id, OLD.instrument, OLD.side, OLD.total_quantity, OLD.num_splits,
                    OLD.duration_minutes, OLD.randomize, OLD.order_unique_key, OLD.order_queue_status,
                    OLD.order_queue_skip_reason, OLD.split_completed_at,
                    OLD.trace_id, OLD.request_id, OLD.span_id, OLD.trace_source,
                    OLD.created_at, OLD.updated_at
                );
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO orders_history (
                    operation, id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key, order_queue_status,
                    order_queue_skip_reason, split_completed_at,
                    trace_id, request_id, span_id, trace_source,
                    created_at, updated_at
                ) VALUES (
                    'INSERT', NEW.id, NEW.instrument, NEW.side, NEW.total_quantity, NEW.num_splits,
                    NEW.duration_minutes, NEW.randomize, NEW.order_unique_key, NEW.order_queue_status,
                    NEW.order_queue_skip_reason, NEW.split_completed_at,
                    NEW.trace_id, NEW.request_id, NEW.span_id, NEW.trace_source,
                    NEW.created_at, NEW.updated_at
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Recreate order_slices history trigger function (with span_id)
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

    # Recreate triggers for orders
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

    # Recreate triggers for order_slices
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

