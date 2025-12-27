-- Database initialization script for pulse-backend
-- This runs automatically when PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE pulse TO pulse;

-- You can add initial schema here or use Alembic migrations
-- For now, this is a placeholder for future schema initialization

