#!/usr/bin/env python
"""Reset database by dropping all tables."""
import asyncio
import sys
import os

# Add repository root to Python path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

import asyncpg
from config.settings import get_settings


async def reset_db():
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.pulse_db_host,
        port=settings.pulse_db_port,
        user=settings.pulse_db_user,
        password=settings.pulse_db_password,
        database=settings.pulse_db_name
    )
    
    print("Dropping all tables and functions...")

    # Drop tables first (this will cascade drop triggers)
    await conn.execute("DROP TABLE IF EXISTS order_slices_history CASCADE")
    await conn.execute("DROP TABLE IF EXISTS order_slices CASCADE")
    await conn.execute("DROP TABLE IF EXISTS orders_history CASCADE")
    await conn.execute("DROP TABLE IF EXISTS orders CASCADE")

    # Drop functions
    await conn.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
    await conn.execute("DROP FUNCTION IF EXISTS orders_history_trigger() CASCADE")
    await conn.execute("DROP FUNCTION IF EXISTS order_slices_history_trigger() CASCADE")
    
    # Update alembic version to base
    await conn.execute("DELETE FROM alembic_version")
    
    await conn.close()
    print("Database reset complete!")


if __name__ == "__main__":
    asyncio.run(reset_db())

