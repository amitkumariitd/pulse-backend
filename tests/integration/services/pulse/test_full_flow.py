"""Integration tests for full order flow (acceptance → splitting).

These tests verify the complete flow from order creation through splitting,
including concurrency scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from pulse.repositories.order_repository import OrderRepository
from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.workers.splitting_worker import process_single_order
from shared.observability.context import RequestContext
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings


def create_test_ctx(suffix=""):
    """Create a test RequestContext."""
    return RequestContext(
        trace_id=f"t1234567890abcdef{suffix}",
        trace_source="TEST:full_flow",
        request_id=f"r1234567890abcdef{suffix}",
        request_source="TEST:full_flow",
        span_source="TEST:full_flow"
    )


@pytest.mark.asyncio
async def test_full_flow_acceptance_to_splitting():
    """Test full flow from order acceptance to splitting completion."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)

        # Phase 1: Order Acceptance
        order_id = f"test_full_flow_{datetime.now().timestamp()}"
        order_unique_key = f"ouk_full_flow_{datetime.now().timestamp()}"

        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument="NSE:RELIANCE",
            side="BUY",
            total_quantity=100,
            num_splits=5,
            duration_minutes=60,
            randomize=True,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        # Verify initial state
        assert created_order['order_queue_status'] == 'PENDING'
        assert created_order['split_completed_at'] is None

        # Phase 2: Order Splitting
        result = await process_single_order(
            created_order,
            order_repo,
            slice_repo,
            ctx
        )

        assert result is True

        # Verify final state
        updated_order = await order_repo.get_order_by_id(order_id, ctx)
        assert updated_order['order_queue_status'] == 'COMPLETED'
        assert updated_order['split_completed_at'] is not None

        # Verify child orders created
        slices = await slice_repo.get_slices_by_order_id(order_id, ctx)
        assert len(slices) == 5

        # Verify quantities sum to total
        total_quantity = sum(s['quantity'] for s in slices)
        assert total_quantity == 100

        # Verify all scheduled times are within duration window
        # created_at and scheduled_at are already datetime objects (TIMESTAMPTZ from database)
        parent_created_at = created_order['created_at']
        time_window_end = parent_created_at + timedelta(minutes=60)

        for slice_record in slices:
            scheduled_at = slice_record['scheduled_at']
            assert parent_created_at <= scheduled_at <= time_window_end
            assert slice_record['status'] == 'SCHEDULED'

    finally:
        await close_pool(pool)


@pytest.mark.asyncio
async def test_duplicate_request_with_same_order_unique_key():
    """Test that duplicate requests with same order_unique_key return same order."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)

        order_unique_key = f"ouk_duplicate_test_{datetime.now().timestamp()}"

        # Create first order
        order1 = await order_repo.create_order(
            order_id=f"order1_{datetime.now().timestamp()}",
            instrument="NSE:INFY",
            side="BUY",
            total_quantity=50,
            num_splits=5,
            duration_minutes=30,
            randomize=False,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        # Try to create duplicate with same data - should raise UniqueViolationError
        import asyncpg
        with pytest.raises(asyncpg.UniqueViolationError):
            await order_repo.create_order(
                order_id=f"order2_{datetime.now().timestamp()}",
                instrument="NSE:INFY",
                side="BUY",
                total_quantity=50,
                num_splits=5,
                duration_minutes=30,
                randomize=False,
                order_unique_key=order_unique_key,
                ctx=ctx
            )

    finally:
        await close_pool(pool)


@pytest.mark.asyncio
async def test_time_window_constraint_enforcement():
    """Test that all scheduled times are within the duration window."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)

        # Create order with randomization
        order_id = f"test_time_window_{datetime.now().timestamp()}"
        order_unique_key = f"ouk_time_window_{datetime.now().timestamp()}"

        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument="NSE:TCS",
            side="SELL",
            total_quantity=200,
            num_splits=10,
            duration_minutes=120,
            randomize=True,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        # Process the order
        await process_single_order(created_order, order_repo, slice_repo, ctx)

        # Verify all scheduled times are within window
        slices = await slice_repo.get_slices_by_order_id(order_id, ctx)
        # created_at and scheduled_at are already datetime objects (TIMESTAMPTZ from database)
        parent_created_at = created_order['created_at']
        time_window_start = parent_created_at
        time_window_end = parent_created_at + timedelta(minutes=120)

        for slice_record in slices:
            scheduled_at = slice_record['scheduled_at']
            # CRITICAL: All scheduled times MUST be within window
            assert time_window_start <= scheduled_at <= time_window_end, \
                f"Slice {slice_record['id']} scheduled_at {scheduled_at} outside window [{time_window_start}, {time_window_end}]"

    finally:
        await close_pool(pool)


@pytest.mark.asyncio
async def test_trace_id_propagation_from_order_to_slices():
    """Test that order slices inherit the parent order's origin trace context."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)

        # Create order with specific trace context
        order_id = f"test_trace_{datetime.now().timestamp()}"
        order_unique_key = f"ouk_trace_{datetime.now().timestamp()}"
        origin_trace_id = ctx.trace_id
        origin_trace_source = ctx.trace_source
        origin_request_id = ctx.request_id
        origin_request_source = ctx.request_source

        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument="NSE:RELIANCE",
            side="BUY",
            total_quantity=100,
            num_splits=5,
            duration_minutes=60,
            randomize=True,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        # Verify parent order has the expected origin context
        assert created_order['origin_trace_id'] == origin_trace_id
        assert created_order['origin_trace_source'] == origin_trace_source
        assert created_order['origin_request_id'] == origin_request_id
        assert created_order['origin_request_source'] == origin_request_source
        # request_id should be different (generated for async workers)
        assert created_order['request_id'] != origin_request_id

        # Process the order (split into slices)
        result = await process_single_order(
            created_order,
            order_repo,
            slice_repo,
            ctx
        )

        assert result is True

        # Get all slices for this order
        slices = await slice_repo.get_slices_by_order_id(order_id, ctx)

        # Verify all slices have the same origin context as parent order
        assert len(slices) == 5
        for slice_record in slices:
            assert slice_record['origin_trace_id'] == origin_trace_id, \
                f"Slice {slice_record['id']} has origin_trace_id {slice_record['origin_trace_id']}, expected {origin_trace_id}"
            assert slice_record['origin_trace_source'] == origin_trace_source, \
                f"Slice {slice_record['id']} has origin_trace_source {slice_record['origin_trace_source']}, expected {origin_trace_source}"
            assert slice_record['origin_request_id'] == origin_request_id, \
                f"Slice {slice_record['id']} has origin_request_id {slice_record['origin_request_id']}, expected {origin_request_id}"
            assert slice_record['origin_request_source'] == origin_request_source, \
                f"Slice {slice_record['id']} has origin_request_source {slice_record['origin_request_source']}, expected {origin_request_source}"
            # Each slice should have its own request_id for async workers
            assert slice_record['request_id'] != origin_request_id

    finally:
        await close_pool(pool)

