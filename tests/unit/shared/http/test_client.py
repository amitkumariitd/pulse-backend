"""Unit tests for ContextPropagatingClient header propagation."""
import types


def test_add_context_headers_maps_fields_correctly(monkeypatch):
    from shared.http import client as client_mod

    # Avoid creating a real httpx.AsyncClient
    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(client_mod.httpx, "AsyncClient", DummyAsyncClient)

    # Stub context
    monkeypatch.setattr(
        client_mod, "get_context", lambda: {
            "trace_id": "t123",
            "trace_source": "GAPI:GET/health",
            "request_id": "r456",
            "request_source": "GAPI:GET/health",
            "extra": "should_not_be_sent",
        }
    )

    c = client_mod.ContextPropagatingClient("http://example.com")
    headers = c._add_context_headers()

    assert headers["X-Trace-Id"] == "t123"
    assert headers["X-Trace-Source"] == "GAPI:GET/health"
    assert headers["X-Request-Id"] == "r456"
    assert headers["X-Request-Source"] == "GAPI:GET/health"
    assert "extra" not in headers


def test_add_context_headers_preserves_existing(monkeypatch):
    from shared.http import client as client_mod

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(client_mod.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(client_mod, "get_context", lambda: {
        "trace_id": "t1",
        "trace_source": "SVC:GET/x",
        "request_id": "r1",
        "request_source": "SVC:GET/x",
    })

    c = client_mod.ContextPropagatingClient("http://example.com")
    headers = {"User-Agent": "pytest", "X-Custom": "1"}
    out = c._add_context_headers(headers)

    # Existing preserved and new added
    assert out["User-Agent"] == "pytest"
    assert out["X-Custom"] == "1"
    assert out["X-Trace-Id"] == "t1"


def test_add_context_headers_skips_missing_values(monkeypatch):
    from shared.http import client as client_mod

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(client_mod.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(client_mod, "get_context", lambda: {
        "trace_id": "t1",
        "trace_source": "SVC:GET/x",
        "request_id": None,  # Should be skipped
        "request_source": "SVC:GET/x",
    })

    c = client_mod.ContextPropagatingClient("http://example.com")
    out = c._add_context_headers()

    assert "X-Request-Id" not in out
    assert out["X-Trace-Id"] == "t1"
