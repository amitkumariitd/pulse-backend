"""Integration tests for ExecutionRepository."""
import pytest
import asyncio
import asyncpg
from datetime import datetime, timezone
from decimal import Decimal
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings
from pulse.repositories.execution_repository import ExecutionRepository
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id


@pytest.mark.asyncio
async def test_create_execution_integration():
    """Test creating an execution record in the database."""
    # Arrange
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

        # Create test order and slice
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
                    scheduled_at, status,
                    origin_trace_id, origin_trace_source, origin_request_id, origin_request_source,
                    request_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                slice_id, order_id, "NSE:RELIANCE", "BUY", 100, 1,
                datetime.now(timezone.utc), "PENDING",
                ctx.trace_id, ctx.trace_source, ctx.request_id, ctx.request_source,
                ctx.request_id
            )
        finally:
            await pool.release(conn)

        # Test execution repository
        exec_repo = ExecutionRepository(pool)
        execution_id = f"test_exec_{generate_request_id()[:8]}"
        attempt_id = f"attempt-{generate_request_id()[:8]}"

        # Act
        result = await exec_repo.create_execution(
            execution_id=execution_id,
            slice_id=slice_id,
            attempt_id=attempt_id,
            executor_id="test-worker-1",
            timeout_minutes=5,
            ctx=ctx
        )

        # Assert
        assert result is not None
        assert result['id'] == execution_id
        assert result['slice_id'] == slice_id
        assert result['attempt_id'] == attempt_id
        assert result['executor_id'] == "test-worker-1"
        assert result['execution_status'] == 'CLAIMED'
        assert result['broker_order_id'] is None
        assert result['execution_result'] is None

        # Cleanup
        conn = await pool.acquire()
        try:
            await conn.execute("DELETE FROM order_slice_executions WHERE id = $1", execution_id)
            await conn.execute("DELETE FROM order_slices WHERE id = $1", slice_id)
            await conn.execute("DELETE FROM orders WHERE id = $1", order_id)
        finally:
            await pool.release(conn)
    finally:
        await close_pool(pool)




