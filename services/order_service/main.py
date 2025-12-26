import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from shared.observability.middleware import TracingMiddleware
from shared.observability.logger import get_logger
from shared.observability.context import get_trace_context

app = FastAPI(title="Order Service")
app.add_middleware(TracingMiddleware, service_name="order_service")

logger = get_logger("order_service")


@app.get("/health")
def health():
    ctx = get_trace_context()
    logger.info("Health check", **ctx)
    return {"status": "ok"}


@app.get("/internal/hello")
def hello():
    ctx = get_trace_context()
    logger.info("Hello endpoint called", **ctx, data={"endpoint": "/internal/hello"})
    return {"message": "Hello from Order Service"}

