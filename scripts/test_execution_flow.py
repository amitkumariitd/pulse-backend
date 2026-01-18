#!/usr/bin/env python3
"""
Test script to demonstrate order execution flow with mock Zerodha client.

This script shows how to test the entire execution flow without real broker integration.
It creates order slices and runs the execution worker to process them.

Usage:
    python scripts/test_execution_flow.py [scenario]

Scenarios:
    success         - Orders complete successfully (default)
    partial_fill    - Limit orders partially fill
    rejection       - Orders get rejected by broker
    network_error   - Simulate network failures
    timeout         - Orders timeout without filling
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from config.settings import get_settings
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id
from shared.observability.logger import get_logger
from pulse.repositories.order_slice_repository import OrderSliceRepository
from pulse.repositories.execution_repository import ExecutionRepository
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest
from pulse.workers.execution_worker import ExecutionWorker

logger = get_logger("test.execution_flow")


async def create_test_order_slice(pool: asyncpg.Pool, scenario: str) -> str:
    """Create a test order slice ready for execution.
    
    Args:
        pool: Database connection pool
        scenario: Test scenario name
        
    Returns:
        Created slice ID
    """
    ctx = RequestContext(
        trace_id=generate_trace_id(),
        trace_source="TEST:test_execution_flow",
        request_id=generate_request_id(),
        request_source="TEST:test_execution_flow",
        span_source="TEST:test_execution_flow"
    )
    
    slice_repo = OrderSliceRepository(pool)
    
    # Create a slice scheduled for immediate execution
    slice_id = f"slice_test_{scenario}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order_id = f"order_test_{scenario}"
    
    # First, create a parent order (required by foreign key)
    conn = await pool.acquire()
    try:
        await conn.execute(
            """
            INSERT INTO orders (
                id, instrument, side, quantity, order_type,
                status, state,
                origin_trace_id, origin_trace_source,
                origin_request_id, origin_request_source,
                request_id, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (id) DO NOTHING
            """,
            order_id, "NSE:RELIANCE", "BUY", 100, "TWAP",
            "ACTIVE", "SPLITTING",
            ctx.trace_id, ctx.trace_source,
            ctx.request_id, ctx.request_source,
            ctx.request_id,
            datetime.now(timezone.utc), datetime.now(timezone.utc)
        )
    finally:
        await pool.release(conn)
    
    # Create the slice
    slice_data = await slice_repo.create_order_slice(
        slice_id=slice_id,
        order_id=order_id,
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        sequence_number=1,
        scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=10),  # Past time = ready to execute
        ctx=ctx
    )
    
    logger.info(f"Created test slice: {slice_id}", ctx, data={"scenario": scenario})
    return slice_id


async def run_test_scenario(scenario: str = "success"):
    """Run a test execution scenario.
    
    Args:
        scenario: Test scenario to run
    """
    settings = get_settings()
    
    # Create database pool
    pool = await asyncpg.create_pool(
        host=settings.pulse_db_host,
        port=settings.pulse_db_port,
        user=settings.pulse_db_user,
        password=settings.pulse_db_password,
        database=settings.pulse_db_name,
        min_size=2,
        max_size=10
    )
    
    try:
        # Create test slice
        slice_id = await create_test_order_slice(pool, scenario)
        
        # Create Zerodha client with specified scenario
        zerodha_client = ZerodhaClient(
            api_key="test_api_key",
            access_token="test_access_token",
            use_mock=True,
            mock_scenario=scenario
        )
        
        # Create and run execution worker (single iteration)
        worker = ExecutionWorker(
            pool=pool,
            zerodha_client=zerodha_client,
            executor_id=f"test_executor_{scenario}",
            timeout_minutes=5,
            poll_interval_seconds=2  # Faster polling for testing
        )
        
        logger.info(f"Running execution worker with scenario: {scenario}")
        
        # Run one iteration
        await worker.process_pending_slices()
        
        # Check results
        slice_repo = OrderSliceRepository(pool)
        exec_repo = ExecutionRepository(pool)
        
        ctx = RequestContext(
            trace_id=generate_trace_id(),
            trace_source="TEST:check_results",
            request_id=generate_request_id(),
            request_source="TEST:check_results",
            span_source="TEST:check_results"
        )
        
        slice_data = await slice_repo.get_slice_by_id(slice_id, ctx)
        execution_data = await exec_repo.get_execution_by_slice_id(slice_id, ctx)
        
        print(f"\n{'='*60}")
        print(f"Test Scenario: {scenario.upper()}")
        print(f"{'='*60}")
        print(f"\nSlice Status: {slice_data['status']}")
        print(f"Filled Quantity: {slice_data.get('filled_quantity', 0)}")
        print(f"Average Price: {slice_data.get('average_price', 'N/A')}")
        
        if execution_data:
            print(f"\nExecution Status: {execution_data['execution_status']}")
            print(f"Execution Result: {execution_data.get('execution_result', 'N/A')}")
            print(f"Broker Order ID: {execution_data.get('broker_order_id', 'N/A')}")
            print(f"Broker Status: {execution_data.get('broker_order_status', 'N/A')}")
        
        print(f"\n{'='*60}\n")
        
    finally:
        await pool.close()


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "success"
    
    valid_scenarios = ["success", "partial_fill", "rejection", "network_error", "timeout"]
    if scenario not in valid_scenarios:
        print(f"Invalid scenario: {scenario}")
        print(f"Valid scenarios: {', '.join(valid_scenarios)}")
        sys.exit(1)
    
    asyncio.run(run_test_scenario(scenario))

