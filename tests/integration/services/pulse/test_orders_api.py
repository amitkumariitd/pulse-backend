"""Integration tests for Pulse orders API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from pulse.main import app


def test_create_order_success():
    """Test creating an order successfully."""
    with TestClient(app) as client:
        # Arrange
        order_data = {
            "order_unique_key": f"ouk_test_{id(object())}",
            "instrument": "NSE:RELIANCE",
            "side": "BUY",
            "total_quantity": 100,
            "num_splits": 5,
            "duration_minutes": 60,
            "randomize": True
        }

        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": "r1234567890abcdef1234",
            "X-Trace-Id": "t1234567890abcdef1234"
        }

        # Act
        response = client.post("/internal/orders", json=order_data, headers=headers)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["order_id"].startswith("ord")
        assert data["order_queue_status"] == "PENDING"
        assert data["instrument"] == "NSE:RELIANCE"
        assert data["side"] == "BUY"
        assert data["total_quantity"] == 100
        assert data["num_splits"] == 5
        assert data["duration_minutes"] == 60
        assert data["randomize"] == True
        assert "created_at" in data

        # Verify tracing headers
        assert response.headers["X-Request-Id"] == "r1234567890abcdef1234"
        assert response.headers["X-Trace-Id"] == "t1234567890abcdef1234"


def test_create_order_duplicate_key():
    """Test creating an order with duplicate unique key."""
    with TestClient(app) as client:
        # Arrange
        order_unique_key = f"ouk_duplicate_{id(object())}"
        order_data = {
            "order_unique_key": order_unique_key,
            "instrument": "NSE:INFY",
            "side": "SELL",
            "total_quantity": 50,
            "num_splits": 10,
            "duration_minutes": 120,
            "randomize": False
        }

        # Act - Create first order
        response1 = client.post("/internal/orders", json=order_data)
        assert response1.status_code == 201

        # Act - Try to create duplicate
        response2 = client.post("/internal/orders", json=order_data)

        # Assert
        assert response2.status_code == 409
        data = response2.json()
        # FastAPI wraps HTTPException detail in "detail" key
        assert "detail" in data
        error_detail = data["detail"]
        assert error_detail["error"]["code"] == "DUPLICATE_ORDER_UNIQUE_KEY"
        assert error_detail["error"]["details"]["order_unique_key"] == order_unique_key


def test_create_order_generates_tracing_headers():
    """Test that endpoint generates tracing headers if not provided."""
    with TestClient(app) as client:
        # Arrange
        order_data = {
            "order_unique_key": f"ouk_test_{id(object())}",
            "instrument": "BSE:TCS",
            "side": "BUY",
            "total_quantity": 200,
            "num_splits": 20,
            "duration_minutes": 240,
            "randomize": True
        }

        # Act - No tracing headers provided
        response = client.post("/internal/orders", json=order_data)

        # Assert
        assert response.status_code == 201
        assert "X-Request-Id" in response.headers
        assert "X-Trace-Id" in response.headers
        assert response.headers["X-Request-Id"].startswith("r")
        assert response.headers["X-Trace-Id"].startswith("t")

