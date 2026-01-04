#!/usr/bin/env python
"""Check database schema."""
import asyncio
import sys
import os

# Add repository root to Python path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

import asyncpg
from config.settings import get_settings


async def check_schema():
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.pulse_db_host,
        port=settings.pulse_db_port,
        user=settings.pulse_db_user,
        password=settings.pulse_db_password,
        database=settings.pulse_db_name
    )
    
    print("=== Orders table columns ===")
    result = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'orders' 
        ORDER BY ordinal_position
    """)
    for row in result:
        print(f"  {row['column_name']}: {row['data_type']}")
    
    print("\n=== Order_slices table columns ===")
    result = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'order_slices' 
        ORDER BY ordinal_position
    """)
    for row in result:
        print(f"  {row['column_name']}: {row['data_type']}")
    
    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_schema())

