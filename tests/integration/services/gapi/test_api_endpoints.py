"""Integration tests for GAPI endpoints"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from fastapi.testclient import TestClient
from services.gapi.main import app

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
    assert response.headers["X-Request-Id"].startswith("r")
    assert response.headers["X-Trace-Id"].startswith("t")
    assert len(response.headers["X-Request-Id"]) == 23
    assert len(response.headers["X-Trace-Id"]) == 23


def test_hello_endpoint_success():
    """Test hello endpoint returns correct message"""
    # Act
    response = client.get("/api/hello")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from GAPI"}


def test_hello_endpoint_includes_tracing_headers():
    """Test hello endpoint propagates tracing headers"""
    # Arrange
    headers = {
        "X-Request-Id": "r-hello123",
        "X-Trace-Id": "t-hello456"
    }
    
    # Act
    response = client.get("/api/hello", headers=headers)
    
    # Assert
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "r-hello123"
    assert response.headers["X-Trace-Id"] == "t-hello456"
    assert "message" in response.json()


def test_hello_endpoint_content_type():
    """Test hello endpoint returns JSON content type"""
    # Act
    response = client.get("/api/hello")

    # Assert
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_trace_source_includes_method_and_path():
    """Test trace_source and request_source include HTTP method and path"""
    # Arrange
    from fastapi import Request

    captured_context = None

    @app.get("/test/source")
    def test_source_endpoint(request: Request):
        nonlocal captured_context
        captured_context = request.state.context
        return {"ok": True}

    # Act
    response = client.get("/test/source")

    # Assert
    assert response.status_code == 200
    assert captured_context is not None
    assert captured_context.trace_source == "GAPI:GET/test/source"
    assert captured_context.request_source == "GAPI:GET/test/source"


def test_trace_source_distinguishes_http_methods():
    """Test trace_source differentiates between GET and POST on same path"""
    # Arrange
    from fastapi import Request

    get_context = None
    post_context = None

    @app.get("/test/method")
    def test_get_endpoint(request: Request):
        nonlocal get_context
        get_context = request.state.context
        return {"method": "GET"}

    @app.post("/test/method")
    def test_post_endpoint(request: Request):
        nonlocal post_context
        post_context = request.state.context
        return {"method": "POST"}

    # Act
    get_response = client.get("/test/method")
    post_response = client.post("/test/method", json={})

    # Assert
    assert get_response.status_code == 200
    assert post_response.status_code == 200
    assert get_context.trace_source == "GAPI:GET/test/method"
    assert post_context.trace_source == "GAPI:POST/test/method"


def test_trace_source_preserved_from_header():
    """Test trace_source is preserved from X-Trace-Source header"""
    # Arrange
    from fastapi import Request

    captured_context = None

    @app.get("/test/propagation")
    def test_propagation_endpoint(request: Request):
        nonlocal captured_context
        captured_context = request.state.context
        return {"ok": True}

    headers = {
        "X-Trace-Source": "EXTERNAL:POST/original/endpoint"
    }

    # Act
    response = client.get("/test/propagation", headers=headers)

    # Assert
    assert response.status_code == 200
    assert captured_context.trace_source == "EXTERNAL:POST/original/endpoint"
    assert captured_context.request_source == "GAPI:GET/test/propagation"

