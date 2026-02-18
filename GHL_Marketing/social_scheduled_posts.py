"""
Social Media - Scheduled Posts API Routes
Fetches social media posts from GHL API using pit_token
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social/scheduled", tags=["social_scheduled"])

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class ScheduledPostsRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"


class ScheduledPostsResponse(BaseModel):
    success: bool
    posts: Optional[List[dict]] = None
    total_count: Optional[int] = None
    error: Optional[str] = None


async def get_ghl_credentials(firm_user_id: str, agent_id: str = "SOL"):
    """
    Fetch GHL location_id and pit_token from ghl_subaccounts table
    """
    try:
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('ghl_location_id, pit_token, access_token')\
            .eq('firm_user_id', firm_user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not ghl_result.data:
            logger.warning(f"[SOCIAL POSTS] No GHL record found for user: {firm_user_id}")
            return None

        return {
            'location_id': ghl_result.data.get('ghl_location_id'),
            'pit_token': ghl_result.data.get('access_token') or ghl_result.data.get('pit_token')
        }
    except Exception as e:
        logger.error(f"[SOCIAL POSTS] Error fetching GHL credentials: {e}")
        return None


@router.post("/posts")
async def get_social_posts(request: ScheduledPostsRequest):
    """
    Get social media posts from GHL API
    """
    try:
        credentials = await get_ghl_credentials(request.firm_user_id, request.agent_id)
        
        if not credentials:
            raise HTTPException(status_code=404, detail="GHL account not found. Please complete GHL setup.")
        
        location_id = credentials.get('location_id')
        pit_token = credentials.get('pit_token')
        
        if not location_id or not pit_token:
            raise HTTPException(status_code=400, detail="Missing GHL credentials. Please complete setup in Settings.")
        
        # Call GHL API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/list",
                headers={
                    "Authorization": f"Bearer {pit_token}",
                    "Version": "2021-07-28",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={"skip": "0", "limit": "50"},
                timeout=30.0
            )
            
            if not response.is_success:
                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail="GHL authentication failed. Please reconnect your GHL account.")
                raise HTTPException(status_code=response.status_code, detail=f"GHL API error: {response.text}")
            
            data = response.json()
            
            # Extract posts from response
            posts = []
            if data.get('posts'):
                posts = data['posts']
            elif data.get('results'):
                results = data['results']
                posts = results if isinstance(results, list) else results.get('posts', [])
            
            # Separate by status
            scheduled = [p for p in posts if p.get('status', '').lower() in ['scheduled', 'pending', 'draft', 'queued']]
            published = [p for p in posts if p.get('status', '').lower() == 'published']
            
            return {
                "success": True,
                "posts": posts,
                "scheduled_count": len(scheduled),
                "published_count": len(published),
                "total_count": len(posts)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOCIAL POSTS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/{firm_user_id}")
async def get_social_posts_by_user(
    firm_user_id: str,
    agent_id: str = Query(default="SOL", description="Agent ID")
):
    """GET endpoint for fetching social posts by user ID"""
    return await get_social_posts(ScheduledPostsRequest(firm_user_id=firm_user_id, agent_id=agent_id))
