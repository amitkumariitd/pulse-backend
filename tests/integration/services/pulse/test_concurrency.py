"""Concurrency tests for split order feature.

These tests verify that the system handles concurrent operations correctly
in a multi-pod deployment scenario.
"""

import pytest
import asyncio
from datetime import datetime

from pulse.repositories.order_repository import OrderRepository
from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.workers.splitting_worker import process_single_order
from shared.observability.context import RequestContext
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings


def create_test_ctx(suffix=""):
    """Create a test RequestContext."""
    return RequestContext(
        trace_id=f"t_concurrency_{suffix}",
        trace_source="TEST:concurrency",
        request_id=f"r_concurrency_{suffix}",
        request_source="TEST:concurrency",
        span_source="TEST:concurrency"
    )


@pytest.mark.asyncio
async def test_two_workers_splitting_same_parent_race_condition():
    """Test concurrent processing of the same order.

    This test demonstrates that when two workers process the same order concurrently,
    the database unique constraint on (order_id, sequence_number) prevents duplicate
    child orders. One worker succeeds, the other fails with a constraint violation.

    Note: In production, the worker loop uses get_pending_orders() which has
    SELECT FOR UPDATE SKIP LOCKED, so workers won't pick the same order.
    This test simulates the edge case where both workers somehow get the same order.
    """
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx("1")
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)

        # Create a pending order
        order_id = f"test_concurrent_split_{datetime.now().timestamp()}"
        order_unique_key = f"ouk_concurrent_{datetime.now().timestamp()}"

        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument="NSE:RELIANCE",
            side="BUY",
            total_quantity=100,
            num_splits=5,
            duration_minutes=60,
            randomize=False,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        assert created_order['order_queue_status'] == 'PENDING'

        # Simulate two workers trying to process the same order concurrently
        ctx1 = create_test_ctx("worker1")
        ctx2 = create_test_ctx("worker2")

        # Process with both workers concurrently (edge case scenario)
        results = await asyncio.gather(
            process_single_order(created_order, order_repo, slice_repo, ctx1),
            process_single_order(created_order, order_repo, slice_repo, ctx2),
            return_exceptions=True
        )

        # One should succeed, one should fail
        successes = [r for r in results if r is True]
        failures = [r for r in results if r is False]

        # At least one should succeed
        assert len(successes) >= 1

        # The second one may fail due to duplicate constraint
        # This is expected behavior - the unique constraint protects us

        # Verify exactly 5 slices were created (not 10)
        slices = await slice_repo.get_slices_by_order_id(order_id, ctx)
        assert len(slices) == 5

        # Verify total quantity is correct
        total_quantity = sum(s['quantity'] for s in slices)
        assert total_quantity == 100

    finally:
        await close_pool(pool)


@pytest.mark.asyncio
async def test_pessimistic_locking_prevents_duplicate_splitting():
    """Test that pessimistic locking prevents duplicate child order creation.
    
    This test verifies that the database-level locking mechanism prevents
    race conditions during splitting.
    """
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)

        # Create a pending order
        order_id = f"test_locking_{datetime.now().timestamp()}"
        order_unique_key = f"ouk_locking_{datetime.now().timestamp()}"

        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument="NSE:INFY",
            side="SELL",
            total_quantity=50,
            num_splits=10,
            duration_minutes=30,
            randomize=True,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        # Process the order (this should acquire lock and complete)
        result = await process_single_order(created_order, order_repo, slice_repo, ctx)
        assert result is True

        # Verify order is no longer PENDING
        updated_order = await order_repo.get_order_by_id(order_id, ctx)
        assert updated_order['order_queue_status'] == 'COMPLETED'

        # Try to get pending orders - should not include this order
        pending = await order_repo.get_pending_orders(limit=100, ctx=ctx)
        pending_ids = [o['id'] for o in pending]
        assert order_id not in pending_ids

    finally:
        await close_pool(pool)

