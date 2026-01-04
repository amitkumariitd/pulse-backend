"""Timeout monitor for detecting and recovering stuck orders.

This monitor:
1. Runs periodically (every 1-5 minutes)
2. Detects orders stuck in IN_PROGRESS status for > 5 minutes
3. Marks them as FAILED with timeout error message
4. Provides crash recovery for pod failures

This implements Pattern 5 from doc/guides/concurrency.md
"""

import asyncio
import asyncpg
import time
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger

logger = get_logger("pulse.workers.timeout_monitor")


async def recover_stuck_orders(
    pool: asyncpg.Pool,
    timeout_minutes: int,
    ctx: RequestContext
) -> int:
    """Recover orders stuck in IN_PROGRESS status.
    
    Args:
        pool: Database connection pool
        timeout_minutes: Minutes after which an IN_PROGRESS order is considered stuck
        ctx: Request context for tracing
        
    Returns:
        Number of orders recovered
    """
    conn = await pool.acquire()
    try:
        # Calculate timeout threshold in microseconds
        # updated_at is stored as Unix microseconds
        timeout_micros = timeout_minutes * 60 * 1_000_000
        current_time_micros = int(time.time() * 1_000_000)
        threshold_micros = current_time_micros - timeout_micros
        
        # Update stuck orders to FAILED
        result = await conn.execute(
            """
            UPDATE orders
            SET order_queue_status = 'FAILED',
                order_queue_skip_reason = $1,
                updated_at = $2,
                request_id = $3
            WHERE order_queue_status = 'IN_PROGRESS'
              AND updated_at < $4
            """,
            f"Processing timeout - worker may have crashed (timeout: {timeout_minutes} minutes)",
            current_time_micros,
            ctx.request_id,
            threshold_micros
        )
        
        # Extract count from result (format: "UPDATE N")
        count = int(result.split()[-1]) if result else 0
        
        if count > 0:
            logger.warning("Recovered stuck orders", ctx, data={
                "count": count,
                "timeout_minutes": timeout_minutes
            })
        
        return count
        
    except asyncpg.PostgresError as e:
        logger.error("Failed to recover stuck orders", ctx, data={"error": str(e)})
        raise
    finally:
        await pool.release(conn)


async def run_timeout_monitor(
    pool: asyncpg.Pool,
    check_interval_seconds: int = 60,
    timeout_minutes: int = 5
):
    """Run the timeout monitor loop.
    
    Args:
        pool: Database connection pool
        check_interval_seconds: Seconds to wait between checks (default: 60)
        timeout_minutes: Minutes after which an order is considered stuck (default: 5)
    """
    logger.info("Timeout monitor started", data={
        "check_interval_seconds": check_interval_seconds,
        "timeout_minutes": timeout_minutes
    })
    
    while True:
        try:
            # Create context for this monitor iteration
            ctx = RequestContext(
                trace_id=generate_trace_id(),
                trace_source="PULSE_BACKGROUND:timeout_monitor",
                request_id=generate_request_id(),
                request_source="PULSE_BACKGROUND:timeout_monitor",
                span_source="PULSE_BACKGROUND:timeout_monitor"
            )
            
            # Check for and recover stuck orders
            recovered_count = await recover_stuck_orders(pool, timeout_minutes, ctx)
            
            if recovered_count > 0:
                logger.info("Timeout monitor check completed", ctx, data={
                    "recovered_count": recovered_count
                })
            
        except Exception as e:
            logger.error("Timeout monitor error", data={"error": str(e)})
        
        # Wait before next check
        await asyncio.sleep(check_interval_seconds)

