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
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest, ZerodhaOrderResponse
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


async def verify_ownership(
    exec_repo: ExecutionRepository,
    execution_id: str,
    executor_id: str,
    timeout_minutes: int,
    ctx: RequestContext
) -> bool:
    """Verify executor still owns this execution and extend timeout.

    Args:
        exec_repo: Execution repository
        execution_id: Execution ID to verify
        executor_id: Expected executor ID
        timeout_minutes: Minutes to extend timeout
        ctx: Request context

    Returns:
        True if ownership verified and extended, False otherwise
    """
    conn = await exec_repo.get_connection()
    try:
        now = datetime.now(timezone.utc)

        # Re-fetch execution record
        result = await conn.fetchrow(
            """
            SELECT executor_id, executor_timeout_at
            FROM order_slice_executions
            WHERE id = $1
            """,
            execution_id
        )

        if not result:
            logger.warning("Execution not found during ownership verification", ctx, data={
                "execution_id": execution_id
            })
            return False

        # Check if executor_id matches
        if result['executor_id'] != executor_id:
            logger.warning("Ownership lost - executor_id mismatch", ctx, data={
                "execution_id": execution_id,
                "expected_executor_id": executor_id,
                "actual_executor_id": result['executor_id']
            })
            return False

        # Check if timeout has expired
        if result['executor_timeout_at'] < now:
            logger.warning("Ownership lost - timeout expired", ctx, data={
                "execution_id": execution_id,
                "executor_timeout_at": result['executor_timeout_at'].isoformat(),
                "current_time": now.isoformat()
            })
            return False

        # Ownership verified - extend timeout and update heartbeat
        await exec_repo.update_heartbeat(execution_id, timeout_minutes, ctx)

        return True

    finally:
        await exec_repo.release_connection(conn)


async def place_order_with_retry(
    zerodha_client: ZerodhaClient,
    order_request: ZerodhaOrderRequest,
    execution_id: str,
    slice_id: str,
    attempt_id: str,
    executor_id: str,
    event_repo: BrokerEventRepository,
    exec_repo: ExecutionRepository,
    event_sequence: int,
    max_attempts: int,
    timeout_minutes: int,
    ctx: RequestContext
) -> tuple[Optional[ZerodhaOrderResponse], int]:
    """Place order with retry logic for network failures.

    Args:
        zerodha_client: Zerodha broker client
        order_request: Order details
        execution_id: Execution ID
        slice_id: Slice ID
        attempt_id: Attempt ID
        executor_id: Executor ID
        event_repo: Broker event repository
        exec_repo: Execution repository
        event_sequence: Current event sequence number
        max_attempts: Maximum placement attempts
        timeout_minutes: Timeout in minutes for ownership verification
        ctx: Request context

    Returns:
        Tuple of (broker_response, final_event_sequence)
    """
    for attempt_number in range(1, max_attempts + 1):
        # Verify ownership before each attempt
        if not await verify_ownership(exec_repo, execution_id, executor_id, timeout_minutes, ctx):
            logger.warning("Lost ownership, aborting placement", ctx, data={
                "execution_id": execution_id,
                "attempt_number": attempt_number
            })
            return None, event_sequence

        event_sequence += 1
        start_time = time.time()

        try:
            broker_response = await zerodha_client.place_order(order_request, ctx)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record successful placement event
            await event_repo.create_broker_event(
                event_id=generate_event_id(),
                execution_id=execution_id,
                slice_id=slice_id,
                event_sequence=event_sequence,
                event_type='PLACE_ORDER',
                attempt_number=attempt_number,
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
                ctx=ctx
            )

            logger.info("Order placed successfully", ctx, data={
                "execution_id": execution_id,
                "broker_order_id": broker_response.broker_order_id,
                "attempt_number": attempt_number
            })

            return broker_response, event_sequence

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_str = str(e)

            # Determine if this is a retryable error
            is_network_error = any(keyword in error_str.lower() for keyword in
                                  ['timeout', 'connection', 'network', 'unreachable'])

            # Record failed placement event
            await event_repo.create_broker_event(
                event_id=generate_event_id(),
                execution_id=execution_id,
                slice_id=slice_id,
                event_sequence=event_sequence,
                event_type='PLACE_ORDER',
                attempt_number=attempt_number,
                attempt_id=attempt_id,
                executor_id=executor_id,
                broker_name='zerodha',
                is_success=False,
                error_code='NETWORK_FAILURE' if is_network_error else 'BROKER_REJECTED',
                error_message=error_str,
                response_time_ms=response_time_ms,
                ctx=ctx
            )

            # If broker rejection (not network error), don't retry
            if not is_network_error:
                logger.error("Broker rejected order", ctx, data={
                    "execution_id": execution_id,
                    "error": error_str
                })
                raise

            # If last attempt, raise
            if attempt_number >= max_attempts:
                logger.error("Max placement attempts reached", ctx, data={
                    "execution_id": execution_id,
                    "max_attempts": max_attempts,
                    "error": error_str
                })
                raise

            # Wait before retry
            logger.warning("Placement failed, retrying", ctx, data={
                "execution_id": execution_id,
                "attempt_number": attempt_number,
                "max_attempts": max_attempts,
                "error": error_str
            })
            await asyncio.sleep(5)

    return None, event_sequence


async def monitor_order_until_complete(
    zerodha_client: ZerodhaClient,
    broker_order_id: str,
    execution_id: str,
    slice_id: str,
    attempt_id: str,
    executor_id: str,
    event_repo: BrokerEventRepository,
    exec_repo: ExecutionRepository,
    event_sequence: int,
    poll_interval_seconds: int,
    execution_timeout_minutes: int,
    executor_timeout_minutes: int,
    ctx: RequestContext
) -> tuple[ZerodhaOrderResponse, int]:
    """Monitor order status until completion or timeout.

    Args:
        zerodha_client: Zerodha broker client
        broker_order_id: Broker order ID to monitor
        execution_id: Execution ID
        slice_id: Slice ID
        attempt_id: Attempt ID
        executor_id: Executor ID
        event_repo: Broker event repository
        exec_repo: Execution repository
        event_sequence: Current event sequence number
        poll_interval_seconds: Seconds between polls
        execution_timeout_minutes: Minutes until execution times out
        executor_timeout_minutes: Minutes for executor ownership timeout
        ctx: Request context

    Returns:
        Tuple of (final_broker_response, final_event_sequence)
    """
    start_time = datetime.now(timezone.utc)
    timeout_threshold = start_time + timedelta(minutes=execution_timeout_minutes)

    while True:
        # Check if execution timeout reached
        if datetime.now(timezone.utc) >= timeout_threshold:
            logger.warning("Execution timeout reached", ctx, data={
                "execution_id": execution_id,
                "broker_order_id": broker_order_id,
                "timeout_minutes": execution_timeout_minutes
            })

            # Try to cancel order at broker
            try:
                cancel_response = await zerodha_client.cancel_order(broker_order_id, ctx)
                return cancel_response, event_sequence
            except Exception as e:
                logger.error("Failed to cancel order on timeout", ctx, data={
                    "execution_id": execution_id,
                    "broker_order_id": broker_order_id,
                    "error": str(e)
                })
                # Return last known status
                break

        # Verify ownership before polling
        if not await verify_ownership(exec_repo, execution_id, executor_id, executor_timeout_minutes, ctx):
            logger.warning("Lost ownership during monitoring, aborting", ctx, data={
                "execution_id": execution_id,
                "broker_order_id": broker_order_id
            })
            # Another executor will take over
            return None, event_sequence

        # Poll broker for status
        event_sequence += 1
        start_poll = time.time()

        try:
            broker_response = await zerodha_client.get_order_status(broker_order_id, ctx)
            response_time_ms = int((time.time() - start_poll) * 1000)

            # Record poll event
            await event_repo.create_broker_event(
                event_id=generate_event_id(),
                execution_id=execution_id,
                slice_id=slice_id,
                event_sequence=event_sequence,
                event_type='STATUS_POLL',
                attempt_number=1,
                attempt_id=attempt_id,
                executor_id=executor_id,
                broker_name='zerodha',
                is_success=True,
                broker_order_id=broker_order_id,
                broker_status=broker_response.status,
                broker_message=broker_response.message,
                filled_quantity=broker_response.filled_quantity,
                pending_quantity=broker_response.pending_quantity,
                average_price=broker_response.average_price,
                response_time_ms=response_time_ms,
                ctx=ctx
            )

            # Update execution with latest status
            await exec_repo.update_execution_status(
                execution_id=execution_id,
                execution_status='PLACED',
                broker_order_status=broker_response.status,
                filled_quantity=broker_response.filled_quantity,
                average_price=broker_response.average_price,
                ctx=ctx
            )

            # Check if order is complete
            if broker_response.status in ['COMPLETE', 'CANCELLED', 'REJECTED', 'EXPIRED']:
                logger.info("Order reached terminal status", ctx, data={
                    "execution_id": execution_id,
                    "broker_order_id": broker_order_id,
                    "status": broker_response.status,
                    "filled_quantity": broker_response.filled_quantity
                })
                return broker_response, event_sequence

            # Log partial fills
            if broker_response.filled_quantity > 0:
                logger.info("Order partially filled", ctx, data={
                    "execution_id": execution_id,
                    "broker_order_id": broker_order_id,
                    "filled_quantity": broker_response.filled_quantity,
                    "pending_quantity": broker_response.pending_quantity
                })

        except Exception as e:
            response_time_ms = int((time.time() - start_poll) * 1000)

            # Record failed poll event
            await event_repo.create_broker_event(
                event_id=generate_event_id(),
                execution_id=execution_id,
                slice_id=slice_id,
                event_sequence=event_sequence,
                event_type='STATUS_POLL',
                attempt_number=1,
                attempt_id=attempt_id,
                executor_id=executor_id,
                broker_name='zerodha',
                is_success=False,
                error_code='POLL_FAILED',
                error_message=str(e),
                response_time_ms=response_time_ms,
                ctx=ctx
            )

            logger.warning("Failed to poll order status", ctx, data={
                "execution_id": execution_id,
                "broker_order_id": broker_order_id,
                "error": str(e)
            })

        # Wait before next poll
        await asyncio.sleep(poll_interval_seconds)

    # Should not reach here, but return None if we do
    return None, event_sequence


async def process_single_slice(
    slice_data: dict,
    slice_repo: OrderSliceRepository,
    exec_repo: ExecutionRepository,
    event_repo: BrokerEventRepository,
    zerodha_client: ZerodhaClient,
    executor_id: str,
    executor_timeout_minutes: int,
    execution_timeout_minutes: int,
    poll_interval_seconds: int,
    max_placement_attempts: int,
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
        executor_timeout_minutes: Timeout for executor ownership
        execution_timeout_minutes: Timeout for order execution
        poll_interval_seconds: Seconds between status polls
        max_placement_attempts: Maximum placement retry attempts
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
            timeout_minutes=executor_timeout_minutes,
            ctx=exec_ctx
        )

        logger.info("Execution claimed", exec_ctx, data={
            "execution_id": execution_id,
            "slice_id": slice_id,
            "attempt_id": attempt_id,
            "executor_id": executor_id
        })

        # Step 3: Validate slice parameters
        # Basic validation
        if slice_data['quantity'] <= 0:
            raise ValueError("Invalid quantity")
        if slice_data.get('order_type') == 'LIMIT' and not slice_data.get('limit_price'):
            raise ValueError("Limit price required for LIMIT orders")

        # Step 4: Place order with broker (with retry logic)
        order_request = ZerodhaOrderRequest(
            instrument=slice_data['instrument'],
            side=slice_data['side'],
            quantity=slice_data['quantity'],
            order_type=slice_data.get('order_type', 'MARKET'),
            limit_price=slice_data.get('limit_price'),
            product_type=slice_data.get('product_type', 'CNC'),
            validity=slice_data.get('validity', 'DAY')
        )

        broker_response, event_sequence = await place_order_with_retry(
            zerodha_client=zerodha_client,
            order_request=order_request,
            execution_id=execution_id,
            slice_id=slice_id,
            attempt_id=attempt_id,
            executor_id=executor_id,
            event_repo=event_repo,
            exec_repo=exec_repo,
            event_sequence=event_sequence,
            max_attempts=max_placement_attempts,
            timeout_minutes=executor_timeout_minutes,
            ctx=exec_ctx
        )

        if not broker_response:
            # Lost ownership during placement
            logger.warning("Lost ownership during placement", exec_ctx, data={
                "execution_id": execution_id,
                "slice_id": slice_id
            })
            return False

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

        # Step 5: Monitor order status until completion
        if broker_response.status not in ['COMPLETE', 'CANCELLED', 'REJECTED', 'EXPIRED']:
            # Order needs monitoring
            final_response, event_sequence = await monitor_order_until_complete(
                zerodha_client=zerodha_client,
                broker_order_id=broker_response.broker_order_id,
                execution_id=execution_id,
                slice_id=slice_id,
                attempt_id=attempt_id,
                executor_id=executor_id,
                event_repo=event_repo,
                exec_repo=exec_repo,
                event_sequence=event_sequence,
                poll_interval_seconds=poll_interval_seconds,
                execution_timeout_minutes=execution_timeout_minutes,
                executor_timeout_minutes=executor_timeout_minutes,
                ctx=exec_ctx
            )

            if not final_response:
                # Lost ownership during monitoring
                logger.warning("Lost ownership during monitoring", exec_ctx, data={
                    "execution_id": execution_id,
                    "slice_id": slice_id
                })
                return False

            broker_response = final_response

        # Step 6: Determine execution result
        execution_result = None
        if broker_response.status == 'COMPLETE':
            if broker_response.filled_quantity == slice_data['quantity']:
                execution_result = 'SUCCESS'
            else:
                execution_result = 'PARTIAL_SUCCESS'
        elif broker_response.status == 'REJECTED':
            execution_result = 'BROKER_REJECTED'
        elif broker_response.status == 'CANCELLED':
            execution_result = 'CANCELLED'
        elif broker_response.status == 'EXPIRED':
            execution_result = 'TIMEOUT'
        else:
            execution_result = 'PARTIAL_SUCCESS'

        # Step 7: Finalize execution
        await exec_repo.update_execution_status(
            execution_id=execution_id,
            execution_status='COMPLETED',
            broker_order_status=broker_response.status,
            filled_quantity=broker_response.filled_quantity,
            average_price=broker_response.average_price,
            execution_result=execution_result,
            ctx=exec_ctx
        )

        # Step 8: Update slice with final results
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
            "execution_result": execution_result,
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

        # Determine error type
        error_str = str(e)
        if 'validation' in error_str.lower() or 'invalid' in error_str.lower():
            execution_result = 'VALIDATION_FAILED'
        else:
            execution_result = 'BROKER_REJECTED'

        # Mark execution as failed
        try:
            await exec_repo.update_execution_status(
                execution_id=execution_id,
                execution_status='COMPLETED',
                execution_result=execution_result,
                error_code='EXECUTION_FAILED',
                error_message=error_str,
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
    worker_index: int = 0,
    poll_interval_seconds: int = 5,
    batch_size: int = 10,
    executor_timeout_minutes: int = 5,
    execution_timeout_minutes: int = 30,
    max_placement_attempts: int = 3
):
    """Run the execution worker loop.

    Args:
        pool: Database connection pool
        worker_index: Worker index for generating executor_id
        poll_interval_seconds: Seconds to wait between polls when no work found
        batch_size: Maximum number of slices to process per iteration
        executor_timeout_minutes: Timeout for executor ownership
        execution_timeout_minutes: Timeout for order execution
        max_placement_attempts: Maximum placement retry attempts
    """
    import os
    settings = get_settings()

    # Generate executor_id based on pod name and worker index
    pod_name = os.getenv("POD_NAME")
    if pod_name:
        executor_id = f"{pod_name}-worker-{worker_index}"
    else:
        # Fallback for local development
        executor_id = f"exec-worker-{uuid.uuid4().hex[:8]}"

    logger.info("Execution worker started", data={
        "executor_id": executor_id,
        "worker_index": worker_index,
        "poll_interval_seconds": poll_interval_seconds,
        "batch_size": batch_size,
        "executor_timeout_minutes": executor_timeout_minutes,
        "execution_timeout_minutes": execution_timeout_minutes,
        "max_placement_attempts": max_placement_attempts
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
                    slice_data=slice_data,
                    slice_repo=slice_repo,
                    exec_repo=exec_repo,
                    event_repo=event_repo,
                    zerodha_client=zerodha_client,
                    executor_id=executor_id,
                    executor_timeout_minutes=executor_timeout_minutes,
                    execution_timeout_minutes=execution_timeout_minutes,
                    poll_interval_seconds=poll_interval_seconds,
                    max_placement_attempts=max_placement_attempts,
                    ctx=ctx
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

