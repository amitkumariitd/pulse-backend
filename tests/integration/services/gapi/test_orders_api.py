"""Integration tests for GAPI orders API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from gapi.main import app
from shared.models.orders import OrderResponse

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_order_missing_auth():
    """Test that missing auth token returns 401."""
    # Arrange
    order_data = {
        "order_unique_key": "ouk_test123",
        "instrument": "NSE:RELIANCE",
        "side": "BUY",
        "total_quantity": 100,
        "split_config": {
            "num_splits": 5,
            "duration_minutes": 60,
            "randomize": True
        }
    }
    
    # Act
    response = client.post("/api/orders", json=order_data)
    
    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    error_detail = data["detail"]
    assert error_detail["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_create_order_invalid_instrument():
    """Test that invalid instrument format returns 400."""
    # Arrange
    order_data = {
        "order_unique_key": "ouk_test123",
        "instrument": "RELIANCE",  # Missing exchange prefix
        "side": "BUY",
        "total_quantity": 100,
        "split_config": {
            "num_splits": 5,
            "duration_minutes": 60,
            "randomize": True
        }
    }
    
    headers = {"Authorization": "Bearer test_token"}
    
    # Act
    response = client.post("/api/orders", json=order_data, headers=headers)
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_create_order_invalid_quantity():
    """Test that total_quantity < num_splits returns 400."""
    # Arrange
    order_data = {
        "order_unique_key": "ouk_test123",
        "instrument": "NSE:RELIANCE",
        "side": "BUY",
        "total_quantity": 3,
        "split_config": {
            "num_splits": 5,
            "duration_minutes": 60,
            "randomize": True
        }
    }
    
    headers = {"Authorization": "Bearer test_token"}
    
    # Act
    response = client.post("/api/orders", json=order_data, headers=headers)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    error_detail = data["detail"]
    assert error_detail["error"]["code"] == "INVALID_QUANTITY"


@pytest.mark.asyncio
async def test_create_order_success():
    """Test successful order creation."""
    # Arrange
    order_data = {
        "order_unique_key": "ouk_test123",
        "instrument": "NSE:RELIANCE",
        "side": "BUY",
        "total_quantity": 100,
        "split_config": {
            "num_splits": 5,
            "duration_minutes": 60,
            "randomize": True
        }
    }
    
    headers = {"Authorization": "Bearer test_token"}
    
    mock_pulse_response = OrderResponse(
        order_id="ord1234567890abcdef",
        order_unique_key="ouk_test123"
    )
    
    mock_pulse_client = AsyncMock()
    mock_pulse_client.create_order.return_value = mock_pulse_response
    
    # Act
    with patch('gapi.api.orders.PulseClient', return_value=mock_pulse_client):
        response = client.post("/api/orders", json=order_data, headers=headers)
    
    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data["order_id"] == "ord1234567890abcdef"
    assert data["order_unique_key"] == "ouk_test123"
    # Only order_id and order_unique_key should be in response
    assert set(data.keys()) == {"order_id", "order_unique_key"}

    # Verify tracing headers
    assert "X-Request-Id" in response.headers
    assert "X-Trace-Id" in response.headers


@pytest.mark.asyncio
async def test_create_order_invalid_split_config():
    """Test that invalid split config returns 422."""
    # Arrange
    order_data = {
        "order_unique_key": "ouk_test123",
        "instrument": "NSE:RELIANCE",
        "side": "BUY",
        "total_quantity": 100,
        "split_config": {
            "num_splits": 150,  # Exceeds max of 100
            "duration_minutes": 60,
            "randomize": True
        }
    }
    
    headers = {"Authorization": "Bearer test_token"}
    
    # Act
    response = client.post("/api/orders", json=order_data, headers=headers)
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error

