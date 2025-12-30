import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI
from shared.observability.middleware import ContextMiddleware
from shared.observability.logger import get_logger
from shared.database.pool import create_pool, close_pool
from config.settings import get_settings

logger = get_logger("pulse")

# Global database pool
db_pool: asyncpg.Pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)."""
    global db_pool

    # Startup
    settings = get_settings()
    db_pool = await create_pool(settings)
    logger.info("Database pool created", data={
        "host": settings.pulse_db_host,
        "port": settings.pulse_db_port,
        "database": settings.pulse_db_name
    })

    yield

    # Shutdown
    await close_pool(db_pool)
    logger.info("Database pool closed")


app = FastAPI(title="Pulse", lifespan=lifespan)
app.add_middleware(ContextMiddleware, service_name="pulse")


def get_db_pool() -> asyncpg.Pool:
    """Dependency to get database pool."""
    return db_pool


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}


@app.get("/internal/hello")
def hello():
    logger.info("Hello endpoint called", data={"endpoint": "/internal/hello"})
    return {"message": "Hello from Pulse"}

