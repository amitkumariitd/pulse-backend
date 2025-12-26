"""FastAPI dependencies for request context."""
from fastapi import Request
from .context import RequestContext


def get_context(request: Request) -> RequestContext:
    """
    FastAPI dependency to extract RequestContext from request state.

    Usage:
        @app.get("/endpoint")
        async def my_endpoint(ctx: RequestContext = Depends(get_context)):
            logger.info("Processing request", ctx)
    """
    return request.state.context

