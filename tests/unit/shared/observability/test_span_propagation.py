"""Tests for span_id and parent_span_id propagation across service boundaries."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from shared.observability.middleware import ContextMiddleware


def test_span_id_becomes_parent_span_id_across_services():
    """Test that incoming X-Parent-Span-Id becomes parent_span_id in receiving service."""
    # Arrange - Create a test app
    app = FastAPI()
    app.add_middleware(ContextMiddleware, service_name="pulse")

    captured_context = None

    @app.get("/test")
    def test_endpoint(request: Request):
        nonlocal captured_context
        captured_context = request.state.context
        return {"ok": True}

    client = TestClient(app)

    # Act - Send request with X-Parent-Span-Id header (simulating call from GAPI)
    headers = {
        "X-Trace-Id": "t1735228800a1b2c3d4e5f6",
        "X-Trace-Source": "GAPI:POST/api/orders",
        "X-Request-Id": "r1735228800f6e5d4c3b2a1",
        "X-Request-Source": "GAPI:POST/api/orders",
        "X-Parent-Span-Id": "sa1b2c3d4"  # GAPI's span_id sent as parent
    }

    response = client.get("/test", headers=headers)

    # Assert
    assert response.status_code == 200
    assert captured_context is not None

    # Verify parent_span_id is set from incoming X-Parent-Span-Id
    assert captured_context.parent_span_id == "sa1b2c3d4"

    # Verify new span_id was generated (different from parent)
    assert captured_context.span_id != "sa1b2c3d4"
    assert captured_context.span_id.startswith("s")
    assert len(captured_context.span_id) == 9

    # Verify span_source was built from parent's request_source
    assert captured_context.span_source == "GAPI:POST/api/orders->PULSE:GET/test"


def test_no_parent_span_id_when_first_service():
    """Test that parent_span_id is None when no X-Parent-Span-Id header is present."""
    # Arrange
    app = FastAPI()
    app.add_middleware(ContextMiddleware, service_name="gapi")

    captured_context = None

    @app.get("/test")
    def test_endpoint(request: Request):
        nonlocal captured_context
        captured_context = request.state.context
        return {"ok": True}

    client = TestClient(app)

    # Act - Send request without X-Parent-Span-Id header (first service in chain)
    response = client.get("/test")

    # Assert
    assert response.status_code == 200
    assert captured_context is not None

    # Verify parent_span_id is None (no parent)
    assert captured_context.parent_span_id is None

    # Verify span_id was generated
    assert captured_context.span_id.startswith("s")
    assert len(captured_context.span_id) == 9

    # Verify span_source is just the current service
    assert captured_context.span_source == "GAPI:GET/test"


def test_span_source_chain_building():
    """Test that span_source builds a chain across multiple services."""
    # Arrange
    app = FastAPI()
    app.add_middleware(ContextMiddleware, service_name="broker")

    captured_context = None

    @app.post("/submit")
    def test_endpoint(request: Request):
        nonlocal captured_context
        captured_context = request.state.context
        return {"ok": True}

    client = TestClient(app)

    # Act - Simulate call from PULSE which was called from GAPI
    # Note: X-Request-Source contains PULSE's request_source, used to build span_source
    headers = {
        "X-Trace-Id": "t1735228800a1b2c3d4e5f6",
        "X-Trace-Source": "GAPI:POST/api/orders",
        "X-Request-Id": "r1735228800f6e5d4c3b2a1",
        "X-Request-Source": "PULSE:POST/internal/orders",
        "X-Parent-Span-Id": "sb2c3d4e5"  # PULSE's span_id sent as parent
    }

    response = client.post("/submit", headers=headers)

    # Assert
    assert response.status_code == 200
    assert captured_context is not None

    # Verify parent_span_id is PULSE's span_id
    assert captured_context.parent_span_id == "sb2c3d4e5"

    # Verify span_source shows chain built from request_source
    assert captured_context.span_source == "PULSE:POST/internal/orders->BROKER:POST/submit"


def test_response_headers_include_new_span_id():
    """Test that response headers include the newly generated span_id, not parent."""
    # Arrange
    app = FastAPI()
    app.add_middleware(ContextMiddleware, service_name="pulse")

    @app.get("/test")
    def test_endpoint():
        return {"ok": True}

    client = TestClient(app)

    # Act - Send request with parent span_id
    headers = {
        "X-Parent-Span-Id": "sa1b2c3d4"  # Parent span
    }

    response = client.get("/test", headers=headers)

    # Assert
    assert response.status_code == 200

    # Verify response contains NEW span_id (not the parent)
    response_span_id = response.headers.get("x-span-id")
    assert response_span_id is not None
    assert response_span_id != "sa1b2c3d4"  # Different from parent
    assert response_span_id.startswith("s")
    assert len(response_span_id) == 9

