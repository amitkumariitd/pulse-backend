import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from shared.observability.middleware import TracingMiddleware
from shared.observability.logger import get_logger
from shared.observability.context import get_trace_context

app = FastAPI(title="GAPI")
app.add_middleware(TracingMiddleware, service_name="gapi")

logger = get_logger("gapi")


@app.get("/health")
def health():
    ctx = get_trace_context()
    logger.info("Health check", **ctx)
    return {"status": "ok"}


@app.get("/api/hello")
def hello():
    ctx = get_trace_context()
    logger.info("Hello endpoint called", **ctx, data={"endpoint": "/api/hello"})
    return {"message": "Hello from GAPI"}

