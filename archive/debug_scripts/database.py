# database.py
import os
import asyncpg
from typing import Optional, Dict, List, Any, Union
import logging

logger = logging.getLogger(__name__)

# Database connection pool
pool = None

async def get_connection():
    """Get a connection from the pool"""
    global pool
    if pool is None:
        # Initialize the connection pool
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL not set in environment variables")
                
            pool = await asyncpg.create_pool(database_url)
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Error creating database connection pool: {e}")
            raise
            
    return await pool.acquire()

async def release_connection(connection):
    """Release a connection back to the pool"""
    await pool.release(connection)

async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute a query and return a single row as a dictionary"""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None
    finally:
        await release_connection(conn)

async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Execute a query and return all rows as dictionaries"""
    conn = await get_connection()
    try:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]
    finally:
        await release_connection(conn)

async def execute(query: str, *args) -> str:
    """Execute a query and return the status"""
    conn = await get_connection()
    try:
        status = await conn.execute(query, *args)
        return status
    finally:
        await release_connection(conn)

async def close_pool():
    """Close the database connection pool"""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database connection pool closed")