"""Execution worker for executing order slices on broker.

This worker:
1. Picks PENDING slices using SELECT FOR UPDATE SKIP LOCKED
2. Creates execution record (claims ownership)
3. Validates slice parameters
4. Places order with broker (Zerodha)
5. Monitors order status until completion
6. Updates slice and execution records with results
"""

import asyncio
import asyncpg
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal

from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.repositories.execution_repository import ExecutionRepository
from pulse.repositories.broker_event_repository import BrokerEventRepository
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger
from config.settings import get_settings

logger = get_logger("pulse.workers.execution")


def generate_execution_id() -> str:
    """Generate unique ID for execution record.
    
    Format: exec + Unix timestamp (seconds) + 12 hexadecimal characters
    Example: exec1735228800a1b2c3d4e5f6
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)
    return f"exec{timestamp}{random_hex}"


def generate_attempt_id() -> str:
    """Generate unique attempt ID for this execution attempt.
    
    Format: attempt-{uuid4}
    Example: attempt-550e8400-e29b-41d4-a716-446655440000
    """
    return f"attempt-{uuid.uuid4()}"


def generate_event_id() -> str:
    """Generate unique ID for broker event.
    
    Format: evt + Unix timestamp (seconds) + 12 hexadecimal characters
    Example: evt1735228800a1b2c3d4e5f6
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)
    return f"evt{timestamp}{random_hex}"


async def get_pending_slices(
    pool: asyncpg.Pool,
    batch_size: int,
    ctx: RequestContext
) -> list[dict]:
    """Get pending slices ready for execution using pessimistic locking.
    
    Uses SELECT FOR UPDATE SKIP LOCKED to claim slices atomically.
    
    Args:
        pool: Database connection pool
        batch_size: Maximum number of slices to fetch
        ctx: Request context
        
    Returns:
        List of slice records ready for execution
    """
    conn = await pool.acquire()
    try:
        now = datetime.now(timezone.utc)
        
        # Get slices that are PENDING and scheduled_at <= NOW
        # Use FOR UPDATE SKIP LOCKED for pessimistic locking
        results = await conn.fetch(
            """
            SELECT * FROM order_slices
            WHERE status = 'PENDING'
              AND scheduled_at <= $1
            ORDER BY scheduled_at ASC
            LIMIT $2
            FOR UPDATE SKIP LOCKED
            """,
            now,
            batch_size
        )
        
        return [dict(r) for r in results]
        
    finally:
        await pool.release(conn)


async def update_slice_status(
    slice_repo: OrderSliceRepository,
    slice_id: str,
    status: str,
    filled_quantity: Optional[int] = None,
    average_price: Optional[Decimal] = None,
    ctx: RequestContext = None
) -> None:
    """Update order slice status and execution results.
    
    Args:
        slice_repo: Order slice repository
        slice_id: Slice ID to update
        status: New status
        filled_quantity: Filled quantity (if available)
        average_price: Average fill price (if available)
        ctx: Request context
    """
    conn = await slice_repo.get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        # Build dynamic update
        updates = ["status = $2", "updated_at = $3"]
        params = [slice_id, status, now]
        param_idx = 4
        
        if filled_quantity is not None:
            updates.append(f"filled_quantity = ${param_idx}")
            params.append(filled_quantity)
            param_idx += 1
        
        if average_price is not None:
            updates.append(f"average_price = ${param_idx}")
            params.append(average_price)
            param_idx += 1
        
        query = f"""
            UPDATE order_slices
            SET {', '.join(updates)}
            WHERE id = $1
        """
        
        await conn.execute(query, *params)

    finally:
        await slice_repo.release_connection(conn)


async def process_single_slice(
    slice_data: dict,
    slice_repo: OrderSliceRepository,
    exec_repo: ExecutionRepository,
    event_repo: BrokerEventRepository,
    zerodha_client: ZerodhaClient,
    executor_id: str,
    timeout_minutes: int,
    ctx: RequestContext
) -> bool:
    """Process a single order slice - place order and monitor execution.

    Args:
        slice_data: Slice record from database
        slice_repo: Order slice repository
        exec_repo: Execution repository
        event_repo: Broker event repository
        zerodha_client: Zerodha broker client
        executor_id: Worker ID
        timeout_minutes: Timeout in minutes
        ctx: Request context (worker context)

    Returns:
        True if successfully processed, False otherwise
    """
    slice_id = slice_data['id']

    # Create execution context using slice's request_id
    exec_ctx = RequestContext(
        trace_id=generate_trace_id(),
        trace_source="PULSE_BACKGROUND:execution_worker",
        request_id=slice_data['request_id'],
        request_source="PULSE_BACKGROUND:execution_worker",
        span_source="PULSE_BACKGROUND:execution_worker"
    )

    execution_id = generate_execution_id()
    attempt_id = generate_attempt_id()
    event_sequence = 0

    try:
        # Step 1: Update slice status to EXECUTING
        await update_slice_status(slice_repo, slice_id, 'EXECUTING', ctx=exec_ctx)

        # Step 2: Create execution record (claim ownership)
        execution = await exec_repo.create_execution(
            execution_id=execution_id,
            slice_id=slice_id,
            attempt_id=attempt_id,
            executor_id=executor_id,
            timeout_minutes=timeout_minutes,
            ctx=exec_ctx
        )

        logger.info("Execution claimed", exec_ctx, data={
            "execution_id": execution_id,
            "slice_id": slice_id,
            "attempt_id": attempt_id,
            "executor_id": executor_id
        })

        # Step 3: Validate slice parameters
        # TODO: Add validation logic

        # Step 4: Place order with broker
        order_request = ZerodhaOrderRequest(
            instrument=slice_data['instrument'],
            side=slice_data['side'],
            quantity=slice_data['quantity'],
            order_type=slice_data.get('order_type', 'MARKET'),
            limit_price=slice_data.get('limit_price'),
            product_type=slice_data.get('product_type', 'CNC'),
            validity=slice_data.get('validity', 'DAY')
        )

        # Place order and record broker event
        event_sequence += 1
        start_time = time.time()

        try:
            broker_response = await zerodha_client.place_order(order_request, exec_ctx)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record successful placement event
            await event_repo.create_broker_event(
                event_id=generate_event_id(),
                execution_id=execution_id,
                slice_id=slice_id,
                event_sequence=event_sequence,
                event_type='PLACE_ORDER',
                attempt_number=1,
                attempt_id=attempt_id,
                executor_id=executor_id,
                broker_name='zerodha',
                is_success=True,
                broker_order_id=broker_response.broker_order_id,
                broker_status=broker_response.status,
                broker_message=broker_response.message,
                filled_quantity=broker_response.filled_quantity,
                pending_quantity=broker_response.pending_quantity,
                average_price=broker_response.average_price,
                response_time_ms=response_time_ms,
                ctx=exec_ctx
            )

            # Update execution with broker order ID
            await exec_repo.update_execution_status(
                execution_id=execution_id,
                execution_status='PLACED',
                broker_order_id=broker_response.broker_order_id,
                broker_order_status=broker_response.status,
                filled_quantity=broker_response.filled_quantity,
                average_price=broker_response.average_price,
                ctx=exec_ctx
            )

            logger.info("Order placed with broker", exec_ctx, data={
                "execution_id": execution_id,
                "broker_order_id": broker_response.broker_order_id,
                "status": broker_response.status
            })

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record failed placement event
            await event_repo.create_broker_event(
                event_id=generate_event_id(),
                execution_id=execution_id,
                slice_id=slice_id,
                event_sequence=event_sequence,
                event_type='PLACE_ORDER',
                attempt_number=1,
                attempt_id=attempt_id,
                executor_id=executor_id,
                broker_name='zerodha',
                is_success=False,
                error_code='PLACEMENT_FAILED',
                error_message=str(e),
                response_time_ms=response_time_ms,
                ctx=exec_ctx
            )

            raise

        # Step 5: Monitor order status until completion
        # For now, assume immediate completion (will add polling logic later)
        # TODO: Add polling loop for LIMIT orders

        # Step 6: Finalize execution
        await exec_repo.update_execution_status(
            execution_id=execution_id,
            execution_status='COMPLETED',
            execution_result='SUCCESS',
            ctx=exec_ctx
        )

        # Step 7: Update slice with final results
        await update_slice_status(
            slice_repo,
            slice_id,
            'COMPLETED',
            filled_quantity=broker_response.filled_quantity,
            average_price=broker_response.average_price,
            ctx=exec_ctx
        )

        logger.info("Slice execution completed", exec_ctx, data={
            "execution_id": execution_id,
            "slice_id": slice_id,
            "filled_quantity": broker_response.filled_quantity,
            "average_price": str(broker_response.average_price) if broker_response.average_price else None
        })

        return True

    except Exception as e:
        logger.error("Slice execution failed", exec_ctx, data={
            "execution_id": execution_id,
            "slice_id": slice_id,
            "error": str(e)
        })

        # Mark execution as failed
        try:
            await exec_repo.update_execution_status(
                execution_id=execution_id,
                execution_status='COMPLETED',
                execution_result='BROKER_REJECTED',
                error_code='EXECUTION_FAILED',
                error_message=str(e),
                ctx=exec_ctx
            )

            # Mark slice as completed with failure
            await update_slice_status(slice_repo, slice_id, 'COMPLETED', ctx=exec_ctx)

        except Exception as update_error:
            logger.error("Failed to update execution status", exec_ctx, data={
                "execution_id": execution_id,
                "error": str(update_error)
            })

        return False


async def run_execution_worker(
    pool: asyncpg.Pool,
    poll_interval_seconds: int = 5,
    batch_size: int = 10,
    timeout_minutes: int = 5
):
    """Run the execution worker loop.

    Args:
        pool: Database connection pool
        poll_interval_seconds: Seconds to wait between polls when no work found
        batch_size: Maximum number of slices to process per iteration
        timeout_minutes: Timeout for each execution
    """
    settings = get_settings()
    executor_id = f"exec-worker-{uuid.uuid4().hex[:8]}"

    logger.info("Execution worker started", data={
        "executor_id": executor_id,
        "poll_interval_seconds": poll_interval_seconds,
        "batch_size": batch_size,
        "timeout_minutes": timeout_minutes
    })

    slice_repo = OrderSliceRepository(pool)
    exec_repo = ExecutionRepository(pool)
    event_repo = BrokerEventRepository(pool)

    # Initialize Zerodha client (using mock for now)
    zerodha_client = ZerodhaClient(
        api_key=settings.zerodha_api_key if hasattr(settings, 'zerodha_api_key') else "mock_key",
        access_token=settings.zerodha_access_token if hasattr(settings, 'zerodha_access_token') else None,
        use_mock=True  # TODO: Set to False for production
    )

    while True:
        try:
            # Create context for this worker iteration
            ctx = RequestContext(
                trace_id=generate_trace_id(),
                trace_source="PULSE_BACKGROUND:execution_worker",
                request_id=generate_request_id(),
                request_source="PULSE_BACKGROUND:execution_worker",
                span_source="PULSE_BACKGROUND:execution_worker"
            )

            # Get pending slices ready for execution
            pending_slices = await get_pending_slices(pool, batch_size, ctx)

            if not pending_slices:
                # No work to do, sleep and retry
                await asyncio.sleep(poll_interval_seconds)
                continue

            logger.info("Found pending slices", ctx, data={
                "count": len(pending_slices)
            })

            # Process each slice
            for slice_data in pending_slices:
                await process_single_slice(
                    slice_data,
                    slice_repo,
                    exec_repo,
                    event_repo,
                    zerodha_client,
                    executor_id,
                    timeout_minutes,
                    ctx
                )

        except asyncio.CancelledError:
            logger.info("Execution worker cancelled", data={"executor_id": executor_id})
            break

        except Exception as e:
            logger.error("Execution worker error", data={
                "executor_id": executor_id,
                "error": str(e)
            })
            # Continue running despite errors
            await asyncio.sleep(poll_interval_seconds)

    # Cleanup
    await zerodha_client.close()
    logger.info("Execution worker stopped", data={"executor_id": executor_id})

