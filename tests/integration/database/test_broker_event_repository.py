"""Integration tests for BrokerEventRepository."""
import pytest
import asyncio
import asyncpg
from datetime import datetime, timezone
from decimal import Decimal
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings
from pulse.repositories.broker_event_repository import BrokerEventRepository
from pulse.repositories.execution_repository import ExecutionRepository
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id


@pytest.mark.asyncio
async def test_create_broker_event_place_order_integration():
    """Test creating a PLACE_ORDER broker event in the database."""
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

        # Create test data
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
                ctx.request_id  # order_slices only has request_id, not origin_* columns
            )

            execution_id = f"test_exec_{generate_request_id()[:8]}"
            now = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO order_slice_executions (
                    id, slice_id, attempt_id, executor_id, execution_status,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    placement_attempts, request_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                execution_id, slice_id, f"attempt-{generate_request_id()[:8]}",
                "test-worker-1", "CLAIMED",
                now, now, now, 0, ctx.request_id
            )
        finally:
            await pool.release(conn)

        # Test broker event repository
        event_repo = BrokerEventRepository(pool)
        event_id = f"test_evt_{generate_request_id()[:8]}"

        # Act
        result = await event_repo.create_broker_event(
            event_id=event_id,
            execution_id=execution_id,
            slice_id=slice_id,
            event_sequence=1,
            event_type='PLACE_ORDER',
            attempt_number=1,
            attempt_id=f"attempt-{generate_request_id()[:8]}",
            executor_id="test-worker-1",
            broker_name='zerodha',
            is_success=True,
            broker_order_id='ZH240101test123',
            broker_status='COMPLETE',
            filled_quantity=100,
            average_price=Decimal('1250.50'),
            response_time_ms=250,
            ctx=ctx
        )

        # Assert
        assert result is not None
        assert result['id'] == event_id
        assert result['execution_id'] == execution_id
        assert result['event_type'] == 'PLACE_ORDER'
        assert result['is_success'] is True
        assert result['broker_order_id'] == 'ZH240101test123'
        assert result['filled_quantity'] == 100
        assert result['average_price'] == Decimal('1250.50')

        # Cleanup
        conn = await pool.acquire()
        try:
            await conn.execute("DELETE FROM order_slice_broker_events WHERE id = $1", event_id)
            await conn.execute("DELETE FROM order_slice_executions WHERE id = $1", execution_id)
            await conn.execute("DELETE FROM order_slices WHERE id = $1", slice_id)
            await conn.execute("DELETE FROM orders WHERE id = $1", order_id)
        finally:
            await pool.release(conn)
    finally:
        await close_pool(pool)

