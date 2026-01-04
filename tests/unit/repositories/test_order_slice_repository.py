"""Unit tests for OrderSliceRepository."""
import pytest
import asyncpg
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from pulse.repositories.order_slice_repository import OrderSliceRepository
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
        span_source="TEST:test"
    )


@pytest.fixture
def order_slice_repository(mock_pool):
    """Create OrderSliceRepository instance with mock pool."""
    return OrderSliceRepository(mock_pool)


@pytest.mark.asyncio
async def test_create_order_slice_success(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test creating an order slice successfully."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    scheduled_at = datetime(2025, 12, 30, 10, 0, 0, tzinfo=timezone.utc)
    expected_slice = {
        'id': 'slice_123',
        'order_id': 'ord_123',
        'instrument': 'NSE:RELIANCE',
        'side': 'BUY',
        'quantity': 20,
        'sequence_number': 1,
        'status': 'SCHEDULED',
        'scheduled_at': scheduled_at
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_slice)
    
    # Act
    result = await order_slice_repository.create_order_slice(
        slice_id='slice_123',
        order_id='ord_123',
        instrument='NSE:RELIANCE',
        side='BUY',
        quantity=20,
        sequence_number=1,
        scheduled_at=scheduled_at,
        ctx=request_context
    )
    
    # Assert
    assert result == expected_slice
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_create_order_slice_duplicate_sequence(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test creating an order slice with duplicate sequence number raises error."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(side_effect=asyncpg.UniqueViolationError("duplicate sequence"))
    
    scheduled_at = datetime(2025, 12, 30, 10, 0, 0, tzinfo=timezone.utc)
    
    # Act & Assert
    with pytest.raises(asyncpg.UniqueViolationError):
        await order_slice_repository.create_order_slice(
            slice_id='slice_123',
            order_id='ord_123',
            instrument='NSE:RELIANCE',
            side='BUY',
            quantity=20,
            sequence_number=1,
            scheduled_at=scheduled_at,
            ctx=request_context
        )
    
    # Ensure connection is released even on error
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_create_order_slices_batch_success(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test creating multiple order slices in batch."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    # Mock transaction context manager
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock()
    mock_transaction.__aexit__ = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=mock_transaction)
    mock_conn.execute = AsyncMock()
    
    scheduled_at = datetime(2025, 12, 30, 10, 0, 0, tzinfo=timezone.utc)
    slices = [
        {
            'id': 'slice_1',
            'order_id': 'ord_123',
            'instrument': 'NSE:RELIANCE',
            'side': 'BUY',
            'quantity': 20,
            'sequence_number': 1,
            'scheduled_at': scheduled_at
        },
        {
            'id': 'slice_2',
            'order_id': 'ord_123',
            'instrument': 'NSE:RELIANCE',
            'side': 'BUY',
            'quantity': 22,
            'sequence_number': 2,
            'scheduled_at': scheduled_at
        }
    ]
    
    # Act
    result = await order_slice_repository.create_order_slices_batch(slices, request_context)
    
    # Assert
    assert result == 2
    assert mock_conn.execute.call_count == 2
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_slices_by_order_id_success(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test getting all slices for a parent order."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_slices = [
        {'id': 'slice_1', 'order_id': 'ord_123', 'sequence_number': 1},
        {'id': 'slice_2', 'order_id': 'ord_123', 'sequence_number': 2}
    ]
    mock_conn.fetch = AsyncMock(return_value=expected_slices)
    
    # Act
    result = await order_slice_repository.get_slices_by_order_id('ord_123', request_context)
    
    # Assert
    assert result == expected_slices
    mock_conn.fetch.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_slice_by_id_found(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test getting an order slice by ID when it exists."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    expected_slice = {'id': 'slice_123', 'order_id': 'ord_123', 'quantity': 20}
    mock_conn.fetchrow = AsyncMock(return_value=expected_slice)

    # Act
    result = await order_slice_repository.get_slice_by_id('slice_123', request_context)

    # Assert
    assert result == expected_slice
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_slice_by_id_not_found(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test getting an order slice by ID when it doesn't exist."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)

    # Act
    result = await order_slice_repository.get_slice_by_id('slice_nonexistent', request_context)

    # Assert
    assert result is None
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_update_slice_status_success(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test updating order slice status successfully."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    # Act
    result = await order_slice_repository.update_slice_status(
        slice_id='slice_123',
        new_status='IN_PROGRESS',
        ctx=request_context
    )

    # Assert
    assert result is True
    mock_conn.execute.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_update_slice_status_not_found(order_slice_repository, mock_pool, mock_conn, request_context):
    """Test updating order slice status when slice doesn't exist."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 0")

    # Act
    result = await order_slice_repository.update_slice_status(
        slice_id='slice_nonexistent',
        new_status='IN_PROGRESS',
        ctx=request_context
    )

    # Assert
    assert result is False
    mock_pool.release.assert_called_once_with(mock_conn)

