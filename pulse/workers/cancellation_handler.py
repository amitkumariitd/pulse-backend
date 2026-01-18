"""Parent order cancellation handler.

This handler:
1. Monitors for parent order cancellations
2. Skips all pending slices for cancelled orders
3. Cancels active executions at broker
4. Marks executing slices as SKIPPED

This implements the cancellation logic from doc/requirements/003.order_slice_execution_feature.md
"""

import asyncio
import asyncpg
import time
import uuid
from datetime import datetime, timezone
from typing import List

from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.repositories.execution_repository import ExecutionRepository
from pulse.repositories.broker_event_repository import BrokerEventRepository
from pulse.brokers.zerodha_client import ZerodhaClient
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger

logger = get_logger("pulse.workers.cancellation_handler")


def generate_event_id() -> str:
    """Generate unique event ID."""
    return f"evt-{uuid.uuid4()}"


async def handle_order_cancellation(
    order_id: str,
    slice_repo: OrderSliceRepository,
    exec_repo: ExecutionRepository,
    event_repo: BrokerEventRepository,
    zerodha_client: ZerodhaClient,
    ctx: RequestContext
) -> dict:
    """Handle cancellation of a parent order.
    
    Args:
        order_id: Parent order ID that was cancelled
        slice_repo: Order slice repository
        exec_repo: Execution repository
        event_repo: Broker event repository
        zerodha_client: Zerodha broker client
        ctx: Request context
        
    Returns:
        Dict with counts of skipped slices and cancelled executions
    """
    skipped_slices = 0
    cancelled_executions = 0
    
    try:
        # Step 1: Find all non-completed slices for this order
        conn = await slice_repo.get_connection()
        try:
            slices = await conn.fetch(
                """
                SELECT * FROM order_slices
                WHERE order_id = $1
                  AND status IN ('PENDING', 'EXECUTING')
                ORDER BY sequence_number ASC
                """,
                order_id
            )
        finally:
            await slice_repo.release_connection(conn)
        
        if not slices:
            logger.info("No slices to cancel", ctx, data={"order_id": order_id})
            return {"skipped_slices": 0, "cancelled_executions": 0}
        
        logger.info("Found slices to cancel", ctx, data={
            "order_id": order_id,
            "count": len(slices)
        })
        
        # Step 2: Process each slice
        for slice_record in slices:
            slice_id = slice_record['id']
            slice_status = slice_record['status']
            
            if slice_status == 'PENDING':
                # Just mark as SKIPPED
                conn = await slice_repo.get_connection()
                try:
                    await conn.execute(
                        """
                        UPDATE order_slices
                        SET status = 'SKIPPED',
                            updated_at = $2
                        WHERE id = $1
                        """,
                        slice_id,
                        datetime.now(timezone.utc)
                    )
                    skipped_slices += 1
                    
                    logger.info("Skipped pending slice", ctx, data={
                        "slice_id": slice_id,
                        "order_id": order_id
                    })
                finally:
                    await slice_repo.release_connection(conn)
                    
            elif slice_status == 'EXECUTING':
                # Find active execution
                execution = await exec_repo.get_execution_by_slice_id(slice_id, ctx)

                if not execution:
                    # No execution found, just mark slice as SKIPPED
                    conn = await slice_repo.get_connection()
                    try:
                        await conn.execute(
                            """
                            UPDATE order_slices
                            SET status = 'SKIPPED',
                                updated_at = $2
                            WHERE id = $1
                            """,
                            slice_id,
                            datetime.now(timezone.utc)
                        )
                        skipped_slices += 1
                    finally:
                        await slice_repo.release_connection(conn)
                    continue

                # If broker_order_id exists, try to cancel at broker
                if execution.get('broker_order_id'):
                    broker_order_id = execution['broker_order_id']
                    execution_id = execution['id']
                    attempt_id = execution.get('attempt_id', 'unknown')
                    executor_id = execution.get('executor_id', 'cancellation-handler')

                    # Get next event sequence number
                    conn = await event_repo.get_connection()
                    try:
                        event_seq_result = await conn.fetchval(
                            """
                            SELECT COALESCE(MAX(event_sequence), 0) + 1
                            FROM order_slice_broker_events
                            WHERE execution_id = $1
                            """,
                            execution_id
                        )
                        event_sequence = event_seq_result or 1
                    finally:
                        await event_repo.release_connection(conn)

                    start_time = time.time()
                    cancel_success = False
                    error_code = None
                    error_message = None

                    try:
                        cancel_response = await zerodha_client.cancel_order(
                            broker_order_id,
                            ctx
                        )

                        response_time_ms = int((time.time() - start_time) * 1000)
                        cancel_success = True

                        logger.info("Cancelled order at broker", ctx, data={
                            "slice_id": slice_id,
                            "broker_order_id": broker_order_id,
                            "status": cancel_response.status
                        })

                        # Record successful cancellation event
                        await event_repo.create_broker_event(
                            event_id=generate_event_id(),
                            execution_id=execution_id,
                            slice_id=slice_id,
                            event_sequence=event_sequence,
                            event_type='CANCEL_REQUEST',
                            attempt_number=1,
                            attempt_id=attempt_id,
                            executor_id=executor_id,
                            broker_name='zerodha',
                            is_success=True,
                            broker_order_id=broker_order_id,
                            broker_status=cancel_response.status,
                            broker_message=cancel_response.message,
                            response_time_ms=response_time_ms,
                            ctx=ctx
                        )

                        cancelled_executions += 1

                    except Exception as e:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        error_code = 'CANCEL_FAILED'
                        error_message = str(e)

                        logger.warning("Failed to cancel order at broker", ctx, data={
                            "slice_id": slice_id,
                            "broker_order_id": broker_order_id,
                            "error": error_message
                        })

                        # Record failed cancellation event
                        await event_repo.create_broker_event(
                            event_id=generate_event_id(),
                            execution_id=execution_id,
                            slice_id=slice_id,
                            event_sequence=event_sequence,
                            event_type='CANCEL_REQUEST',
                            attempt_number=1,
                            attempt_id=attempt_id,
                            executor_id=executor_id,
                            broker_name='zerodha',
                            is_success=False,
                            broker_order_id=broker_order_id,
                            error_code=error_code,
                            error_message=error_message,
                            response_time_ms=response_time_ms,
                            ctx=ctx
                        )

                # Mark execution as SKIPPED (regardless of broker cancellation success)
                await exec_repo.update_execution_status(
                    execution_id=execution['id'],
                    execution_status='SKIPPED',
                    ctx=ctx
                )

                # Mark slice as SKIPPED
                conn = await slice_repo.get_connection()
                try:
                    await conn.execute(
                        """
                        UPDATE order_slices
                        SET status = 'SKIPPED',
                            updated_at = $2
                        WHERE id = $1
                        """,
                        slice_id,
                        datetime.now(timezone.utc)
                    )
                    skipped_slices += 1
                finally:
                    await slice_repo.release_connection(conn)
        
        logger.info("Order cancellation handled", ctx, data={
            "order_id": order_id,
            "skipped_slices": skipped_slices,
            "cancelled_executions": cancelled_executions
        })
        
        return {
            "skipped_slices": skipped_slices,
            "cancelled_executions": cancelled_executions
        }
        
    except Exception as e:
        logger.error("Failed to handle order cancellation", ctx, data={
            "order_id": order_id,
            "error": str(e)
        })
        raise

