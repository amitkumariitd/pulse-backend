"""Unit tests for BrokerEventRepository."""
import pytest
import asyncpg
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from pulse.repositories.broker_event_repository import BrokerEventRepository
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
def broker_event_repository(mock_pool):
    """Create BrokerEventRepository instance with mock pool."""
    return BrokerEventRepository(mock_pool)


@pytest.mark.asyncio
async def test_create_broker_event_place_order_success(broker_event_repository, mock_pool, mock_conn, request_context):
    """Test creating a successful PLACE_ORDER broker event."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_event = {
        'id': 'evt_123',
        'execution_id': 'exec_123',
        'slice_id': 'slice_123',
        'event_sequence': 1,
        'event_type': 'PLACE_ORDER',
        'attempt_number': 1,
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'broker_name': 'zerodha',
        'is_success': True,
        'broker_order_id': 'ZH240101abc123',
        'broker_status': 'COMPLETE',
        'filled_quantity': 100,
        'average_price': Decimal('1250.50'),
        'response_time_ms': 250
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_event)
    
    # Act
    result = await broker_event_repository.create_broker_event(
        event_id='evt_123',
        execution_id='exec_123',
        slice_id='slice_123',
        event_sequence=1,
        event_type='PLACE_ORDER',
        attempt_number=1,
        attempt_id='attempt-abc',
        executor_id='worker-1',
        broker_name='zerodha',
        is_success=True,
        broker_order_id='ZH240101abc123',
        broker_status='COMPLETE',
        filled_quantity=100,
        average_price=Decimal('1250.50'),
        response_time_ms=250,
        ctx=request_context
    )
    
    # Assert
    assert result == expected_event
    assert result['event_type'] == 'PLACE_ORDER'
    assert result['is_success'] is True
    assert result['broker_order_id'] == 'ZH240101abc123'
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_create_broker_event_place_order_failure(broker_event_repository, mock_pool, mock_conn, request_context):
    """Test creating a failed PLACE_ORDER broker event."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    
    expected_event = {
        'id': 'evt_124',
        'execution_id': 'exec_123',
        'slice_id': 'slice_123',
        'event_sequence': 1,
        'event_type': 'PLACE_ORDER',
        'attempt_number': 1,
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'broker_name': 'zerodha',
        'is_success': False,
        'error_code': 'INSUFFICIENT_FUNDS',
        'error_message': 'Insufficient margin available',
        'response_time_ms': 180
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_event)
    
    # Act
    result = await broker_event_repository.create_broker_event(
        event_id='evt_124',
        execution_id='exec_123',
        slice_id='slice_123',
        event_sequence=1,
        event_type='PLACE_ORDER',
        attempt_number=1,
        attempt_id='attempt-abc',
        executor_id='worker-1',
        broker_name='zerodha',
        is_success=False,
        error_code='INSUFFICIENT_FUNDS',
        error_message='Insufficient margin available',
        response_time_ms=180,
        ctx=request_context
    )
    
    # Assert
    assert result == expected_event
    assert result['is_success'] is False
    assert result['error_code'] == 'INSUFFICIENT_FUNDS'
    assert result['error_message'] == 'Insufficient margin available'
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_create_broker_event_status_poll(broker_event_repository, mock_pool, mock_conn, request_context):
    """Test creating a STATUS_POLL broker event."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    expected_event = {
        'id': 'evt_125',
        'execution_id': 'exec_123',
        'slice_id': 'slice_123',
        'event_sequence': 2,
        'event_type': 'STATUS_POLL',
        'attempt_number': 1,
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'broker_name': 'zerodha',
        'is_success': True,
        'broker_order_id': 'ZH240101abc123',
        'broker_status': 'COMPLETE',
        'filled_quantity': 100,
        'pending_quantity': 0,
        'average_price': Decimal('1250.50'),
        'response_time_ms': 120
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_event)

    # Act
    result = await broker_event_repository.create_broker_event(
        event_id='evt_125',
        execution_id='exec_123',
        slice_id='slice_123',
        event_sequence=2,
        event_type='STATUS_POLL',
        attempt_number=1,
        attempt_id='attempt-abc',
        executor_id='worker-1',
        broker_name='zerodha',
        is_success=True,
        broker_order_id='ZH240101abc123',
        broker_status='COMPLETE',
        filled_quantity=100,
        pending_quantity=0,
        average_price=Decimal('1250.50'),
        response_time_ms=120,
        ctx=request_context
    )

    # Assert
    assert result == expected_event
    assert result['event_type'] == 'STATUS_POLL'
    assert result['event_sequence'] == 2
    assert result['filled_quantity'] == 100
    assert result['pending_quantity'] == 0
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_create_broker_event_cancel_request(broker_event_repository, mock_pool, mock_conn, request_context):
    """Test creating a CANCEL_REQUEST broker event."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    expected_event = {
        'id': 'evt_126',
        'execution_id': 'exec_123',
        'slice_id': 'slice_123',
        'event_sequence': 3,
        'event_type': 'CANCEL_REQUEST',
        'attempt_number': 1,
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'broker_name': 'zerodha',
        'is_success': True,
        'broker_order_id': 'ZH240101abc123',
        'broker_status': 'CANCELLED',
        'response_time_ms': 200
    }
    mock_conn.fetchrow = AsyncMock(return_value=expected_event)

    # Act
    result = await broker_event_repository.create_broker_event(
        event_id='evt_126',
        execution_id='exec_123',
        slice_id='slice_123',
        event_sequence=3,
        event_type='CANCEL_REQUEST',
        attempt_number=1,
        attempt_id='attempt-abc',
        executor_id='worker-1',
        broker_name='zerodha',
        is_success=True,
        broker_order_id='ZH240101abc123',
        broker_status='CANCELLED',
        response_time_ms=200,
        ctx=request_context
    )

    # Assert
    assert result == expected_event
    assert result['event_type'] == 'CANCEL_REQUEST'
    assert result['broker_status'] == 'CANCELLED'
    mock_conn.fetchrow.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_connection_released_on_error(broker_event_repository, mock_pool, mock_conn, request_context):
    """Test that connection is released even when an error occurs."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetchrow = AsyncMock(side_effect=asyncpg.PostgresError("Database error"))

    # Act & Assert
    with pytest.raises(asyncpg.PostgresError):
        await broker_event_repository.create_broker_event(
            event_id='evt_123',
            execution_id='exec_123',
            slice_id='slice_123',
            event_sequence=1,
            event_type='PLACE_ORDER',
            attempt_number=1,
            attempt_id='attempt-abc',
            executor_id='worker-1',
            broker_name='zerodha',
            is_success=True,
            ctx=request_context
        )

    # Connection should still be released
    mock_pool.release.assert_called_once_with(mock_conn)

