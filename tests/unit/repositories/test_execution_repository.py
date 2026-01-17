"""Unit tests for ExecutionRepository."""
import pytest
import asyncpg
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from pulse.repositories.execution_repository import ExecutionRepository
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
def execution_repository(mock_pool):
    """Create ExecutionRepository instance with mock pool."""
    return ExecutionRepository(mock_pool)


@pytest.mark.asyncio
async def test_create_execution_success(execution_repository, mock_pool, mock_conn, request_context):
    """Test creating an execution record successfully."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_execution = {
        'id': 'exec_123',
        'slice_id': 'slice_123',
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'execution_status': 'CREATED',
        'timeout_minutes': 5,
        'broker_order_id': None,
        'broker_order_status': None,
        'filled_quantity': None,
        'average_price': None,
        'execution_result': None,
        'error_code': None,
        'error_message': None
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_execution)
    
    # Act
    result = await execution_repository.create_execution(
        execution_id='exec_123',
        slice_id='slice_123',
        attempt_id='attempt-abc',
        executor_id='worker-1',
        timeout_minutes=5,
        ctx=request_context
    )
    
    # Assert
    assert result == expected_execution
    assert result['execution_status'] == 'CREATED'
    assert result['timeout_minutes'] == 5
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_update_execution_status_to_placed(execution_repository, mock_pool, mock_conn, request_context):
    """Test updating execution status to PLACED with broker order ID."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_execution = {
        'id': 'exec_123',
        'execution_status': 'PLACED',
        'broker_order_id': 'ZH240101abc123',
        'broker_order_status': 'OPEN',
        'filled_quantity': 0,
        'average_price': None
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_execution)
    
    # Act
    result = await execution_repository.update_execution_status(
        execution_id='exec_123',
        execution_status='PLACED',
        broker_order_id='ZH240101abc123',
        broker_order_status='OPEN',
        filled_quantity=0,
        ctx=request_context
    )
    
    # Assert
    assert result == expected_execution
    assert result['execution_status'] == 'PLACED'
    assert result['broker_order_id'] == 'ZH240101abc123'
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_update_execution_status_to_completed(execution_repository, mock_pool, mock_conn, request_context):
    """Test updating execution status to COMPLETED with results."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_execution = {
        'id': 'exec_123',
        'execution_status': 'COMPLETED',
        'execution_result': 'SUCCESS',
        'filled_quantity': 100,
        'average_price': Decimal('1250.50')
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_execution)
    
    # Act
    result = await execution_repository.update_execution_status(
        execution_id='exec_123',
        execution_status='COMPLETED',
        execution_result='SUCCESS',
        filled_quantity=100,
        average_price=Decimal('1250.50'),
        ctx=request_context
    )
    
    # Assert
    assert result == expected_execution
    assert result['execution_status'] == 'COMPLETED'
    assert result['execution_result'] == 'SUCCESS'
    assert result['filled_quantity'] == 100
    assert result['average_price'] == Decimal('1250.50')
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_update_execution_status_with_error(execution_repository, mock_pool, mock_conn, request_context):
    """Test updating execution status with error details."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    expected_execution = {
        'id': 'exec_123',
        'execution_status': 'COMPLETED',
        'execution_result': 'BROKER_REJECTED',
        'error_code': 'INSUFFICIENT_FUNDS',
        'error_message': 'Insufficient margin available'
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_execution)

    # Act
    result = await execution_repository.update_execution_status(
        execution_id='exec_123',
        execution_status='COMPLETED',
        execution_result='BROKER_REJECTED',
        error_code='INSUFFICIENT_FUNDS',
        error_message='Insufficient margin available',
        ctx=request_context
    )

    # Assert
    assert result == expected_execution
    assert result['execution_result'] == 'BROKER_REJECTED'
    assert result['error_code'] == 'INSUFFICIENT_FUNDS'
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_execution_by_slice_id_success(execution_repository, mock_pool, mock_conn, request_context):
    """Test retrieving an execution by slice ID."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    expected_execution = {
        'id': 'exec_123',
        'slice_id': 'slice_123',
        'execution_status': 'PLACED',
        'broker_order_id': 'ZH240101abc123'
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_execution)

    # Act
    result = await execution_repository.get_execution_by_slice_id('slice_123', request_context)

    # Assert
    assert result == expected_execution
    assert result['slice_id'] == 'slice_123'
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_execution_by_slice_id_not_found(execution_repository, mock_pool, mock_conn, request_context):
    """Test retrieving a non-existent execution returns None."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)

    # Act
    result = await execution_repository.get_execution_by_slice_id('nonexistent', request_context)

    # Assert
    assert result is None
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_connection_released_on_error(execution_repository, mock_pool, mock_conn, request_context):
    """Test that connection is released even when an error occurs."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(side_effect=asyncpg.PostgresError("Database error"))

    # Act & Assert
    with pytest.raises(asyncpg.PostgresError):
        await execution_repository.create_execution(
            execution_id='exec_123',
            slice_id='slice_123',
            attempt_id='attempt-abc',
            executor_id='worker-1',
            timeout_minutes=5,
            ctx=request_context
        )

    # Connection should still be released
    mock_pool.release.assert_called_once_with(mock_conn)

