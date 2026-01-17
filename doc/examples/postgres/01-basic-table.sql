-- Example: Async-initiating table (spawns async work)
-- This table triggers background processing, so it needs full tracing context

CREATE TABLE orders (
    -- Primary key
    id VARCHAR(64) PRIMARY KEY,

    -- Business columns
    instrument VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    -- Tracing columns (MANDATORY for async-initiating tables)
    origin_trace_id VARCHAR(64) NOT NULL,
    origin_trace_source VARCHAR(100) NOT NULL,
    origin_request_id VARCHAR(64) NOT NULL,
    origin_request_source VARCHAR(100) NOT NULL,
    request_id VARCHAR(64) NOT NULL,

    -- Timestamp columns (MANDATORY)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes (MANDATORY)
CREATE INDEX idx_orders_origin_trace_id ON orders(origin_trace_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- Comments for documentation
COMMENT ON TABLE orders IS 'Async-initiating table - spawns background order processing';
COMMENT ON COLUMN orders.origin_trace_id IS 'Trace ID that created this order';
COMMENT ON COLUMN orders.origin_trace_source IS 'Where the trace originated (e.g., GAPI:POST/api/orders)';
COMMENT ON COLUMN orders.origin_request_id IS 'Request ID that created this order';
COMMENT ON COLUMN orders.origin_request_source IS 'Where the request originated (e.g., GAPI:POST/api/orders)';
COMMENT ON COLUMN orders.request_id IS 'Request ID for async workers to use';

---

-- Example: Regular table (does not spawn async work)
-- This table only needs request_id for tracking

CREATE TABLE order_slices (
    -- Primary key
    id VARCHAR(64) PRIMARY KEY,

    -- Foreign key
    order_id VARCHAR(64) NOT NULL REFERENCES orders(id),

    -- Business columns
    slice_number INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',

    -- Tracing columns (MANDATORY for all tables)
    request_id VARCHAR(64) NOT NULL,

    -- Timestamp columns (MANDATORY)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_order_slices_order_id ON order_slices(order_id);
CREATE INDEX idx_order_slices_created_at ON order_slices(created_at);

-- Comments
COMMENT ON TABLE order_slices IS 'Regular table - created during async processing, does not spawn new async work';
COMMENT ON COLUMN order_slices.request_id IS 'Request that created this slice';

