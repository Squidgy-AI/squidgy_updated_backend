"""
Knowledge Base API Routes
Handles CRUD operations for user knowledge base in Neon database (user_vector_knowledge_base table)
"""

import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form
from pydantic import BaseModel
import asyncpg
from datetime import datetime
from supabase import create_client, Client
import uuid as uuid_lib

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge_base"])

# Neon PostgreSQL configuration
NEON_DB_HOST = os.getenv('NEON_DB_HOST')
NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
NEON_DB_USER = os.getenv('NEON_DB_USER')
NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def get_supabase_client() -> Client:
    """Create and return a Supabase client"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=500, detail="Supabase configuration missing")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ============================================================================
# Pydantic Models
# ============================================================================

class FileResponse(BaseModel):
    success: bool
    files: List[Dict[str, Any]]


class InstructionsResponse(BaseModel):
    success: bool
    file_id: Optional[str] = None
    instructions: str


class SaveInstructionsRequest(BaseModel):
    user_id: str
    agent_id: str
    agent_name: str
    instructions: str


class UpdateInstructionsRequest(BaseModel):
    user_id: str
    agent_id: str
    instructions: str


class SaveFileRequest(BaseModel):
    user_id: str
    agent_id: str
    agent_name: str
    file_name: str
    file_url: str


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    file_url: Optional[str] = None
    processing_status: Optional[str] = None


class DeleteResponse(BaseModel):
    success: bool
    message: str


# ============================================================================
# Database Connection
# ============================================================================

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


# ============================================================================
# Debug Endpoint
# ============================================================================

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


# ============================================================================
# GET FILES - Fetch previously uploaded files
# ============================================================================

@router.get("/files/{user_id}/{agent_id}", response_model=FileResponse)
async def get_user_files(user_id: str, agent_id: str):
    """
    Get user's uploaded files from Neon database for a specific agent

    Args:
        user_id: The user's UUID
        agent_id: The agent's ID (e.g., 'personal_assistant', 'social_media_agent')

    Returns:
        FileResponse with list of unique files
    """
    conn = None
    try:
        conn = await get_db_connection()

        # Query for files - deduplicate by file_url (multiple chunks per file)
        # Use MIN(id::text)::uuid since MIN() doesn't work directly on UUID type
        query = """
            SELECT
                (MIN(id::text))::uuid as file_id,
                file_name,
                file_url,
                MAX(created_at) as created_at,
                category,
                source
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND agent_id = $2
              AND category = 'documents'
              AND file_name IS NOT NULL
              AND file_url IS NOT NULL
            GROUP BY file_name, file_url, category, source
            ORDER BY MAX(created_at) DESC
        """

        rows = await conn.fetch(query, user_id, agent_id)

        files = [
            {
                'file_id': str(row['file_id']),
                'file_name': row['file_name'],
                'file_url': row['file_url'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'processing_status': 'completed'  # Always completed if in DB
            }
            for row in rows
        ]

        logger.info(f"Fetched {len(files)} files for user {user_id}, agent {agent_id}")
        return FileResponse(success=True, files=files)

    except Exception as e:
        logger.error(f"Error fetching user files from Neon: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ============================================================================
# GET INSTRUCTIONS - Fetch custom instructions
# ============================================================================

@router.get("/instructions/{user_id}/{agent_id}", response_model=InstructionsResponse)
async def get_user_instructions(user_id: str, agent_id: str):
    """
    Get user's custom instructions from Neon database for a specific agent

    Args:
        user_id: The user's UUID
        agent_id: The agent's ID

    Returns:
        InstructionsResponse with combined instruction text and file_id for updates
    """
    conn = None
    try:
        conn = await get_db_connection()

        # Get the most recent created_at timestamp for custom instructions
        timestamp_query = """
            SELECT MAX(created_at) as latest_timestamp
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND agent_id = $2
              AND category = 'custom_instructions'
        """

        timestamp_result = await conn.fetchrow(timestamp_query, user_id, agent_id)
        latest_timestamp = timestamp_result['latest_timestamp'] if timestamp_result else None

        if not latest_timestamp:
            logger.info(f"No custom instructions found for user {user_id}, agent {agent_id}")
            return InstructionsResponse(success=True, file_id=None, instructions='')

        # Get all chunks from the most recent save operation
        query = """
            SELECT id, document
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND agent_id = $2
              AND category = 'custom_instructions'
              AND created_at = $3
            ORDER BY id ASC
        """

        rows = await conn.fetch(query, user_id, agent_id, latest_timestamp)

        if not rows:
            return InstructionsResponse(success=True, file_id=None, instructions='')

        # Use first chunk's ID as the file_id for updates
        file_id = str(rows[0]['id'])

        # Combine all chunks
        combined_instructions = '\n\n'.join([row['document'] for row in rows if row['document']])

        logger.info(f"Fetched custom instructions for user {user_id}, agent {agent_id} (file_id: {file_id})")
        return InstructionsResponse(success=True, file_id=file_id, instructions=combined_instructions)

    except Exception as e:
        logger.error(f"Error fetching custom instructions from Neon: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch instructions: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ============================================================================
# POST INSTRUCTIONS - Create new custom instructions
# ============================================================================

@router.post("/instructions")
async def create_instructions(request: SaveInstructionsRequest = Body(...)):
    """
    Create new custom instructions in Neon database

    Args:
        request: SaveInstructionsRequest with user_id, agent_id, agent_name, instructions

    Returns:
        Success response with file_id
    """
    conn = None
    try:
        conn = await get_db_connection()

        # Chunk text if longer than 1000 characters
        text = request.instructions.strip()
        chunk_size = 1000
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] if len(text) > chunk_size else [text]

        created_at = datetime.utcnow()
        file_id = None

        # Insert all chunks with same timestamp
        for chunk in chunks:
            query = """
                INSERT INTO user_vector_knowledge_base
                (user_id, agent_id, document, category, source, file_name, file_url, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """

            result = await conn.fetchrow(
                query,
                request.user_id,
                request.agent_id,
                chunk,
                'custom_instructions',
                'agent_settings',
                'User Input',
                None,  # No file URL for text
                created_at,
                created_at
            )

            # Use first chunk's ID as file_id
            if file_id is None:
                file_id = str(result['id'])

        logger.info(f"Created custom instructions for user {request.user_id}, agent {request.agent_id} (file_id: {file_id})")

        return {
            "success": True,
            "message": "Custom instructions saved successfully",
            "file_id": file_id
        }

    except Exception as e:
        logger.error(f"Error creating custom instructions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save instructions: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ============================================================================
# PUT INSTRUCTIONS - Update existing custom instructions
# ============================================================================

@router.put("/instructions/{file_id}")
async def update_instructions(file_id: str, request: UpdateInstructionsRequest = Body(...)):
    """
    Update existing custom instructions by deleting old ones and creating new ones

    Args:
        file_id: The ID of the first chunk (used to find all related chunks by timestamp)
        request: UpdateInstructionsRequest with user_id, agent_id, instructions

    Returns:
        Success response
    """
    conn = None
    try:
        conn = await get_db_connection()

        # Get the created_at timestamp of the record we're updating
        timestamp_query = """
            SELECT created_at
            FROM user_vector_knowledge_base
            WHERE id = $1
              AND user_id = $2
              AND agent_id = $3
        """

        timestamp_result = await conn.fetchrow(timestamp_query, file_id, request.user_id, request.agent_id)

        if not timestamp_result:
            raise HTTPException(status_code=404, detail="Custom instructions not found")

        old_timestamp = timestamp_result['created_at']

        # Delete all chunks with the same timestamp (all parts of old instructions)
        delete_query = """
            DELETE FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND agent_id = $2
              AND category = 'custom_instructions'
              AND created_at = $3
        """

        await conn.execute(delete_query, request.user_id, request.agent_id, old_timestamp)

        # Insert new chunks
        text = request.instructions.strip()
        chunk_size = 1000
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] if len(text) > chunk_size else [text]

        created_at = datetime.utcnow()
        new_file_id = None

        for chunk in chunks:
            query = """
                INSERT INTO user_vector_knowledge_base
                (user_id, agent_id, document, category, source, file_name, file_url, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """

            result = await conn.fetchrow(
                query,
                request.user_id,
                request.agent_id,
                chunk,
                'custom_instructions',
                'agent_settings',
                'User Input',
                None,
                created_at,
                created_at
            )

            if new_file_id is None:
                new_file_id = str(result['id'])

        logger.info(f"Updated custom instructions for user {request.user_id}, agent {request.agent_id} (new file_id: {new_file_id})")

        return {
            "success": True,
            "message": "Custom instructions updated successfully",
            "file_id": new_file_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custom instructions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update instructions: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ============================================================================
# POST FILE - Upload file to Supabase and save metadata to Neon
# ============================================================================

@router.post("/file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    agent_id: str = Form(...),
    agent_name: str = Form(...)
):
    """
    Upload file to Supabase storage and save metadata to Neon database.
    Text extraction and embedding generation happens via n8n workflow.

    Args:
        file: The uploaded file
        user_id: The user's UUID
        agent_id: The agent's ID (e.g., 'personal_assistant')
        agent_name: The agent's display name

    Returns:
        FileUploadResponse with file_id and file_url
    """
    conn = None
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Read file content
        file_content = await file.read()
        file_name = file.filename or f"file_{uuid_lib.uuid4()}"
        
        # Generate unique storage path
        unique_id = str(uuid_lib.uuid4())
        storage_path = f"knowledge-base/{user_id}/{agent_id}/{unique_id}_{file_name}"
        
        # Upload to Supabase storage
        try:
            response = supabase.storage.from_('knowledge-base').upload(
                storage_path,
                file_content,
                {
                    "content-type": file.content_type or "application/octet-stream",
                    "upsert": "false"
                }
            )
            
            # Check for upload errors
            if hasattr(response, 'error') and response.error:
                raise HTTPException(status_code=500, detail=f"Storage upload failed: {response.error}")
                
        except Exception as upload_error:
            if "already exists" not in str(upload_error):
                logger.error(f"Supabase upload error: {str(upload_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(upload_error)}")
        
        # Get public URL
        file_url = supabase.storage.from_('knowledge-base').get_public_url(storage_path)
        
        # Save metadata to Neon database
        conn = await get_db_connection()

        query = """
            INSERT INTO user_vector_knowledge_base
            (user_id, agent_id, document, category, source, file_name, file_url, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """

        created_at = datetime.utcnow()

        result = await conn.fetchrow(
            query,
            user_id,
            agent_id,
            f"File uploaded: {file_name}",  # Placeholder until extraction
            'documents',
            'file_upload',
            file_name,
            file_url,
            created_at,
            created_at
        )

        file_id = str(result['id'])

        logger.info(f"Uploaded file for user {user_id}, agent {agent_id}: {file_name} (file_id: {file_id})")

        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            file_id=file_id,
            file_url=file_url,
            processing_status="pending"
        )

    except Exception as e:
        logger.error(f"Error saving file metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ============================================================================
# DELETE FILE - Delete file and all its chunks
# ============================================================================

@router.delete("/file/{file_id}", response_model=DeleteResponse)
async def delete_file(file_id: str):
    """
    Delete file and all its chunks from Neon database

    Args:
        file_id: The UUID of the file record

    Returns:
        DeleteResponse with success status
    """
    conn = None
    try:
        conn = await get_db_connection()

        # Get file_url to delete all chunks with same file_url
        file_query = """
            SELECT file_url, user_id, agent_id
            FROM user_vector_knowledge_base
            WHERE id = $1
        """

        file_result = await conn.fetchrow(file_query, file_id)

        if not file_result:
            raise HTTPException(status_code=404, detail="File not found")

        file_url = file_result['file_url']
        user_id = file_result['user_id']
        agent_id = file_result['agent_id']

        # Delete all chunks with same file_url (multiple chunks per file)
        delete_query = """
            DELETE FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND agent_id = $2
              AND file_url = $3
        """

        result = await conn.execute(delete_query, user_id, agent_id, file_url)

        # Extract number of deleted rows
        deleted_count = int(result.split()[-1])

        logger.info(f"Deleted file {file_id} and {deleted_count} chunks for user {user_id}, agent {agent_id}")

        return DeleteResponse(
            success=True,
            message=f"File and {deleted_count} chunks deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    finally:
        if conn:
            await conn.close()
