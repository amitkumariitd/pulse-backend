"""Unit tests for the splitting worker.

These tests verify the worker logic without requiring a real database.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from pulse.workers.splitting_worker import (
    generate_order_slice_id,
    process_single_order,
    run_splitting_worker
)
from shared.observability.context import RequestContext, is_valid_trace_id, is_valid_request_id


@pytest.fixture
def mock_ctx():
    """Create a mock RequestContext for testing."""
    return RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST:splitting_worker",
        request_id="r1234567890abcdef1234",
        request_source="TEST:splitting_worker",
        span_source="TEST:splitting_worker"
    )


@pytest.fixture
def sample_order():
    """Create a sample order record."""
    # TIMESTAMPTZ is returned as datetime object from database
    created_at = datetime(2025, 12, 29, 10, 0, 0, tzinfo=timezone.utc)

    return {
        'id': 'order_123',
        'instrument': 'NSE:RELIANCE',
        'side': 'BUY',
        'total_quantity': 100,
        'num_splits': 5,
        'duration_minutes': 60,
        'randomize': False,
        'created_at': created_at,
        'order_queue_status': 'PENDING',
        'trace_id': 't1234567890abcdef1234',
        'trace_source': 'TEST:parent_order'
    }


def test_generate_order_slice_id_format():
    """Test that order slice IDs have the correct format."""
    slice_id = generate_order_slice_id()
    
    assert slice_id.startswith('os')
    assert len(slice_id) == 24  # 'os' + 10 digits + 12 hex chars
    
    # Verify timestamp part is numeric
    timestamp_part = slice_id[2:12]
    assert timestamp_part.isdigit()
    
    # Verify random part is hexadecimal
    random_part = slice_id[12:]
    assert len(random_part) == 12
    assert all(c in '0123456789abcdef' for c in random_part)


def test_generate_order_slice_id_uniqueness():
    """Test that consecutive slice IDs are unique."""
    id1 = generate_order_slice_id()
    id2 = generate_order_slice_id()
    
    assert id1 != id2


@pytest.mark.asyncio
async def test_process_single_order_success(mock_ctx, sample_order):
    """Test successful processing of a single order."""
    # Create mock repositories
    mock_order_repo = MagicMock()
    mock_order_repo.update_order_status = AsyncMock()
    mock_order_repo.mark_split_complete = AsyncMock(return_value=True)
    
    mock_slice_repo = MagicMock()
    mock_slice_repo.create_order_slices_batch = AsyncMock(return_value=5)
    
    # Process the order
    result = await process_single_order(
        sample_order,
        mock_order_repo,
        mock_slice_repo,
        mock_ctx
    )
    
    # Verify success
    assert result is True

    # Verify status was updated to IN_PROGRESS
    # The context should have the parent order's trace_id
    assert mock_order_repo.update_order_status.called
    update_call_args = mock_order_repo.update_order_status.call_args_list[0]
    assert update_call_args[0][0] == 'order_123'
    assert update_call_args[0][1] == 'IN_PROGRESS'
    update_ctx = update_call_args[0][2]
    assert update_ctx.trace_id == 't1234567890abcdef1234'  # From parent order
    assert update_ctx.trace_source == 'TEST:parent_order'  # From parent order

    # Verify slices were created
    assert mock_slice_repo.create_order_slices_batch.called
    call_args = mock_slice_repo.create_order_slices_batch.call_args
    slice_records = call_args[0][0]
    slice_ctx = call_args[0][1]

    # Verify context passed to slice creation has parent's trace_id
    assert slice_ctx.trace_id == 't1234567890abcdef1234'
    assert slice_ctx.trace_source == 'TEST:parent_order'
    
    # Verify correct number of slices
    assert len(slice_records) == 5
    
    # Verify slice structure
    for i, slice_record in enumerate(slice_records):
        assert slice_record['order_id'] == 'order_123'
        assert slice_record['instrument'] == 'NSE:RELIANCE'
        assert slice_record['side'] == 'BUY'
        assert slice_record['quantity'] == 20  # 100 / 5
        assert slice_record['sequence_number'] == i + 1
        assert 'id' in slice_record
        assert 'scheduled_at' in slice_record
    
    # Verify order was marked as complete
    assert mock_order_repo.mark_split_complete.called
    complete_call_args = mock_order_repo.mark_split_complete.call_args
    assert complete_call_args[0][0] == 'order_123'
    assert complete_call_args[0][1] == 5
    complete_ctx = complete_call_args[0][2]
    assert complete_ctx.trace_id == 't1234567890abcdef1234'
    assert complete_ctx.trace_source == 'TEST:parent_order'


@pytest.mark.asyncio
async def test_process_single_order_failure(mock_ctx, sample_order):
    """Test handling of processing failure."""
    # Create mock repositories that fail
    mock_order_repo = MagicMock()
    mock_order_repo.update_order_status = AsyncMock()
    
    mock_slice_repo = MagicMock()
    mock_slice_repo.create_order_slices_batch = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    # Process the order
    result = await process_single_order(
        sample_order,
        mock_order_repo,
        mock_slice_repo,
        mock_ctx
    )
    
    # Verify failure
    assert result is False
    
    # Verify order was marked as FAILED
    failed_call = None
    for call in mock_order_repo.update_order_status.call_args_list:
        if call[0][1] == 'FAILED':
            failed_call = call
            break

    assert failed_call is not None
    assert 'Database error' in failed_call[1]['skip_reason']


@pytest.mark.asyncio
async def test_splitting_worker_creates_valid_context():
    """Test that worker creates context with valid trace_id, request_id, and span_id formats."""
    import asyncio

    captured_ctx = None

    # Mock order repository to capture context and stop the loop
    mock_order_repo = MagicMock()

    async def capture_and_stop(batch_size, ctx):
        nonlocal captured_ctx
        captured_ctx = ctx
        raise asyncio.CancelledError()  # Stop the loop after first iteration

    mock_order_repo.get_pending_orders = AsyncMock(side_effect=capture_and_stop)

    mock_pool = MagicMock()

    with patch('pulse.workers.splitting_worker.OrderRepository', return_value=mock_order_repo):
        with patch('pulse.workers.splitting_worker.OrderSliceRepository'):
            try:
                await run_splitting_worker(mock_pool, poll_interval_seconds=1, batch_size=10)
            except asyncio.CancelledError:
                pass

    # Verify context was created with valid formats
    assert captured_ctx is not None
    assert is_valid_trace_id(captured_ctx.trace_id), f"Invalid trace_id: {captured_ctx.trace_id}"
    assert is_valid_request_id(captured_ctx.request_id), f"Invalid request_id: {captured_ctx.request_id}"
    assert captured_ctx.trace_source == "PULSE_BACKGROUND:splitting_worker"
    assert captured_ctx.request_source == "PULSE_BACKGROUND:splitting_worker"
    assert captured_ctx.span_source == "PULSE_BACKGROUND:splitting_worker"

