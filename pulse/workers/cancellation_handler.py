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
from datetime import datetime, timezone
from typing import List

from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.repositories.execution_repository import ExecutionRepository
from pulse.repositories.broker_event_repository import BrokerEventRepository
from pulse.brokers.zerodha_client import ZerodhaClient
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger

logger = get_logger("pulse.workers.cancellation_handler")


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
                    try:
                        await zerodha_client.cancel_order(
                            execution['broker_order_id'],
                            ctx
                        )
                        
                        logger.info("Cancelled order at broker", ctx, data={
                            "slice_id": slice_id,
                            "broker_order_id": execution['broker_order_id']
                        })
                        
                        cancelled_executions += 1
                        
                    except Exception as e:
                        logger.warning("Failed to cancel order at broker", ctx, data={
                            "slice_id": slice_id,
                            "broker_order_id": execution['broker_order_id'],
                            "error": str(e)
                        })
                
                # Mark execution as SKIPPED
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

