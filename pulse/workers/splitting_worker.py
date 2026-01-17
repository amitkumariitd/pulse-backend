"""Splitting worker for processing pending orders.

This worker:
1. Picks pending orders using SELECT FOR UPDATE SKIP LOCKED
2. Updates status to IN_PROGRESS
3. Calculates split schedule using pulse.splitting
4. Creates order slices in a transaction
5. Updates parent order status to COMPLETED or FAILED
"""

import asyncio
import asyncpg
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from pulse.splitting import calculate_split_schedule
from pulse.repositories.order_repository import OrderRepository
from pulse.repositories.order_slice_repository import OrderSliceRepository
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger

logger = get_logger("pulse.workers.splitting")


def generate_order_slice_id() -> str:
    """Generate unique ID for order slice.
    
    Format: os + Unix timestamp (seconds) + 12 hexadecimal characters
    Example: os1735228800a1b2c3d4e5f6
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)
    return f"os{timestamp}{random_hex}"


async def process_single_order(
    order: dict,
    order_repo: OrderRepository,
    slice_repo: OrderSliceRepository,
    ctx: RequestContext
) -> bool:
    """Process a single pending order and split it into slices.

    Args:
        order: Order record from database
        order_repo: Order repository instance
        slice_repo: Order slice repository instance
        ctx: Request context for tracing (worker context, will be replaced with order's trace_id)

    Returns:
        True if successfully processed, False otherwise
    """
    order_id = order['id']

    # Create a new context that inherits the parent order's origin trace context
    # This ensures slices inherit the same origin_* fields as the parent order
    order_ctx = RequestContext(
        trace_id=order['origin_trace_id'],  # Use parent order's origin_trace_id
        trace_source=order['origin_trace_source'],  # Use parent order's origin_trace_source
        request_id=order['origin_request_id'],  # Use parent order's origin_request_id
        request_source=order['origin_request_source'],  # Use parent order's origin_request_source
        span_source="PULSE_BACKGROUND:splitting_worker"
    )

    try:
        # Update status to IN_PROGRESS immediately
        await order_repo.update_order_status(order_id, 'IN_PROGRESS', order_ctx)
        
        logger.info("Processing order for splitting", order_ctx, data={
            "order_id": order_id,
            "total_quantity": order['total_quantity'],
            "num_splits": order['num_splits']
        })

        # created_at is already a datetime object (TIMESTAMPTZ from database)
        parent_created_at = order['created_at']

        # Calculate split schedule
        slices = calculate_split_schedule(
            parent_created_at=parent_created_at,
            total_quantity=order['total_quantity'],
            num_splits=order['num_splits'],
            duration_minutes=order['duration_minutes'],
            randomize=order['randomize']
        )

        # Prepare slice records for batch insert
        slice_records = []
        for split_slice in slices:
            slice_records.append({
                'id': generate_order_slice_id(),
                'order_id': order_id,
                'instrument': order['instrument'],
                'side': order['side'],
                'quantity': split_slice.quantity,
                'sequence_number': split_slice.sequence_number,
                'scheduled_at': split_slice.scheduled_at  # datetime object, asyncpg handles conversion
            })

        # Create all slices in batch
        created_count = await slice_repo.create_order_slices_batch(slice_records, order_ctx)

        if created_count != order['num_splits']:
            raise RuntimeError(f"Expected {order['num_splits']} slices, created {created_count}")

        # Mark order as completed
        await order_repo.mark_split_complete(order_id, created_count, order_ctx)

        logger.info("Order splitting completed", order_ctx, data={
            "order_id": order_id,
            "slices_created": created_count
        })

        return True

    except Exception as e:
        logger.error("Order splitting failed", order_ctx, data={
            "order_id": order_id,
            "error": str(e)
        })

        # Mark order as failed
        try:
            await order_repo.update_order_status(
                order_id,
                'FAILED',
                order_ctx,
                skip_reason=f"Splitting error: {str(e)}"
            )
        except Exception as update_error:
            logger.error("Failed to mark order as FAILED", order_ctx, data={
                "order_id": order_id,
                "error": str(update_error)
            })

        return False


async def run_splitting_worker(
    pool: asyncpg.Pool,
    poll_interval_seconds: int = 5,
    batch_size: int = 10
):
    """Run the splitting worker loop.
    
    Args:
        pool: Database connection pool
        poll_interval_seconds: Seconds to wait between polls when no work found
        batch_size: Maximum number of orders to process per iteration
    """
    logger.info("Splitting worker started", data={
        "poll_interval_seconds": poll_interval_seconds,
        "batch_size": batch_size
    })
    
    order_repo = OrderRepository(pool)
    slice_repo = OrderSliceRepository(pool)
    
    while True:
        try:
            # Create context for this worker iteration
            ctx = RequestContext(
                trace_id=generate_trace_id(),
                trace_source="PULSE_BACKGROUND:splitting_worker",
                request_id=generate_request_id(),
                request_source="PULSE_BACKGROUND:splitting_worker",
                span_source="PULSE_BACKGROUND:splitting_worker"
            )

            # Get pending orders with pessimistic locking
            pending_orders = await order_repo.get_pending_orders(batch_size, ctx)

            if not pending_orders:
                # No work to do, sleep and retry
                await asyncio.sleep(poll_interval_seconds)
                continue

            logger.info("Found pending orders", ctx, data={
                "count": len(pending_orders)
            })

            # Process each order
            for order in pending_orders:
                await process_single_order(order, order_repo, slice_repo, ctx)

        except Exception as e:
            logger.error("Worker loop error", data={"error": str(e)})
            await asyncio.sleep(poll_interval_seconds)

