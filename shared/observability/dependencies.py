from typing import Dict, Any, Optional
from .context import (
    get_context,
    get_trace_id,
    get_request_id,
    get_user_id,
    get_order_id
)


def get_request_context() -> Dict[str, Any]:
    """
    FastAPI dependency that returns the complete request context.
    
    Usage:
        @app.get("/api/orders")
        def list_orders(ctx: dict = Depends(get_request_context)):
            logger.info("Listing orders")  # Context auto-injected
            return {"request_id": ctx['request_id']}
    """
    return get_context()


def require_trace_id() -> str:
    """
    FastAPI dependency that requires trace_id to be present.
    
    Usage:
        @app.get("/api/orders")
        def list_orders(trace_id: str = Depends(require_trace_id)):
            return {"trace_id": trace_id}
    """
    trace_id = get_trace_id()
    if not trace_id:
        raise ValueError("trace_id not found in context")
    return trace_id


def require_user_id() -> str:
    """
    FastAPI dependency that requires user_id to be present.
    Useful for authenticated endpoints.
    
    Usage:
        @app.post("/api/orders")
        def create_order(user_id: str = Depends(require_user_id)):
            # user_id guaranteed to exist
            return {"user_id": user_id}
    """
    user_id = get_user_id()
    if not user_id:
        raise ValueError("user_id not found in context - authentication required")
    return user_id


def get_optional_user_id() -> Optional[str]:
    """
    FastAPI dependency that returns user_id if present, None otherwise.
    
    Usage:
        @app.get("/api/public")
        def public_endpoint(user_id: Optional[str] = Depends(get_optional_user_id)):
            if user_id:
                # Authenticated request
                pass
            else:
                # Anonymous request
                pass
    """
    return get_user_id()

