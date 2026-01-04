"""Unit tests for timeout monitor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
from shared.observability.context import RequestContext, is_valid_trace_id, is_valid_request_id, is_valid_span_id
from pulse.workers.timeout_monitor import recover_stuck_orders, run_timeout_monitor


@pytest.mark.asyncio
async def test_recover_stuck_orders_success():
    """Test recovering stuck orders."""
    # Arrange
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 3")

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )

    # Act
    count = await recover_stuck_orders(mock_pool, timeout_minutes=5, ctx=ctx)

    # Assert
    assert count == 3
    mock_pool.acquire.assert_called_once()
    mock_conn.execute.assert_called_once()
    mock_pool.release.assert_called_once_with(mock_conn)

    # Verify SQL parameters
    call_args = mock_conn.execute.call_args
    sql = call_args[0][0]
    params = call_args[0][1:]

    assert "UPDATE orders" in sql
    assert "order_queue_status = 'FAILED'" in sql
    assert "WHERE order_queue_status = 'IN_PROGRESS'" in sql
    assert "AND updated_at <" in sql

    # Check error message
    assert "Processing timeout" in params[0]
    assert "5 minutes" in params[0]

    # Check context propagation
    assert params[2] == ctx.request_id
    assert params[3] == ctx.span_id


@pytest.mark.asyncio
async def test_recover_stuck_orders_no_stuck_orders():
    """Test when there are no stuck orders."""
    # Arrange
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 0")

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )

    # Act
    count = await recover_stuck_orders(mock_pool, timeout_minutes=5, ctx=ctx)

    # Assert
    assert count == 0
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_recover_stuck_orders_custom_timeout():
    """Test with custom timeout value."""
    # Arrange
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )

    # Act
    count = await recover_stuck_orders(mock_pool, timeout_minutes=10, ctx=ctx)

    # Assert
    assert count == 1

    # Verify timeout calculation
    call_args = mock_conn.execute.call_args
    params = call_args[0][1:]

    # Error message should mention 10 minutes
    assert "10 minutes" in params[0]

    # Threshold should be calculated correctly
    # params[4] is the threshold_micros
    current_time_micros = int(time.time() * 1_000_000)
    timeout_micros = 10 * 60 * 1_000_000
    expected_threshold = current_time_micros - timeout_micros

    # Allow 1 second tolerance for test execution time
    assert abs(params[4] - expected_threshold) < 1_000_000


@pytest.mark.asyncio
async def test_recover_stuck_orders_database_error():
    """Test handling of database errors."""
    # Arrange
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.release = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=Exception("Database error"))

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await recover_stuck_orders(mock_pool, timeout_minutes=5, ctx=ctx)

    assert "Database error" in str(exc_info.value)
    # Connection should still be released
    mock_pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_timeout_monitor_creates_valid_context():
    """Test that monitor creates context with valid trace_id, request_id, and span_id formats."""
    import asyncio

    captured_ctx = None

    async def capture_and_stop(pool, timeout_minutes, ctx):
        nonlocal captured_ctx
        captured_ctx = ctx
        raise asyncio.CancelledError()  # Stop the loop after first iteration

    mock_pool = AsyncMock()

    with patch('pulse.workers.timeout_monitor.recover_stuck_orders', side_effect=capture_and_stop):
        try:
            await run_timeout_monitor(mock_pool, check_interval_seconds=1, timeout_minutes=5)
        except asyncio.CancelledError:
            pass

    # Verify context was created with valid formats
    assert captured_ctx is not None
    assert is_valid_trace_id(captured_ctx.trace_id), f"Invalid trace_id: {captured_ctx.trace_id}"
    assert is_valid_request_id(captured_ctx.request_id), f"Invalid request_id: {captured_ctx.request_id}"
    assert is_valid_span_id(captured_ctx.span_id), f"Invalid span_id: {captured_ctx.span_id}"
    assert captured_ctx.trace_source == "PULSE_BACKGROUND:timeout_monitor"
    assert captured_ctx.request_source == "PULSE_BACKGROUND:timeout_monitor"
    assert captured_ctx.span_source == "PULSE_BACKGROUND:timeout_monitor"

