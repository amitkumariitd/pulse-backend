-- Example: Basic table schema with all required columns
-- This is the standard template for creating tables in Pulse

CREATE TABLE orders (
    -- Primary key
    id VARCHAR(64) PRIMARY KEY,
    
    -- Business columns
    instrument VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    
    -- Tracing columns (MANDATORY)
    trace_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,

    -- Timestamp columns (MANDATORY)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes (MANDATORY)
CREATE INDEX idx_orders_trace_id ON orders(trace_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- Comments for documentation
COMMENT ON TABLE orders IS 'Order records with full tracing support';
COMMENT ON COLUMN orders.trace_id IS 'Distributed tracing ID across services';
COMMENT ON COLUMN orders.request_id IS 'Unique request identifier';

