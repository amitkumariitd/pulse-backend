#!/usr/bin/env python
"""Temporary script to fix alembic version in database."""
import asyncio
import sys
import os

# Add repository root to Python path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

import asyncpg
from config.settings import get_settings


async def fix_version():
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.pulse_db_host,
        port=settings.pulse_db_port,
        user=settings.pulse_db_user,
        password=settings.pulse_db_password,
        database=settings.pulse_db_name
    )
    await conn.execute("UPDATE alembic_version SET version_num = '1767086939'")
    await conn.close()
    print('Updated alembic version to 1767086939')


if __name__ == "__main__":
    asyncio.run(fix_version())

