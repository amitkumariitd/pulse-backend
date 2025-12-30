"""Base repository with connection pooling."""
import asyncpg


class BaseRepository:
    """Base repository with connection pooling.
    
    All repositories MUST inherit from this class and use the connection
    management methods to ensure proper pooling and resource cleanup.
    """
    
    def __init__(self, pool: asyncpg.Pool):
        """Initialize repository with connection pool.
        
        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get connection from pool.
        
        Returns:
            Database connection from pool
        """
        return await self.pool.acquire()
    
    async def release_connection(self, conn: asyncpg.Connection):
        """Release connection back to pool.
        
        Args:
            conn: Connection to release
        """
        await self.pool.release(conn)

