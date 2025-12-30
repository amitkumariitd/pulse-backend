"""Unit tests for OrderRepository."""
import pytest
import asyncpg
from unittest.mock import AsyncMock, MagicMock
from pulse.repositories.order_repository import OrderRepository
from shared.observability.context import RequestContext


@pytest.fixture
def mock_pool():
    """Create a mock connection pool."""
    return MagicMock(spec=asyncpg.Pool)


@pytest.fixture
def mock_conn():
    """Create a mock database connection."""
    conn = AsyncMock(spec=asyncpg.Connection)
    return conn


@pytest.fixture
def request_context():
    """Create a test request context."""
    return RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST:test",
        request_id="r1234567890abcdef1234",
        request_source="TEST:test",
        span_id="s12345678",
        span_source="TEST:test"
    )


@pytest.fixture
def order_repository(mock_pool):
    """Create OrderRepository instance with mock pool."""
    return OrderRepository(mock_pool)


@pytest.mark.asyncio
async def test_create_order_success(order_repository, mock_pool, mock_conn, request_context):
    """Test creating an order successfully."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_order = {
        'id': 'ord_123',
        'instrument': 'NSE:RELIANCE',
        'side': 'BUY',
        'total_quantity': 100,
        'num_splits': 5,
        'duration_minutes': 60,
        'randomize': True,
        'order_unique_key': 'ouk_abc123',
        'order_queue_status': 'PENDING'
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_order)
    
    # Act
    result = await order_repository.create_order(
        order_id='ord_123',
        instrument='NSE:RELIANCE',
        side='BUY',
        total_quantity=100,
        num_splits=5,
        duration_minutes=60,
        randomize=True,
        order_unique_key='ouk_abc123',
        ctx=request_context
    )
    
    # Assert
    assert result == expected_order
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_create_order_duplicate_key(order_repository, mock_pool, mock_conn, request_context):
    """Test creating an order with duplicate unique key raises error."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(side_effect=asyncpg.UniqueViolationError("duplicate key"))
    
    # Act & Assert
    with pytest.raises(asyncpg.UniqueViolationError):
        await order_repository.create_order(
            order_id='ord_123',
            instrument='NSE:RELIANCE',
            side='BUY',
            total_quantity=100,
            num_splits=5,
            duration_minutes=60,
            randomize=True,
            order_unique_key='ouk_duplicate',
            ctx=request_context
        )
    
    # Ensure connection is released even on error
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_order_by_id_found(order_repository, mock_pool, mock_conn, request_context):
    """Test getting an order by ID when it exists."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_order = {'id': 'ord_123', 'instrument': 'NSE:RELIANCE'}
    mock_conn.fetchrow = AsyncMock(return_value=expected_order)
    
    # Act
    result = await order_repository.get_order_by_id('ord_123', request_context)
    
    # Assert
    assert result == expected_order
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_order_by_id_not_found(order_repository, mock_pool, mock_conn, request_context):
    """Test getting an order by ID when it doesn't exist."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    
    # Act
    result = await order_repository.get_order_by_id('ord_nonexistent', request_context)
    
    # Assert
    assert result is None
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_update_order_status_success(order_repository, mock_pool, mock_conn, request_context):
    """Test updating order status successfully."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")
    
    # Act
    result = await order_repository.update_order_status(
        order_id='ord_123',
        new_status='IN_PROGRESS',
        ctx=request_context
    )
    
    # Assert
    assert result is True
    mock_conn.execute.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)

