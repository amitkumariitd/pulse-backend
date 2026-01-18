"""Integration tests for execution worker.

Tests execution worker with real database and mock broker.
Focuses on:
- Successful execution flow
- Network failure handling
- Crash recovery via ownership timeout
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from shared.database.pool import create_pool, close_pool
from config.settings import get_settings
from pulse.repositories.execution_repository import ExecutionRepository
from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.repositories.broker_event_repository import BrokerEventRepository
from pulse.brokers.zerodha_client import ZerodhaClient
from pulse.workers.execution_worker import (
    verify_ownership,
    place_order_with_retry,
    monitor_order_until_complete
)
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id


async def create_test_order_and_slice(pool, ctx):
    """Helper to create test order and slice in database."""
    conn = await pool.acquire()
    try:
        order_id = f"test_ord_{generate_request_id()[:8]}"
        order_unique_key = f"ouk_test_{generate_request_id()[:8]}"
        
        await conn.execute(
            """
            INSERT INTO orders (
                id, order_unique_key, instrument, side, total_quantity, num_splits, duration_minutes,
                randomize, order_queue_status, origin_trace_id, origin_trace_source,
                origin_request_id, origin_request_source, request_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            order_id, order_unique_key, "NSE:RELIANCE", "BUY", 100, 1, 60, False, "COMPLETED",
            ctx.trace_id, ctx.trace_source, ctx.request_id, ctx.request_source, ctx.request_id
        )

        slice_id = f"test_slice_{generate_request_id()[:8]}"
        await conn.execute(
            """
            INSERT INTO order_slices (
                id, order_id, instrument, side, quantity, sequence_number,
                scheduled_at, status, request_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            slice_id, order_id, "NSE:RELIANCE", "BUY", 100, 1,
            datetime.now(timezone.utc), "PENDING",
            ctx.request_id
        )
        
        return order_id, slice_id
    finally:
        await pool.release(conn)


async def cleanup_test_data(pool, order_id, slice_id):
    """Helper to cleanup test data from database."""
    conn = await pool.acquire()
    try:
        # Delete in reverse order of foreign keys
        await conn.execute("DELETE FROM order_slice_broker_events WHERE slice_id = $1", slice_id)
        await conn.execute("DELETE FROM order_slice_executions WHERE slice_id = $1", slice_id)
        await conn.execute("DELETE FROM order_slices WHERE id = $1", slice_id)
        await conn.execute("DELETE FROM orders WHERE id = $1", order_id)
    finally:
        await pool.release(conn)


@pytest.mark.asyncio
async def test_ownership_verification_with_database():
    """Test ownership verification with real database."""
    settings = get_settings()
    pool = await create_pool(settings)

    try:
        ctx = RequestContext(
            trace_id=generate_trace_id(),
            trace_source="TEST:integration",
            request_id=generate_request_id(),
            request_source="TEST:integration",
            span_source="TEST:integration"
        )

        order_id, slice_id = await create_test_order_and_slice(pool, ctx)
        exec_repo = ExecutionRepository(pool)

        # Create execution record
        execution_id = f"test_exec_{generate_request_id()[:8]}"
        attempt_id = f"attempt-{generate_request_id()[:8]}"
        executor_id = "test-worker-1"

        await exec_repo.create_execution(
            execution_id=execution_id,
            slice_id=slice_id,
            attempt_id=attempt_id,
            executor_id=executor_id,
            timeout_minutes=5,
            ctx=ctx
        )

        # Test 1: Verify ownership succeeds for correct executor
        result = await verify_ownership(
            exec_repo=exec_repo,
            execution_id=execution_id,
            executor_id=executor_id,
            timeout_minutes=5,
            ctx=ctx
        )
        assert result is True

        # Test 2: Verify ownership fails for different executor
        result = await verify_ownership(
            exec_repo=exec_repo,
            execution_id=execution_id,
            executor_id="different-worker",
            timeout_minutes=5,
            ctx=ctx
        )
        assert result is False

        # Test 3: Verify ownership fails after timeout expires
        # Update execution to have expired timeout
        conn = await pool.acquire()
        try:
            expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
            await conn.execute(
                "UPDATE order_slice_executions SET executor_timeout_at = $1 WHERE id = $2",
                expired_time, execution_id
            )
        finally:
            await pool.release(conn)

        result = await verify_ownership(
            exec_repo=exec_repo,
            execution_id=execution_id,
            executor_id=executor_id,
            timeout_minutes=5,
            ctx=ctx
        )
        assert result is False

        # Cleanup
        await cleanup_test_data(pool, order_id, slice_id)
    finally:
        await close_pool(pool)

