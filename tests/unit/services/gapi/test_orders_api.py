"""Unit tests for GAPI orders API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, HTTPException
from shared.observability.context import RequestContext
from gapi.api.orders import create_order, validate_auth_token
from gapi.models.orders import CreateOrderRequest, SplitConfig, OrderResponse


def test_validate_auth_token_missing():
    """Test validation fails when token is missing."""
    with pytest.raises(HTTPException) as exc_info:
        validate_auth_token(None)
    
    assert exc_info.value.status_code == 401
    assert "UNAUTHORIZED" in str(exc_info.value.detail)


def test_validate_auth_token_invalid_format():
    """Test validation fails when token format is invalid."""
    with pytest.raises(HTTPException) as exc_info:
        validate_auth_token("InvalidToken")
    
    assert exc_info.value.status_code == 401


def test_validate_auth_token_empty():
    """Test validation fails when token is empty."""
    with pytest.raises(HTTPException) as exc_info:
        validate_auth_token("Bearer ")
    
    assert exc_info.value.status_code == 401


def test_validate_auth_token_success():
    """Test validation succeeds with valid token."""
    # Should not raise exception
    validate_auth_token("Bearer valid_token_123")


@pytest.mark.asyncio
async def test_create_order_quantity_validation():
    """Test that total_quantity must be >= num_splits."""
    # Arrange
    request = MagicMock(spec=Request)
    request.state.context = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )
    
    order_data = CreateOrderRequest(
        order_unique_key="ouk_test123",
        instrument="NSE:RELIANCE",
        side="BUY",
        total_quantity=3,  # Less than num_splits
        split_config=SplitConfig(
            num_splits=5,
            duration_minutes=60,
            randomize=True
        )
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_order(request, order_data, "Bearer token123")
    
    assert exc_info.value.status_code == 400
    assert "INVALID_QUANTITY" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_order_success():
    """Test successful order creation."""
    # Arrange
    request = MagicMock(spec=Request)
    request.state.context = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )
    
    order_data = CreateOrderRequest(
        order_unique_key="ouk_test123",
        instrument="NSE:RELIANCE",
        side="BUY",
        total_quantity=100,
        split_config=SplitConfig(
            num_splits=5,
            duration_minutes=60,
            randomize=True
        )
    )
    
    mock_pulse_response = OrderResponse(
        order_id="ord1234567890abcdef",
        order_unique_key="ouk_test123"
    )
    
    mock_pulse_client = AsyncMock()
    mock_pulse_client.create_order.return_value = mock_pulse_response
    
    # Act
    with patch('gapi.api.orders.PulseClient', return_value=mock_pulse_client):
        response = await create_order(request, order_data, "Bearer token123")
    
    # Assert
    assert response.order_id == "ord1234567890abcdef"
    assert response.order_unique_key == "ouk_test123"

    # Verify Pulse client was called
    mock_pulse_client.create_order.assert_called_once()

