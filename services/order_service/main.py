import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from shared.observability.middleware import ContextMiddleware
from shared.observability.logger import get_logger

app = FastAPI(title="Order Service")
app.add_middleware(ContextMiddleware, service_name="order_service")

logger = get_logger("order_service")


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}


@app.get("/internal/hello")
def hello():
    logger.info("Hello endpoint called", data={"endpoint": "/internal/hello"})
    return {"message": "Hello from Order Service"}

