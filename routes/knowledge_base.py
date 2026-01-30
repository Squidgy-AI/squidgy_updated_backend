"""
Knowledge Base API Routes
Handles fetching user files and custom instructions from Neon database
"""

import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge_base"])

# Neon PostgreSQL configuration
NEON_DB_HOST = os.getenv('NEON_DB_HOST')
NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
NEON_DB_USER = os.getenv('NEON_DB_USER')
NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')


class FileResponse(BaseModel):
    success: bool
    files: List[Dict[str, Any]]


class InstructionsResponse(BaseModel):
    success: bool
    instructions: str


async def get_db_connection():
    """Create and return a connection to the Neon database"""
    if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
        raise HTTPException(status_code=500, detail="Database configuration missing")

    try:
        conn = await asyncpg.connect(
            host=NEON_DB_HOST,
            port=int(NEON_DB_PORT),
            user=NEON_DB_USER,
            password=NEON_DB_PASSWORD,
            database=NEON_DB_NAME,
            ssl='require'
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Neon database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


@router.get("/debug/config")
async def debug_config():
    """
    Debug endpoint to check environment variable configuration
    """
    return {
        "neon_db_host_set": bool(NEON_DB_HOST),
        "neon_db_user_set": bool(NEON_DB_USER),
        "neon_db_password_set": bool(NEON_DB_PASSWORD),
        "neon_db_name": NEON_DB_NAME,
        "neon_db_port": NEON_DB_PORT
    }


@router.get("/files/{user_id}", response_model=FileResponse)
async def get_user_files(user_id: str):
    """
    Get user's uploaded files from Neon database

    Args:
        user_id: The user's UUID

    Returns:
        FileResponse with list of unique files
    """
    conn = None
    try:
        # Connect to Neon database
        conn = await get_db_connection()

        # Query for files
        query = """
            SELECT DISTINCT file_name, file_url, created_at
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND source = 'file_upload'
              AND file_name IS NOT NULL
              AND file_url IS NOT NULL
            ORDER BY created_at DESC
        """

        rows = await conn.fetch(query, user_id)

        # Deduplicate by file_url (remove chunks of same file)
        unique_files_map = {}
        for row in rows:
            file_url = row['file_url']
            if file_url not in unique_files_map:
                unique_files_map[file_url] = {
                    'file_name': row['file_name'],
                    'file_url': row['file_url'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }

        unique_files = list(unique_files_map.values())

        return FileResponse(success=True, files=unique_files)

    except Exception as e:
        logger.error(f"Error fetching user files from Neon: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/instructions/{user_id}", response_model=InstructionsResponse)
async def get_user_instructions(user_id: str):
    """
    Get user's custom instructions from Neon database

    Args:
        user_id: The user's UUID

    Returns:
        InstructionsResponse with combined instruction text
    """
    conn = None
    try:
        # Connect to Neon database
        conn = await get_db_connection()

        # First, get the most recent created_at timestamp
        timestamp_query = """
            SELECT MAX(created_at) as latest_timestamp
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND source = 'agent_settings'
              AND category = 'custom_instructions'
        """

        timestamp_result = await conn.fetchrow(timestamp_query, user_id)
        latest_timestamp = timestamp_result['latest_timestamp'] if timestamp_result else None

        if not latest_timestamp:
            # No custom instructions found
            return InstructionsResponse(success=True, instructions='')

        # Get all chunks from the most recent save operation
        query = """
            SELECT document
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND source = 'agent_settings'
              AND category = 'custom_instructions'
              AND created_at = $2
            ORDER BY id ASC
        """

        rows = await conn.fetch(query, user_id, latest_timestamp)

        # Combine chunks from the most recent save only
        combined_instructions = '\n\n'.join([row['document'] for row in rows if row['document']])

        return InstructionsResponse(success=True, instructions=combined_instructions)

    except Exception as e:
        logger.error(f"Error fetching custom instructions from Neon: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch instructions: {str(e)}")
    finally:
        if conn:
            await conn.close()
