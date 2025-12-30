"""Integration tests for database connection pool."""
import pytest
import asyncpg
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings


@pytest.mark.asyncio
async def test_create_pool_success():
    """Test creating database connection pool."""
    # Arrange
    settings = get_settings()
    
    # Act
    pool = await create_pool(settings)
    
    # Assert
    assert pool is not None
    assert isinstance(pool, asyncpg.Pool)
    
    # Cleanup
    await close_pool(pool)


@pytest.mark.asyncio
async def test_pool_can_acquire_connection():
    """Test acquiring connection from pool."""
    # Arrange
    settings = get_settings()
    pool = await create_pool(settings)
    
    try:
        # Act
        conn = await pool.acquire()
        
        # Assert
        assert conn is not None
        assert isinstance(conn, asyncpg.Connection)
        
        # Test simple query
        result = await conn.fetchval("SELECT 1")
        assert result == 1
        
        # Release connection
        await pool.release(conn)
    finally:
        # Cleanup
        await close_pool(pool)


@pytest.mark.asyncio
async def test_pool_can_execute_query():
    """Test executing query through pool."""
    # Arrange
    settings = get_settings()
    pool = await create_pool(settings)
    
    try:
        # Act
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1 + 1")
        
        # Assert
        assert result == 2
    finally:
        # Cleanup
        await close_pool(pool)


@pytest.mark.asyncio
async def test_pool_multiple_connections():
    """Test acquiring multiple connections from pool."""
    # Arrange
    settings = get_settings()
    pool = await create_pool(settings)
    
    try:
        # Act - acquire multiple connections
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()
        
        # Assert
        assert conn1 is not None
        assert conn2 is not None
        assert conn1 != conn2  # Different connections
        
        # Both can execute queries
        result1 = await conn1.fetchval("SELECT 1")
        result2 = await conn2.fetchval("SELECT 2")
        
        assert result1 == 1
        assert result2 == 2
        
        # Release connections
        await pool.release(conn1)
        await pool.release(conn2)
    finally:
        # Cleanup
        await close_pool(pool)

