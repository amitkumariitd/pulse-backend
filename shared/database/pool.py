"""Database connection pool management."""
import asyncpg
from config.settings import Settings


async def create_pool(settings: Settings) -> asyncpg.Pool:
    """Create database connection pool.
    
    Args:
        settings: Application settings with database configuration
        
    Returns:
        asyncpg connection pool
    """
    return await asyncpg.create_pool(
        host=settings.pulse_db_host,
        port=settings.pulse_db_port,
        user=settings.pulse_db_user,
        password=settings.pulse_db_password,
        database=settings.pulse_db_name,
        min_size=10,
        max_size=20,
        max_queries=50000,
        max_inactive_connection_lifetime=300.0
    )


async def close_pool(pool: asyncpg.Pool):
    """Close database connection pool.
    
    Args:
        pool: Connection pool to close
    """
    await pool.close()

