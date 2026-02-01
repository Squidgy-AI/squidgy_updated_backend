"""
GHL Media API Routes
Handles fetching and uploading media files to HighLevel accounts
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ghl", tags=["ghl_media"])

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class MediaResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


async def get_ghl_credentials(user_id: str, agent_id: str = 'social_media_scheduler'):
    """
    Fetch GHL location_id and PIT_Token from ghl_subaccounts table
    """
    try:
        result = supabase.table('ghl_subaccounts')\
            .select('ghl_location_id, pit_token')\
            .eq('firm_user_id', user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not result.data:
            return None

        return {
            'location_id': result.data.get('ghl_location_id'),
            'bearer_token': result.data.get('pit_token')
        }
    except Exception as e:
        logger.error(f"Error fetching GHL credentials: {e}")
        return None


@router.get("/media/{user_id}")
async def get_user_media(user_id: str, agent_id: str = 'social_media_scheduler'):
    """
    Fetch media files from user's HighLevel account
    
    Args:
        user_id: The firm_user_id to fetch media for
        agent_id: The agent_id (defaults to social_media_scheduler)
    
    Returns:
        MediaResponse with list of media files
    """
    try:
        # Get GHL credentials from database
        credentials = await get_ghl_credentials(user_id, agent_id)
        
        if not credentials:
            raise HTTPException(
                status_code=404,
                detail="No HighLevel account found for this user"
            )
        
        location_id = credentials.get('location_id')
        bearer_token = credentials.get('bearer_token')
        
        if not location_id or not bearer_token:
            raise HTTPException(
                status_code=400,
                detail="Missing location_id or bearer token"
            )
        
        # Fetch media from GHL API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://services.leadconnectorhq.com/medias/files",
                params={
                    "altId": location_id,
                    "altType": "location",
                    "sortBy": "createdAt",
                    "sortOrder": "desc",
                    "type": "file"
                },
                headers={
                    "Accept": "application/json",
                    "Version": "2021-07-28",
                    "Authorization": f"Bearer {bearer_token}"
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"GHL API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch media from HighLevel: {response.text}"
                )
            
            data = response.json()
            
            # Transform the response to match our MediaLibrary component format
            media_items = []
            if 'files' in data:
                for file in data['files']:
                    media_items.append({
                        'id': file.get('id', ''),
                        'url': file.get('url', ''),
                        'name': file.get('name', 'Untitled'),
                        'thumbnail': file.get('thumbnailUrl'),
                        'createdAt': file.get('createdAt')
                    })
            
            return MediaResponse(
                success=True,
                data={
                    'media': media_items,
                    'total': len(media_items)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching GHL media: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/media/{user_id}/upload")
async def upload_media(
    user_id: str,
    file: UploadFile = File(...),
    agent_id: str = Form(default='social_media_scheduler')
):
    """
    Upload a file to user's HighLevel media storage
    
    Args:
        user_id: The firm_user_id to upload media for
        file: The file to upload (max 25MB for images, 500MB for videos)
        agent_id: The agent_id (defaults to social_media_scheduler)
    
    Returns:
        MediaResponse with uploaded file details
    """
    try:
        # Get GHL credentials from database
        credentials = await get_ghl_credentials(user_id, agent_id)
        
        if not credentials:
            raise HTTPException(
                status_code=404,
                detail="No HighLevel account found for this user"
            )
        
        location_id = credentials.get('location_id')
        bearer_token = credentials.get('bearer_token')
        
        if not location_id or not bearer_token:
            raise HTTPException(
                status_code=400,
                detail="Missing location_id or bearer token"
            )
        
        # Validate file size (25MB for images, 500MB for videos)
        file_size = 0
        file_content = await file.read()
        file_size = len(file_content)
        
        # Check if it's a video file
        is_video = file.content_type and file.content_type.startswith('video/')
        max_size = 500 * 1024 * 1024 if is_video else 25 * 1024 * 1024  # 500MB or 25MB
        
        if file_size > max_size:
            max_size_mb = 500 if is_video else 25
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
            )
        
        # Upload file to GHL API
        async with httpx.AsyncClient() as client:
            # Prepare multipart form data
            files = {
                'file': (file.filename, file_content, file.content_type)
            }
            data = {
                'locationId': location_id
            }
            
            response = await client.post(
                "https://services.leadconnectorhq.com/medias/upload-file",
                files=files,
                data=data,
                headers={
                    "Accept": "application/json",
                    "Version": "2021-07-28",
                    "Authorization": f"Bearer {bearer_token}"
                },
                timeout=60.0  # Longer timeout for file uploads
            )
            
            if response.status_code != 200:
                logger.error(f"GHL upload error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to upload file to HighLevel: {response.text}"
                )
            
            result = response.json()
            
            # Transform the response
            uploaded_file = {
                'id': result.get('id', ''),
                'url': result.get('url', ''),
                'name': result.get('name', file.filename),
                'thumbnail': result.get('thumbnailUrl'),
                'createdAt': result.get('createdAt')
            }
            
            return MediaResponse(
                success=True,
                data={
                    'file': uploaded_file,
                    'message': 'File uploaded successfully'
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to GHL: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
