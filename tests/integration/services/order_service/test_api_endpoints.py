"""Integration tests for Order Service endpoints"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from fastapi.testclient import TestClient
from services.order_service.main import app

client = TestClient(app)


def test_health_endpoint_success():
    """Test health endpoint returns 200 OK"""
    # Act
    response = client.get("/health")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_includes_tracing_headers():
    """Test health endpoint returns tracing headers"""
    # Arrange
    headers = {
        "X-Request-Id": "r-test123",
        "X-Trace-Id": "t-test456"
    }
    
    # Act
    response = client.get("/health", headers=headers)
    
    # Assert
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers
    assert "X-Trace-Id" in response.headers
    assert response.headers["X-Request-Id"] == "r-test123"
    assert response.headers["X-Trace-Id"] == "t-test456"


def test_health_endpoint_generates_tracing_headers_when_missing():
    """Test health endpoint generates tracing headers if not provided"""
    # Act
    response = client.get("/health")
    
    # Assert
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers
    assert "X-Trace-Id" in response.headers
    assert response.headers["X-Request-Id"].startswith("r-")
    assert response.headers["X-Trace-Id"].startswith("t-")


def test_hello_endpoint_success():
    """Test hello endpoint returns correct message"""
    # Act
    response = client.get("/internal/hello")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Order Service"}


def test_hello_endpoint_includes_tracing_headers():
    """Test hello endpoint propagates tracing headers"""
    # Arrange
    headers = {
        "X-Request-Id": "r-hello123",
        "X-Trace-Id": "t-hello456"
    }
    
    # Act
    response = client.get("/internal/hello", headers=headers)
    
    # Assert
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "r-hello123"
    assert response.headers["X-Trace-Id"] == "t-hello456"
    assert "message" in response.json()


def test_hello_endpoint_content_type():
    """Test hello endpoint returns JSON content type"""
    # Act
    response = client.get("/internal/hello")
    
    # Assert
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

