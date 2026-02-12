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
import httpx

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


class SemanticSearchRequest(BaseModel):
    query: str
    user_id: str
    agent_id: Optional[str] = None
    limit: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.0


class SearchResult(BaseModel):
    category: str
    file_name: Optional[str]
    document: str
    similarity: float
    created_at: datetime


class SemanticSearchResponse(BaseModel):
    success: bool
    query: str
    results: List[SearchResult]
    count: int


# ============================================================================
# Database Connection
# ============================================================================

async def get_db_connection(max_retries: int = 3, retry_delay: float = 1.0):
    """Create and return a connection to the Neon database with retry logic"""
    import asyncio
    
    if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
        raise HTTPException(status_code=500, detail="Database configuration missing")

    last_error = None
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(
                host=NEON_DB_HOST,
                port=int(NEON_DB_PORT),
                user=NEON_DB_USER,
                password=NEON_DB_PASSWORD,
                database=NEON_DB_NAME,
                ssl='require',
                timeout=30
            )
            return conn
        except Exception as e:
            last_error = e
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
    
    logger.error(f"Failed to connect to Neon database after {max_retries} attempts: {str(last_error)}")
    raise HTTPException(status_code=500, detail=f"Database connection failed: {str(last_error)}")


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

        # Chunk text if longer than 1536 characters
        text = request.instructions.strip()
        chunk_size = 1536
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
        chunk_size = 1536
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
async def delete_file(file_id: str, file_url: Optional[str] = None):
    """
    Delete file and all its chunks from Neon database and Supabase storage

    Args:
        file_id: The UUID of the file record
        file_url: Optional file URL for storage deletion (used if DB record already deleted)

    Returns:
        DeleteResponse with success status
    """
    conn = None
    db_file_url = None
    user_id = None
    agent_id = None
    
    try:
        conn = await get_db_connection()

        # Get file_url to delete all chunks with same file_url
        file_query = """
            SELECT file_url, user_id, agent_id
            FROM user_vector_knowledge_base
            WHERE id = $1
        """

        file_result = await conn.fetchrow(file_query, file_id)

        if file_result:
            db_file_url = file_result['file_url']
            user_id = file_result['user_id']
            agent_id = file_result['agent_id']
        
        # Use provided file_url if DB record not found
        storage_url = db_file_url or file_url
        
        # Delete from Supabase storage first
        if storage_url:
            try:
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
                # URL format: https://xxx.supabase.co/storage/v1/object/public/agentkbs/knowledge-base/userId/agentName/filename
                # Bucket is always 'agentkbs', path starts after bucket name
                # Remove query string from URL if present
                clean_url = storage_url.split('?')[0]
                logger.info(f"File URL for deletion: {clean_url}")
                url_parts = clean_url.split('/')
                logger.info(f"URL parts: {url_parts}")
                
                if 'agentkbs' in url_parts:
                    bucket_index = url_parts.index('agentkbs')
                    storage_path = '/'.join(url_parts[bucket_index + 1:])
                    logger.info(f"Deleting from Supabase storage bucket 'agentkbs': {storage_path}")
                    result = supabase.storage.from_('agentkbs').remove([storage_path])
                    logger.info(f"Supabase delete result: {result}")
                    logger.info(f"Successfully deleted file from Supabase storage")
                else:
                    logger.warning(f"Could not find 'agentkbs' bucket in URL: {clean_url}")
            except Exception as storage_error:
                logger.warning(f"Failed to delete from Supabase storage: {storage_error}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
                # Continue with database deletion even if storage fails
        else:
            logger.warning(f"No file URL available for storage deletion")

        # Delete from database if record exists
        if db_file_url and user_id and agent_id:
            # Delete all chunks with same file_url (multiple chunks per file)
            delete_query = """
                DELETE FROM user_vector_knowledge_base
                WHERE user_id = $1
                  AND agent_id = $2
                  AND file_url = $3
            """

            result = await conn.execute(delete_query, user_id, agent_id, db_file_url)

            # Extract number of deleted rows
            deleted_count = int(result.split()[-1])

            logger.info(f"Deleted file {file_id} and {deleted_count} chunks for user {user_id}, agent {agent_id}")

            return DeleteResponse(
                success=True,
                message=f"File and {deleted_count} chunks deleted successfully"
            )
        else:
            # DB record not found, but we may have deleted from storage
            logger.info(f"File {file_id} not found in database, storage deletion attempted")
            return DeleteResponse(
                success=True,
                message="File not found in database, storage cleanup attempted"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    finally:
        if conn:
            await conn.close()


# ============================================================================
# SEMANTIC SEARCH - Vector Similarity Search
# ============================================================================

async def generate_query_embedding(text: str) -> Optional[list]:
    """
    Generate embedding for search query using OpenRouter API.
    Uses openai/text-embedding-3-small model (1536 dimensions).
    Returns list of floats (embedding vector).
    """
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set, cannot generate embedding")
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://openrouter.ai/api/v1/embeddings',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'openai/text-embedding-3-small',
                    'input': text[:8000]  # Limit input size
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()
                embedding = result.get('data', [{}])[0].get('embedding', [])
                if embedding and len(embedding) > 0:
                    logger.info(f"Generated query embedding ({len(embedding)} dimensions)")
                    return embedding
                else:
                    logger.error("OpenRouter returned empty embedding")
                    return None
            else:
                logger.error(f"OpenRouter embedding failed ({response.status_code}): {response.text}")
                return None
    except Exception as e:
        logger.error(f"Embedding generation error: {str(e)}")
        return None


@router.post("/search", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest = Body(...)):
    """
    Semantic search using vector similarity (cosine distance).
    
    This endpoint allows AI agents to search the knowledge base using natural language queries.
    
    Process:
    1. Generates embedding for the query text using OpenRouter API
    2. Finds most similar documents using pgvector cosine distance
    3. Returns ranked results with similarity scores
    
    Args:
        request: SemanticSearchRequest with query, user_id, optional agent_id, limit, and similarity_threshold
    
    Returns:
        SemanticSearchResponse with ranked search results
    
    Example:
        POST /api/knowledge-base/search
        {
            "query": "What are the company's marketing strategies?",
            "user_id": "user-123",
            "agent_id": "personal_assistant",
            "limit": 5,
            "similarity_threshold": 0.7
        }
    """
    conn = None
    try:
        logger.info(f"Semantic search: query='{request.query}', user_id={request.user_id}, agent_id={request.agent_id}")
        
        # Step 1: Generate embedding for query
        query_embedding = await generate_query_embedding(request.query)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding for query")

        # Step 2: Connect to database
        conn = await get_db_connection()

        # Step 3: Build query with optional filters
        # Using cosine distance: 1 - (a <=> b) gives similarity score (1 = identical, 0 = orthogonal)
        where_clauses = ["embedding IS NOT NULL"]
        params = []
        param_idx = 1

        # Format embedding as PostgreSQL vector string
        vector_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        params.append(vector_str)
        param_idx += 1

        # Add user_id filter
        where_clauses.append(f"user_id = ${param_idx}")
        params.append(request.user_id)
        param_idx += 1

        # Add optional agent_id filter
        if request.agent_id:
            where_clauses.append(f"agent_id = ${param_idx}")
            params.append(request.agent_id)
            param_idx += 1

        # Add similarity threshold filter
        if request.similarity_threshold > 0:
            where_clauses.append(f"(1 - (embedding <=> $1::vector)) >= {request.similarity_threshold}")

        where_clause = " AND ".join(where_clauses)
        
        # Add limit as the last parameter
        params.append(request.limit)

        query = f"""
            SELECT 
                id,
                user_id,
                agent_id,
                category,
                file_name,
                document,
                created_at,
                1 - (embedding <=> $1::vector) as similarity
            FROM user_vector_knowledge_base
            WHERE {where_clause}
            ORDER BY embedding <=> $1::vector
            LIMIT ${param_idx}
        """

        logger.info(f"Executing semantic search with {len(params)} parameters")
        rows = await conn.fetch(query, *params)

        # Step 4: Format results
        results = []
        for row in rows:
            results.append(SearchResult(
                category=row['category'],
                file_name=row['file_name'],
                document=row['document'],
                similarity=float(row['similarity']),
                created_at=row['created_at']
            ))

        logger.info(f"Semantic search found {len(results)} results for user {request.user_id}")

        return SemanticSearchResponse(
            success=True,
            query=request.query,
            results=results,
            count=len(results)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    finally:
        if conn:
            await conn.close()
