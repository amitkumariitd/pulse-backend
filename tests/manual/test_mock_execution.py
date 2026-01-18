#!/usr/bin/env python3
"""
Manual test for mock execution flow.

This demonstrates how to test order execution without real broker integration.
Run this to verify the execution flow works end-to-end with mock data.

Usage:
    python tests/manual/test_mock_execution.py
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from decimal import Decimal
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest
from shared.observability.context import RequestContext, generate_trace_id, generate_request_id


async def test_market_order():
    """Test market order execution (completes immediately)."""
    print("\n" + "="*60)
    print("TEST 1: Market Order (Success)")
    print("="*60)
    
    client = ZerodhaClient(
        api_key="test_key",
        access_token="test_token",
        use_mock=True,
        mock_scenario="success"
    )
    
    ctx = RequestContext(
        trace_id=generate_trace_id(),
        trace_source="TEST:manual",
        request_id=generate_request_id(),
        request_source="TEST:manual",
        span_source="TEST:manual"
    )
    
    # Place market order
    request = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="MARKET"
    )
    
    response = await client.place_order(request, ctx)
    
    print(f"✓ Order placed: {response.broker_order_id}")
    print(f"  Status: {response.status}")
    print(f"  Filled: {response.filled_quantity}/{request.quantity}")
    print(f"  Price: ₹{response.average_price}")
    
    assert response.status == "COMPLETE"
    assert response.filled_quantity == 100
    print("\n✓ Market order test PASSED\n")


async def test_limit_order_with_polling():
    """Test limit order with progressive filling."""
    print("\n" + "="*60)
    print("TEST 2: Limit Order (Progressive Fill)")
    print("="*60)
    
    client = ZerodhaClient(
        api_key="test_key",
        access_token="test_token",
        use_mock=True,
        mock_scenario="success"
    )
    
    ctx = RequestContext(
        trace_id=generate_trace_id(),
        trace_source="TEST:manual",
        request_id=generate_request_id(),
        request_source="TEST:manual",
        span_source="TEST:manual"
    )
    
    # Place limit order
    request = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="LIMIT",
        limit_price=Decimal("1240.00")
    )
    
    response = await client.place_order(request, ctx)
    broker_order_id = response.broker_order_id
    
    print(f"✓ Order placed: {broker_order_id}")
    print(f"  Status: {response.status}")
    print(f"  Filled: {response.filled_quantity}/{request.quantity}")
    
    # Poll for status updates
    for poll_num in range(1, 5):
        await asyncio.sleep(1)  # Simulate 5-second polling interval
        status = await client.get_order_status(broker_order_id, ctx)
        
        print(f"\nPoll #{poll_num}:")
        print(f"  Status: {status.status}")
        print(f"  Filled: {status.filled_quantity}/{request.quantity}")
        if status.average_price:
            print(f"  Price: ₹{status.average_price}")
        
        if status.status == "COMPLETE":
            print(f"\n✓ Order completed after {poll_num} polls")
            break
    
    assert status.status == "COMPLETE"
    assert status.filled_quantity == 100
    print("\n✓ Limit order test PASSED\n")


async def test_partial_fill_scenario():
    """Test partial fill scenario."""
    print("\n" + "="*60)
    print("TEST 3: Partial Fill Scenario")
    print("="*60)
    
    client = ZerodhaClient(
        api_key="test_key",
        access_token="test_token",
        use_mock=True,
        mock_scenario="partial_fill"
    )
    
    ctx = RequestContext(
        trace_id=generate_trace_id(),
        trace_source="TEST:manual",
        request_id=generate_request_id(),
        request_source="TEST:manual",
        span_source="TEST:manual"
    )
    
    request = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="LIMIT",
        limit_price=Decimal("1240.00")
    )
    
    response = await client.place_order(request, ctx)
    
    print(f"✓ Order placed: {response.broker_order_id}")
    print(f"  Status: {response.status}")
    print(f"  Filled: {response.filled_quantity}/{request.quantity} (50% partial fill)")
    
    assert response.filled_quantity == 50
    print("\n✓ Partial fill test PASSED\n")


async def test_rejection_scenario():
    """Test broker rejection scenario."""
    print("\n" + "="*60)
    print("TEST 4: Broker Rejection Scenario")
    print("="*60)
    
    client = ZerodhaClient(
        api_key="test_key",
        access_token="test_token",
        use_mock=True,
        mock_scenario="rejection"
    )
    
    ctx = RequestContext(
        trace_id=generate_trace_id(),
        trace_source="TEST:manual",
        request_id=generate_request_id(),
        request_source="TEST:manual",
        span_source="TEST:manual"
    )
    
    request = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="MARKET"
    )
    
    try:
        response = await client.place_order(request, ctx)
        print("✗ Expected rejection but order succeeded")
        assert False
    except Exception as e:
        print(f"✓ Order rejected as expected: {str(e)}")
        assert "INSUFFICIENT_FUNDS" in str(e)
    
    print("\n✓ Rejection test PASSED\n")


async def main():
    """Run all manual tests."""
    print("\n" + "="*60)
    print("MOCK EXECUTION FLOW TESTS")
    print("="*60)
    print("\nThese tests demonstrate order execution without real broker.")
    print("All tests use mock Zerodha client with different scenarios.\n")
    
    try:
        await test_market_order()
        await test_limit_order_with_polling()
        await test_partial_fill_scenario()
        await test_rejection_scenario()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

