"""Unit tests for ZerodhaClient."""
import pytest
from decimal import Decimal
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest, ZerodhaOrderResponse
from shared.observability.context import RequestContext


@pytest.fixture
def request_context():
    """Create a test request context."""
    return RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST:test",
        request_id="r1234567890abcdef1234",
        request_source="TEST:test",
        span_source="TEST:test"
    )


@pytest.fixture
def zerodha_client():
    """Create ZerodhaClient instance in mock mode."""
    return ZerodhaClient(
        api_key="test_api_key",
        access_token="test_access_token",
        use_mock=True
    )


@pytest.mark.asyncio
async def test_place_market_order_success(zerodha_client, request_context):
    """Test placing a market order successfully (mock mode)."""
    # Arrange
    order_request = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        product_type="CNC",
        validity="DAY"
    )
    
    # Act
    response = await zerodha_client.place_order(order_request, request_context)
    
    # Assert
    assert isinstance(response, ZerodhaOrderResponse)
    assert response.broker_order_id is not None
    assert response.broker_order_id.startswith("ZH")
    assert response.status == "COMPLETE"  # Mock market orders fill immediately
    assert response.filled_quantity == 100
    assert response.pending_quantity == 0
    assert response.average_price == Decimal("1250.00")  # Mock price


@pytest.mark.asyncio
async def test_place_limit_order_success(zerodha_client, request_context):
    """Test placing a limit order successfully (mock mode)."""
    # Arrange
    order_request = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="LIMIT",
        limit_price=Decimal("1240.00"),
        product_type="CNC",
        validity="DAY"
    )
    
    # Act
    response = await zerodha_client.place_order(order_request, request_context)
    
    # Assert
    assert isinstance(response, ZerodhaOrderResponse)
    assert response.broker_order_id is not None
    assert response.status == "OPEN"  # Mock limit orders stay open
    assert response.filled_quantity == 0
    assert response.pending_quantity == 100
    assert response.average_price is None  # Not filled yet


@pytest.mark.asyncio
async def test_get_order_status_complete(zerodha_client, request_context):
    """Test getting order status for a completed order (mock mode)."""
    # Arrange
    broker_order_id = "ZH240101abc123"
    
    # Act
    response = await zerodha_client.get_order_status(broker_order_id, request_context)
    
    # Assert
    assert isinstance(response, ZerodhaOrderResponse)
    assert response.broker_order_id == broker_order_id
    assert response.status == "COMPLETE"
    assert response.filled_quantity == 100
    assert response.pending_quantity == 0
    assert response.average_price == Decimal("1250.00")


@pytest.mark.asyncio
async def test_cancel_order_success(zerodha_client, request_context):
    """Test cancelling an order successfully (mock mode)."""
    # Arrange
    broker_order_id = "ZH240101abc123"
    
    # Act
    response = await zerodha_client.cancel_order(broker_order_id, request_context)
    
    # Assert
    assert isinstance(response, ZerodhaOrderResponse)
    assert response.broker_order_id == broker_order_id
    assert response.status == "CANCELLED"
    assert response.message == "Order cancelled successfully"


@pytest.mark.asyncio
async def test_zerodha_order_request_validation():
    """Test ZerodhaOrderRequest validation."""
    # Valid market order
    market_order = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        product_type="CNC",
        validity="DAY"
    )
    assert market_order.order_type == "MARKET"
    assert market_order.limit_price is None
    
    # Valid limit order
    limit_order = ZerodhaOrderRequest(
        instrument="NSE:RELIANCE",
        side="SELL",
        quantity=50,
        order_type="LIMIT",
        limit_price=Decimal("1300.00"),
        product_type="MIS",
        validity="IOC"
    )
    assert limit_order.order_type == "LIMIT"
    assert limit_order.limit_price == Decimal("1300.00")


@pytest.mark.asyncio
async def test_client_context_manager(request_context):
    """Test ZerodhaClient as async context manager."""
    # Act & Assert
    async with ZerodhaClient(api_key="test_key", use_mock=True) as client:
        assert client is not None
        
        # Should be able to use the client
        order_request = ZerodhaOrderRequest(
            instrument="NSE:RELIANCE",
            side="BUY",
            quantity=100,
            order_type="MARKET",
            product_type="CNC",
            validity="DAY"
        )
        response = await client.place_order(order_request, request_context)
        assert response.broker_order_id is not None

