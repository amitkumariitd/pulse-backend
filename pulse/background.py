"""Background worker entry point for Pulse service.

This module runs background workers for:
- Order splitting (PENDING -> IN_PROGRESS -> COMPLETED/FAILED)

Run with:
    python -m pulse.background
"""

import asyncio
import asyncpg
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from shared.database.pool import create_pool, close_pool
from shared.observability.logger import get_logger
from pulse.workers.splitting_worker import run_splitting_worker

logger = get_logger("pulse.background")

# Global state
db_pool: asyncpg.Pool = None
shutdown_event = asyncio.Event()


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Shutdown signal received", data={"signal": signum})
    shutdown_event.set()


async def main():
    """Main entry point for background workers."""
    global db_pool
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    logger.info("Starting Pulse background workers")
    
    try:
        # Create database pool
        settings = get_settings()
        db_pool = await create_pool(settings)
        logger.info("Database pool created", data={
            "host": settings.pulse_db_host,
            "port": settings.pulse_db_port,
            "database": settings.pulse_db_name
        })
        
        # Start splitting worker
        worker_task = asyncio.create_task(
            run_splitting_worker(
                pool=db_pool,
                poll_interval_seconds=5,
                batch_size=10
            )
        )
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        logger.info("Shutting down workers...")
        
        # Cancel worker task
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            logger.info("Worker task cancelled")
        
    except Exception as e:
        logger.error("Fatal error in background worker", data={"error": str(e)})
        raise
    
    finally:
        # Close database pool
        if db_pool:
            await close_pool(db_pool)
            logger.info("Database pool closed")
        
        logger.info("Pulse background workers stopped")


if __name__ == "__main__":
    asyncio.run(main())

