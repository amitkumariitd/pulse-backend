"""Integration tests for the splitting worker.

These tests verify end-to-end splitting behavior with a real database.
"""

import pytest
import asyncpg
from datetime import datetime, timezone

from pulse.workers.splitting_worker import process_single_order
from pulse.repositories.order_repository import OrderRepository
from pulse.repositories.order_slice_repository import OrderSliceRepository
from shared.observability.context import RequestContext
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings


def create_test_ctx():
    """Create a test RequestContext."""
    return RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST:splitting_worker_integration",
        request_id="r1234567890abcdef1234",
        request_source="TEST:splitting_worker_integration",
        span_source="TEST:splitting_worker_integration"
    )


@pytest.mark.asyncio
async def test_process_order_creates_slices():
    """Test that processing an order creates the correct number of slices."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)
    
        # Create a test order
        order_id = f"test_order_{datetime.now().timestamp()}"
        order_unique_key = f"test_unique_{datetime.now().timestamp()}"

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

        # Process the order
        result = await process_single_order(
            created_order,
            order_repo,
            slice_repo,
            ctx
        )

        assert result is True

        # Verify order status was updated
        updated_order = await order_repo.get_order_by_id(order_id, ctx)
        assert updated_order['order_queue_status'] == 'COMPLETED'
        assert updated_order['split_completed_at'] is not None

        # Verify slices were created
        slices = await slice_repo.get_slices_by_order_id(order_id, ctx)
        assert len(slices) == 5

        # Verify slice properties
        total_quantity = sum(s['quantity'] for s in slices)
        assert total_quantity == 100

        for i, slice_record in enumerate(slices):
            assert slice_record['order_id'] == order_id
            assert slice_record['instrument'] == 'NSE:RELIANCE'
            assert slice_record['side'] == 'BUY'
            assert slice_record['sequence_number'] == i + 1
            assert slice_record['status'] == 'PENDING'
            assert slice_record['scheduled_at'] is not None

    finally:
        await close_pool(pool)


@pytest.mark.asyncio
async def test_process_order_with_randomization():
    """Test that processing an order with randomization works correctly."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = create_test_ctx()
        order_repo = OrderRepository(pool)
        slice_repo = OrderSliceRepository(pool)

        # Create a test order with randomization
        order_id = f"test_order_random_{datetime.now().timestamp()}"
        order_unique_key = f"test_unique_random_{datetime.now().timestamp()}"

        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument="NSE:INFY",
            side="SELL",
            total_quantity=200,
            num_splits=10,
            duration_minutes=120,
            randomize=True,
            order_unique_key=order_unique_key,
            ctx=ctx
        )

        # Process the order
        result = await process_single_order(
            created_order,
            order_repo,
            slice_repo,
            ctx
        )

        assert result is True

        # Verify slices were created
        slices = await slice_repo.get_slices_by_order_id(order_id, ctx)
        assert len(slices) == 10

        # Verify total quantity is preserved
        total_quantity = sum(s['quantity'] for s in slices)
        assert total_quantity == 200

        # Verify quantities vary (randomization applied)
        quantities = [s['quantity'] for s in slices]
        # Not all quantities should be the same (with high probability)
        assert len(set(quantities)) > 1

    finally:
        await close_pool(pool)

