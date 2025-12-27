-- Example: History table with trigger-based audit trail
-- Every main table MUST have a corresponding history table

-- Main table (from 01-basic-table.sql)
-- CREATE TABLE orders (...);

-- History table (captures all changes)
CREATE TABLE orders_history (
    -- History metadata
    history_id BIGSERIAL PRIMARY KEY,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- All columns from main table
    id VARCHAR(64) NOT NULL,
    instrument VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    
    -- Tracing (from main table)
    trace_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    tracing_source VARCHAR(50) NOT NULL,
    request_source VARCHAR(50) NOT NULL,
    
    -- Timestamps (from main table)
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Indexes for history table
CREATE INDEX idx_orders_history_id ON orders_history(id);
CREATE INDEX idx_orders_history_changed_at ON orders_history(changed_at);

-- Cluster on changed_at for efficient time-based queries
CLUSTER orders_history USING idx_orders_history_changed_at;

-- Note: No index on 'operation' - low cardinality (only 3 values), rarely queried alone

-- Trigger function (captures changes automatically)
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

-- Create triggers (automatically populate history on every change)
CREATE TRIGGER orders_history_insert
    AFTER INSERT ON orders
    FOR EACH ROW
    EXECUTE FUNCTION orders_history_trigger();

CREATE TRIGGER orders_history_update
    AFTER UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION orders_history_trigger();

CREATE TRIGGER orders_history_delete
    AFTER DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION orders_history_trigger();

-- Comments
COMMENT ON TABLE orders_history IS 'Audit trail for orders table - captures all changes';
COMMENT ON COLUMN orders_history.operation IS 'Type of change: INSERT, UPDATE, or DELETE';
COMMENT ON COLUMN orders_history.changed_at IS 'When the change occurred';

