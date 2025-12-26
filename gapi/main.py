import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from shared.observability.middleware import ContextMiddleware
from shared.observability.logger import get_logger

app = FastAPI(title="GAPI")
app.add_middleware(ContextMiddleware, service_name="gapi")

logger = get_logger("gapi")


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}


@app.get("/api/hello")
def hello():
    logger.info("Hello endpoint called", data={"endpoint": "/api/hello"})
    return {"message": "Hello from GAPI"}

