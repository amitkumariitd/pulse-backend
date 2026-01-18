"""Unit tests for parent order cancellation handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from pulse.workers.cancellation_handler import handle_order_cancellation
from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.repositories.execution_repository import ExecutionRepository
from pulse.repositories.broker_event_repository import BrokerEventRepository
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderResponse
from shared.observability.context import RequestContext


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
def mock_pool():
    """Create a mock database pool."""
    return MagicMock()


@pytest.fixture
def mock_conn():
    """Create a mock database connection."""
    return AsyncMock()


@pytest.fixture
def slice_repo(mock_pool):
    """Create order slice repository with mock pool."""
    return OrderSliceRepository(mock_pool)


@pytest.fixture
def exec_repo(mock_pool):
    """Create execution repository with mock pool."""
    return ExecutionRepository(mock_pool)


@pytest.fixture
def event_repo(mock_pool):
    """Create broker event repository with mock pool."""
    return BrokerEventRepository(mock_pool)


@pytest.fixture
def zerodha_client():
    """Create mock Zerodha client."""
    return AsyncMock(spec=ZerodhaClient)


@pytest.mark.asyncio
async def test_handle_cancellation_no_slices(
    slice_repo, exec_repo, event_repo, zerodha_client, request_context, mock_pool, mock_conn
):
    """Test cancellation when no slices need to be cancelled."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    # Act
    result = await handle_order_cancellation(
        order_id='ord_123',
        slice_repo=slice_repo,
        exec_repo=exec_repo,
        event_repo=event_repo,
        zerodha_client=zerodha_client,
        ctx=request_context
    )

    # Assert
    assert result == {"skipped_slices": 0, "cancelled_executions": 0}
    mock_conn.fetch.assert_called_once()
    zerodha_client.cancel_order.assert_not_called()


@pytest.mark.asyncio
async def test_handle_cancellation_pending_slice(
    slice_repo, exec_repo, event_repo, zerodha_client, request_context, mock_pool, mock_conn
):
    """Test cancellation of a PENDING slice (not yet executing)."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    # First call: fetch slices
    # Second call: update slice status
    mock_conn.fetch = AsyncMock(return_value=[
        {'id': 'slice_1', 'order_id': 'ord_123', 'status': 'PENDING', 'sequence_number': 1}
    ])
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    # Act
    result = await handle_order_cancellation(
        order_id='ord_123',
        slice_repo=slice_repo,
        exec_repo=exec_repo,
        event_repo=event_repo,
        zerodha_client=zerodha_client,
        ctx=request_context
    )

    # Assert
    assert result == {"skipped_slices": 1, "cancelled_executions": 0}
    assert mock_conn.execute.call_count == 1  # Update slice status
    zerodha_client.cancel_order.assert_not_called()  # No broker call for PENDING


@pytest.mark.asyncio
async def test_handle_cancellation_executing_slice_with_broker_order(
    slice_repo, exec_repo, event_repo, zerodha_client, request_context, mock_pool, mock_conn
):
    """Test cancellation of an EXECUTING slice with broker order."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()



    # Mock slice fetch
    mock_conn.fetch = AsyncMock(side_effect=[
        # First call: fetch slices
        [{'id': 'slice_1', 'order_id': 'ord_123', 'status': 'EXECUTING', 'sequence_number': 1}],
        # Second call: get event sequence (in event_repo.get_connection)
    ])

    # Mock execution fetch
    mock_conn.fetchrow = AsyncMock(side_effect=[
        # First call: get execution by slice_id
        {
            'id': 'exec_1',
            'slice_id': 'slice_1',
            'broker_order_id': 'ZH240101abc123',
            'attempt_id': 'attempt-abc',
            'executor_id': 'worker-1',
            'execution_status': 'PLACED'
        },
        # Second call: get event sequence
        None,  # Will use COALESCE to return 1
        # Third call: update execution status
        {'id': 'exec_1', 'execution_status': 'SKIPPED'}
    ])

    # Mock event sequence query
    mock_conn.fetchval = AsyncMock(return_value=3)

    # Mock slice update
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    # Mock Zerodha cancel response
    zerodha_client.cancel_order = AsyncMock(return_value=ZerodhaOrderResponse(
        broker_order_id='ZH240101abc123',
        status='CANCELLED',
        filled_quantity=0,
        pending_quantity=0,
        average_price=None,
        message='Order cancelled successfully'
    ))

    # Mock execution repository methods
    exec_repo.get_execution_by_slice_id = AsyncMock(return_value={
        'id': 'exec_1',
        'slice_id': 'slice_1',
        'broker_order_id': 'ZH240101abc123',
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'execution_status': 'PLACED'
    })
    exec_repo.update_execution_status = AsyncMock(return_value={
        'id': 'exec_1',
        'execution_status': 'SKIPPED'
    })

    # Mock event repository
    event_repo.create_broker_event = AsyncMock(return_value={
        'id': 'evt_1',
        'event_type': 'CANCEL_REQUEST',
        'is_success': True
    })

    # Act
    result = await handle_order_cancellation(
        order_id='ord_123',
        slice_repo=slice_repo,
        exec_repo=exec_repo,
        event_repo=event_repo,
        zerodha_client=zerodha_client,
        ctx=request_context
    )

    # Assert
    assert result == {"skipped_slices": 1, "cancelled_executions": 1}
    zerodha_client.cancel_order.assert_called_once_with('ZH240101abc123', request_context)
    exec_repo.update_execution_status.assert_called_once()
    event_repo.create_broker_event.assert_called_once()

    # Verify broker event was created with correct parameters
    event_call = event_repo.create_broker_event.call_args
    assert event_call.kwargs['event_type'] == 'CANCEL_REQUEST'
    assert event_call.kwargs['is_success'] is True
    assert event_call.kwargs['broker_order_id'] == 'ZH240101abc123'



@pytest.mark.asyncio
async def test_handle_cancellation_executing_slice_broker_cancel_fails(
    slice_repo, exec_repo, event_repo, zerodha_client, request_context, mock_pool, mock_conn
):
    """Test cancellation when broker cancel fails (still marks slice as SKIPPED)."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    mock_conn.fetch = AsyncMock(return_value=[
        {'id': 'slice_1', 'order_id': 'ord_123', 'status': 'EXECUTING', 'sequence_number': 1}
    ])
    mock_conn.fetchval = AsyncMock(return_value=3)
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    # Mock Zerodha cancel failure
    zerodha_client.cancel_order = AsyncMock(side_effect=Exception("Network timeout"))

    # Mock execution repository
    exec_repo.get_execution_by_slice_id = AsyncMock(return_value={
        'id': 'exec_1',
        'slice_id': 'slice_1',
        'broker_order_id': 'ZH240101abc123',
        'attempt_id': 'attempt-abc',
        'executor_id': 'worker-1',
        'execution_status': 'PLACED'
    })
    exec_repo.update_execution_status = AsyncMock(return_value={
        'id': 'exec_1',
        'execution_status': 'SKIPPED'
    })

    # Mock event repository
    event_repo.create_broker_event = AsyncMock(return_value={
        'id': 'evt_1',
        'event_type': 'CANCEL_REQUEST',
        'is_success': False
    })

    # Act
    result = await handle_order_cancellation(
        order_id='ord_123',
        slice_repo=slice_repo,
        exec_repo=exec_repo,
        event_repo=event_repo,
        zerodha_client=zerodha_client,
        ctx=request_context
    )

    # Assert
    assert result == {"skipped_slices": 1, "cancelled_executions": 0}
    zerodha_client.cancel_order.assert_called_once()
    exec_repo.update_execution_status.assert_called_once()  # Still marks as SKIPPED
    event_repo.create_broker_event.assert_called_once()

    # Verify failed broker event was created
    event_call = event_repo.create_broker_event.call_args
    assert event_call.kwargs['event_type'] == 'CANCEL_REQUEST'
    assert event_call.kwargs['is_success'] is False
    assert event_call.kwargs['error_code'] == 'CANCEL_FAILED'
    assert 'Network timeout' in event_call.kwargs['error_message']


@pytest.mark.asyncio
async def test_handle_cancellation_mixed_slices(
    slice_repo, exec_repo, event_repo, zerodha_client, request_context, mock_pool, mock_conn
):
    """Test cancellation with mix of PENDING and EXECUTING slices."""
    # Arrange
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()

    mock_conn.fetch = AsyncMock(return_value=[
        {'id': 'slice_1', 'order_id': 'ord_123', 'status': 'PENDING', 'sequence_number': 1},
        {'id': 'slice_2', 'order_id': 'ord_123', 'status': 'EXECUTING', 'sequence_number': 2}
    ])
    mock_conn.fetchval = AsyncMock(return_value=2)
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    # Mock Zerodha cancel
    zerodha_client.cancel_order = AsyncMock(return_value=ZerodhaOrderResponse(
        broker_order_id='ZH240101abc456',
        status='CANCELLED',
        filled_quantity=0,
        pending_quantity=0,
        average_price=None,
        message='Order cancelled successfully'
    ))

    # Mock execution repository - only slice_2 has execution
    async def mock_get_execution(slice_id, ctx):
        if slice_id == 'slice_2':
            return {
                'id': 'exec_2',
                'slice_id': 'slice_2',
                'broker_order_id': 'ZH240101abc456',
                'attempt_id': 'attempt-def',
                'executor_id': 'worker-2',
                'execution_status': 'PLACED'
            }
        return None

    exec_repo.get_execution_by_slice_id = AsyncMock(side_effect=mock_get_execution)
    exec_repo.update_execution_status = AsyncMock(return_value={'id': 'exec_2', 'execution_status': 'SKIPPED'})

    # Mock event repository
    event_repo.create_broker_event = AsyncMock(return_value={'id': 'evt_1', 'event_type': 'CANCEL_REQUEST'})

    # Act
    result = await handle_order_cancellation(
        order_id='ord_123',
        slice_repo=slice_repo,
        exec_repo=exec_repo,
        event_repo=event_repo,
        zerodha_client=zerodha_client,
        ctx=request_context
    )

    # Assert
    assert result == {"skipped_slices": 2, "cancelled_executions": 1}
    zerodha_client.cancel_order.assert_called_once()  # Only for slice_2
    exec_repo.update_execution_status.assert_called_once()  # Only for slice_2
