"""
Example: Connection pool setup with FastAPI

This shows how to:
- Initialize asyncpg connection pool
- Configure pool settings
- Integrate with FastAPI lifespan
- Use in repositories
"""

import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "pulse"
    postgres_password: str = "pulse"
    postgres_database: str = "pulse"
    
    # Connection pool settings
    pool_min_size: int = 10
    pool_max_size: int = 20
    pool_max_queries: int = 50000
    pool_max_inactive_connection_lifetime: float = 300.0
    
    class Config:
        env_file = ".env"


# Global pool instance
db_pool: asyncpg.Pool = None


async def create_pool(settings: DatabaseSettings) -> asyncpg.Pool:
    """
    Create PostgreSQL connection pool.
    
    Args:
        settings: Database configuration
        
    Returns:
        Connection pool
    """
    return await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_database,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
        max_queries=settings.pool_max_queries,
        max_inactive_connection_lifetime=settings.pool_max_inactive_connection_lifetime,
    )


async def close_pool(pool: asyncpg.Pool):
    """Close connection pool."""
    await pool.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    
    Handles startup and shutdown of database connection pool.
    """
    global db_pool
    
    # Startup
    settings = DatabaseSettings()
    db_pool = await create_pool(settings)
    print(f"Database pool created: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}")
    
    yield
    
    # Shutdown
    await close_pool(db_pool)
    print("Database pool closed")


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)


# Example: Using pool in dependency injection
from fastapi import Depends


def get_db_pool() -> asyncpg.Pool:
    """Dependency to get database pool."""
    return db_pool


# Example: Using in route handler
from pulse.repositories.order_repository import OrderRepository
from pulse.shared.context import RequestContext


@app.post("/orders")
async def create_order(
    order_data: dict,
    ctx: RequestContext = Depends(get_request_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Create order endpoint."""
    repo = OrderRepository(pool)
    result = await repo.create_order(order_data, ctx)
    return result


# Example: Health check endpoint
@app.get("/health")
async def health_check(pool: asyncpg.Pool = Depends(get_db_pool)):
    """Health check with database connectivity test."""
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

