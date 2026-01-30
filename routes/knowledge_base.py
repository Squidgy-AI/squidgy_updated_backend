"""
Knowledge Base API Routes
Handles fetching user files and custom instructions from Neon database
"""

import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge_base"])

# Neon REST API configuration
NEON_API_URL = os.getenv('NEON_API_URL')
NEON_API_KEY = os.getenv('NEON_API_KEY')


class FileResponse(BaseModel):
    success: bool
    files: List[Dict[str, Any]]


class InstructionsResponse(BaseModel):
    success: bool
    instructions: str


@router.get("/files/{user_id}", response_model=FileResponse)
async def get_user_files(user_id: str):
    """
    Get user's uploaded files from Neon database

    Args:
        user_id: The user's UUID

    Returns:
        FileResponse with list of unique files
    """
    try:
        if not NEON_API_URL or not NEON_API_KEY:
            logger.error("NEON_API_URL or NEON_API_KEY is not configured")
            raise HTTPException(status_code=500, detail="Database configuration missing")

        # Query Neon database for files
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{NEON_API_URL}/sql",
                json={
                    "query": """
                        SELECT DISTINCT file_name, file_url, created_at
                        FROM user_vector_knowledge_base
                        WHERE user_id = $1
                          AND source = 'file_upload'
                          AND file_name IS NOT NULL
                          AND file_url IS NOT NULL
                        ORDER BY created_at DESC
                    """,
                    "params": [user_id]
                },
                headers={
                    "Authorization": f"Bearer {NEON_API_KEY}",
                    "Content-Type": "application/json"
                }
            )

            response.raise_for_status()
            data = response.json()

        # Deduplicate by file_url (remove chunks of same file)
        files = data.get('rows', [])
        unique_files_map = {}

        for file in files:
            file_url = file.get('file_url')
            if file_url and file_url not in unique_files_map:
                unique_files_map[file_url] = file

        unique_files = list(unique_files_map.values())

        return FileResponse(success=True, files=unique_files)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching user files from Neon: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {e.response.text}")
    except Exception as e:
        logger.error(f"Error fetching user files from Neon: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {str(e)}")


@router.get("/instructions/{user_id}", response_model=InstructionsResponse)
async def get_user_instructions(user_id: str):
    """
    Get user's custom instructions from Neon database

    Args:
        user_id: The user's UUID

    Returns:
        InstructionsResponse with combined instruction text
    """
    try:
        if not NEON_API_URL or not NEON_API_KEY:
            logger.error("NEON_API_URL or NEON_API_KEY is not configured")
            raise HTTPException(status_code=500, detail="Database configuration missing")

        # Query Neon database for custom instructions
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{NEON_API_URL}/sql",
                json={
                    "query": """
                        SELECT document, created_at
                        FROM user_vector_knowledge_base
                        WHERE user_id = $1
                          AND source = 'agent_settings'
                          AND category = 'custom_instructions'
                        ORDER BY created_at DESC
                        LIMIT 10
                    """,
                    "params": [user_id]
                },
                headers={
                    "Authorization": f"Bearer {NEON_API_KEY}",
                    "Content-Type": "application/json"
                }
            )

            response.raise_for_status()
            data = response.json()

        instructions = data.get('rows', [])

        # Combine all instruction chunks
        combined_instructions = '\n\n'.join([item.get('document', '') for item in instructions])

        return InstructionsResponse(success=True, instructions=combined_instructions)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching custom instructions from Neon: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch instructions: {e.response.text}")
    except Exception as e:
        logger.error(f"Error fetching custom instructions from Neon: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch instructions: {str(e)}")
