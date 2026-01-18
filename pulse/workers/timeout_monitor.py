"""Timeout monitor for detecting and recovering stuck executions.

This monitor:
1. Runs periodically (every 1 minute)
2. Detects executions stuck in CLAIMED or PLACED status with expired timeout
3. Marks them as COMPLETED with EXECUTOR_TIMEOUT result
4. Provides crash recovery for executor failures

This implements the timeout mechanism from doc/requirements/003.order_slice_execution_feature.md
"""

import asyncio
import asyncpg
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pulse.repositories.execution_repository import ExecutionRepository
from pulse.repositories.order_slice_repository import OrderSliceRepository
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger

logger = get_logger("pulse.workers.timeout_monitor")


async def recover_timed_out_executions(
    exec_repo: ExecutionRepository,
    slice_repo: OrderSliceRepository,
    ctx: RequestContext
) -> int:
    """Recover executions that have timed out (executor crashed or became unresponsive).

    Args:
        exec_repo: Execution repository
        slice_repo: Order slice repository
        ctx: Request context for tracing

    Returns:
        Number of executions recovered
    """
    try:
        # Find all timed-out executions
        timed_out_executions = await exec_repo.find_timed_out_executions(ctx)

        if not timed_out_executions:
            return 0

        logger.warning("Found timed-out executions", ctx, data={
            "count": len(timed_out_executions)
        })

        recovered_count = 0

        for execution in timed_out_executions:
            execution_id = execution['id']
            slice_id = execution['slice_id']

            try:
                # Mark execution as COMPLETED with EXECUTOR_TIMEOUT result
                await exec_repo.update_execution_status(
                    execution_id=execution_id,
                    execution_status='COMPLETED',
                    execution_result='EXECUTOR_TIMEOUT',
                    error_code='EXECUTOR_TIMEOUT',
                    error_message=f"Executor {execution['executor_id']} timed out",
                    ctx=ctx
                )

                # Update slice status to COMPLETED
                # Copy filled_quantity and average_price from execution (may be partial fill)
                conn = await slice_repo.get_connection()
                try:
                    await conn.execute(
                        """
                        UPDATE order_slices
                        SET status = 'COMPLETED',
                            filled_quantity = $2,
                            average_price = $3,
                            updated_at = $4
                        WHERE id = $1
                        """,
                        slice_id,
                        execution.get('filled_quantity', 0),
                        execution.get('average_price'),
                        datetime.now(timezone.utc)
                    )
                finally:
                    await slice_repo.release_connection(conn)

                logger.warning("Recovered timed-out execution", ctx, data={
                    "execution_id": execution_id,
                    "slice_id": slice_id,
                    "executor_id": execution['executor_id'],
                    "filled_quantity": execution.get('filled_quantity', 0)
                })

                recovered_count += 1

            except Exception as e:
                logger.error("Failed to recover timed-out execution", ctx, data={
                    "execution_id": execution_id,
                    "slice_id": slice_id,
                    "error": str(e)
                })

        return recovered_count

    except Exception as e:
        logger.error("Failed to recover timed-out executions", ctx, data={"error": str(e)})
        raise


async def run_timeout_monitor(
    pool: asyncpg.Pool,
    check_interval_seconds: int = 60
):
    """Run the timeout monitor loop.

    Args:
        pool: Database connection pool
        check_interval_seconds: Seconds to wait between checks (default: 60)
    """
    logger.info("Timeout monitor started", data={
        "check_interval_seconds": check_interval_seconds
    })

    exec_repo = ExecutionRepository(pool)
    slice_repo = OrderSliceRepository(pool)

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

            # Check for and recover timed-out executions
            recovered_count = await recover_timed_out_executions(exec_repo, slice_repo, ctx)

            if recovered_count > 0:
                logger.info("Timeout monitor check completed", ctx, data={
                    "recovered_count": recovered_count
                })

        except asyncio.CancelledError:
            logger.info("Timeout monitor cancelled")
            break

        except Exception as e:
            logger.error("Timeout monitor error", data={"error": str(e)})

        # Wait before next check
        await asyncio.sleep(check_interval_seconds)

    logger.info("Timeout monitor stopped")

