"""Unit tests for execution worker."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from shared.observability.context import RequestContext
from pulse.workers.execution_worker import (
    get_pending_slices,
    update_slice_status,
    verify_ownership,
    place_order_with_retry,
    monitor_order_until_complete,
    process_single_slice
)


@pytest.mark.asyncio
async def test_get_pending_slices_success():
    """Test getting pending slices with pessimistic locking."""
    # Arrange
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()

    slices = [
        {
            'id': 'slice1',
            'order_id': 'order1',
            'sequence_number': 1,
            'instrument': 'RELIANCE',
            'quantity': 100,
            'order_type': 'MARKET',
            'status': 'PENDING'
        },
        {
            'id': 'slice2',
            'order_id': 'order2',
            'sequence_number': 1,
            'instrument': 'TCS',
            'quantity': 50,
            'order_type': 'LIMIT',
            'status': 'PENDING'
        }
    ]

    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=slices)

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_source="TEST"
    )

    # Act
    result = await get_pending_slices(
        pool=mock_pool,
        batch_size=10,
        ctx=ctx
    )

    # Assert
    assert len(result) == 2
    assert result[0]['id'] == 'slice1'
    assert result[1]['id'] == 'slice2'
    mock_pool.acquire.assert_called_once()
    mock_pool.release.assert_called_once()


@pytest.mark.asyncio
async def test_get_pending_slices_no_slices():
    """Test getting pending slices when none are available."""
    # Arrange
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()

    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_source="TEST"
    )

    # Act
    result = await get_pending_slices(
        pool=mock_pool,
        batch_size=10,
        ctx=ctx
    )

    # Assert
    assert len(result) == 0
    mock_pool.release.assert_called_once()


@pytest.mark.asyncio
async def test_update_slice_status_success():
    """Test updating slice status successfully."""
    # Arrange
    mock_slice_repo = AsyncMock()
    mock_conn = AsyncMock()

    mock_slice_repo.get_connection = AsyncMock(return_value=mock_conn)
    mock_slice_repo.release_connection = AsyncMock()
    mock_conn.execute = AsyncMock()

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_source="TEST"
    )

    # Act
    await update_slice_status(
        slice_repo=mock_slice_repo,
        slice_id='slice1',
        status='COMPLETED',
        filled_quantity=100,
        average_price=Decimal('1250.00'),
        ctx=ctx
    )

    # Assert
    mock_slice_repo.get_connection.assert_called_once()
    mock_conn.execute.assert_called_once()
    mock_slice_repo.release_connection.assert_called_once()


@pytest.mark.asyncio
async def test_verify_ownership_success():
    """Test verifying execution ownership successfully."""
    # Arrange
    mock_exec_repo = AsyncMock()
    mock_conn = AsyncMock()

    # Execution timeout is 5 minutes in the future
    from datetime import timedelta
    timeout_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    execution_record = {
        'id': 'exec1',
        'executor_id': 'worker-1',
        'executor_timeout_at': timeout_at
    }

    mock_exec_repo.get_connection = AsyncMock(return_value=mock_conn)
    mock_exec_repo.release_connection = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=execution_record)

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_source="TEST"
    )

    # Act
    result = await verify_ownership(
        exec_repo=mock_exec_repo,
        execution_id='exec1',
        executor_id='worker-1',
        timeout_minutes=5,
        ctx=ctx
    )

    # Assert
    assert result is True
    mock_exec_repo.get_connection.assert_called_once()
    mock_exec_repo.release_connection.assert_called_once()


@pytest.mark.asyncio
async def test_verify_ownership_timeout():
    """Test verifying ownership when execution has timed out."""
    # Arrange
    mock_exec_repo = AsyncMock()
    mock_conn = AsyncMock()

    # Execution timed out 1 minute ago
    from datetime import timedelta
    timed_out_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    execution_record = {
        'id': 'exec1',
        'executor_id': 'worker-1',
        'executor_timeout_at': timed_out_at
    }

    mock_exec_repo.get_connection = AsyncMock(return_value=mock_conn)
    mock_exec_repo.release_connection = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=execution_record)

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_source="TEST"
    )

    # Act
    result = await verify_ownership(
        exec_repo=mock_exec_repo,
        execution_id='exec1',
        executor_id='worker-1',
        timeout_minutes=5,
        ctx=ctx
    )

    # Assert
    assert result is False  # Ownership expired
