import asyncio
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from gapi.main import app as gapi_app
from pulse.main import app as pulse_app, lifespan as pulse_lifespan, get_db_pool
from pulse.workers.splitting_worker import run_splitting_worker
from pulse.workers.timeout_monitor import run_timeout_monitor
from shared.observability.logger import get_logger
from shared.observability.access_log_middleware import AccessLogMiddleware
from config.logging_config import LOGGING_CONFIG

# Configure logging at module import time (before Uvicorn starts)
logging.config.dictConfig(LOGGING_CONFIG)

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize Pulse database pool and start background workers."""
    # Start Pulse's lifespan (initializes database pool)
    async with pulse_lifespan(pulse_app):
        # Get the database pool from Pulse
        db_pool = get_db_pool()

        logger.info("Starting background workers")

        # Start splitting worker
        splitting_task = asyncio.create_task(
            run_splitting_worker(
                pool=db_pool,
                poll_interval_seconds=5,
                batch_size=10
            )
        )

        # Start timeout monitor
        monitor_task = asyncio.create_task(
            run_timeout_monitor(
                pool=db_pool,
                check_interval_seconds=60,
                timeout_minutes=5
            )
        )

        logger.info("Background workers started", data={
            "splitting_worker": "running",
            "timeout_monitor": "running"
        })

        try:
            yield
        finally:
            # Shutdown: cancel worker tasks
            logger.info("Shutting down background workers")

            splitting_task.cancel()
            monitor_task.cancel()

            try:
                await splitting_task
            except asyncio.CancelledError:
                logger.info("Splitting worker task cancelled")

            try:
                await monitor_task
            except asyncio.CancelledError:
                logger.info("Timeout monitor task cancelled")

            logger.info("Background workers stopped")


app = FastAPI(
    title="Pulse Backend",
    description="Trading backend monorepo - single deployable (gapi + pulse + background workers)",
    lifespan=lifespan
)

# Add access log middleware for structured JSON logging
app.add_middleware(AccessLogMiddleware)

app.mount("/gapi", gapi_app)
app.mount("/pulse", pulse_app)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "components": {
            "gapi": "mounted at /gapi",
            "pulse": "mounted at /pulse",
            "background_workers": "running"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        access_log=False,  # Disable uvicorn's default access logs (we use our own structured JSON logs)
        log_config=LOGGING_CONFIG  # Use custom JSON logging configuration
    )

