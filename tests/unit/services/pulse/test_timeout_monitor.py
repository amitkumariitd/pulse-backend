"""Unit tests for timeout monitor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from shared.observability.context import RequestContext, is_valid_trace_id, is_valid_request_id
from pulse.workers.timeout_monitor import recover_timed_out_executions, run_timeout_monitor


@pytest.mark.asyncio
async def test_recover_timed_out_executions_success():
    """Test recovering timed-out executions."""
    # Arrange
    mock_exec_repo = AsyncMock()
    mock_slice_repo = AsyncMock()

    # Mock timed-out executions
    timed_out_executions = [
        {
            'id': 'exec1',
            'slice_id': 'slice1',
            'executor_id': 'exec-worker-1',
            'filled_quantity': 50,
            'average_price': 1250.00
        },
        {
            'id': 'exec2',
            'slice_id': 'slice2',
            'executor_id': 'exec-worker-2',
            'filled_quantity': 0,
            'average_price': None
        }
    ]

    mock_exec_repo.find_timed_out_executions = AsyncMock(return_value=timed_out_executions)
    mock_exec_repo.update_execution_status = AsyncMock()

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
    count = await recover_timed_out_executions(mock_exec_repo, mock_slice_repo, ctx)

    # Assert
    assert count == 2
    mock_exec_repo.find_timed_out_executions.assert_called_once()
    assert mock_exec_repo.update_execution_status.call_count == 2
    assert mock_conn.execute.call_count == 2

    # Verify first execution was marked as EXECUTOR_TIMEOUT
    first_call = mock_exec_repo.update_execution_status.call_args_list[0]
    assert first_call[1]['execution_id'] == 'exec1'
    assert first_call[1]['execution_status'] == 'COMPLETED'
    assert first_call[1]['execution_result'] == 'EXECUTOR_TIMEOUT'
    assert first_call[1]['error_code'] == 'EXECUTOR_TIMEOUT'


@pytest.mark.asyncio
async def test_recover_timed_out_executions_no_timeouts():
    """Test when there are no timed-out executions."""
    # Arrange
    mock_exec_repo = AsyncMock()
    mock_slice_repo = AsyncMock()

    mock_exec_repo.find_timed_out_executions = AsyncMock(return_value=[])

    ctx = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_source="TEST"
    )

    # Act
    count = await recover_timed_out_executions(mock_exec_repo, mock_slice_repo, ctx)

    # Assert
    assert count == 0
    mock_exec_repo.find_timed_out_executions.assert_called_once()


@pytest.mark.asyncio
async def test_recover_timed_out_executions_partial_fill():
    """Test recovering execution with partial fill."""
    # Arrange
    mock_exec_repo = AsyncMock()
    mock_slice_repo = AsyncMock()

    # Mock execution with partial fill
    timed_out_executions = [
        {
            'id': 'exec1',
            'slice_id': 'slice1',
            'executor_id': 'exec-worker-1',
            'filled_quantity': 75,
            'average_price': 1249.50
        }
    ]

    mock_exec_repo.find_timed_out_executions = AsyncMock(return_value=timed_out_executions)
    mock_exec_repo.update_execution_status = AsyncMock()

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
    count = await recover_timed_out_executions(mock_exec_repo, mock_slice_repo, ctx)

    # Assert
    assert count == 1

    # Verify slice was updated with partial fill data
    slice_update_call = mock_conn.execute.call_args
    assert slice_update_call[0][1] == 'slice1'  # slice_id
    assert slice_update_call[0][2] == 75  # filled_quantity
    assert slice_update_call[0][3] == 1249.50  # average_price


@pytest.mark.asyncio
async def test_timeout_monitor_creates_valid_context():
    """Test that monitor creates context with valid trace_id, request_id, and span_id formats."""
    import asyncio

    captured_ctx = None

    async def capture_and_stop(exec_repo, slice_repo, ctx):
        nonlocal captured_ctx
        captured_ctx = ctx
        raise asyncio.CancelledError()  # Stop the loop after first iteration

    mock_pool = AsyncMock()

    with patch('pulse.workers.timeout_monitor.recover_timed_out_executions', side_effect=capture_and_stop):
        try:
            await run_timeout_monitor(mock_pool, check_interval_seconds=1)
        except asyncio.CancelledError:
            pass

    # Verify context was created with valid formats
    assert captured_ctx is not None
    assert is_valid_trace_id(captured_ctx.trace_id), f"Invalid trace_id: {captured_ctx.trace_id}"
    assert is_valid_request_id(captured_ctx.request_id), f"Invalid request_id: {captured_ctx.request_id}"
    assert captured_ctx.trace_source == "PULSE_BACKGROUND:timeout_monitor"
    assert captured_ctx.request_source == "PULSE_BACKGROUND:timeout_monitor"
    assert captured_ctx.span_source == "PULSE_BACKGROUND:timeout_monitor"

