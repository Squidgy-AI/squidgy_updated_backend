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


async def get_connected_accounts(location_id: str, pit_token: str) -> dict:
    """
    Fetch connected social media accounts from GHL and build accountId -> platform mapping
    The accountId in posts is a composite: {accountId}_{locationId}_{platformUserId}
    We need to match by checking if the post's accountId contains the account's id
    """
    account_platform_map = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/accounts",
                headers={
                    "Authorization": f"Bearer {pit_token}",
                    "Version": "2021-07-28",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            
            if response.is_success:
                data = response.json()
                logger.info(f"[SOCIAL POSTS] Accounts API response: {data}")
                accounts = data.get('accounts', []) or data.get('data', []) or []
                
                for account in accounts:
                    account_id = account.get('id') or account.get('_id')
                    platform = account.get('platform', '').lower()
                    # Also get the platform-specific user ID which might be in the composite accountId
                    platform_user_id = account.get('platformUserId') or account.get('userId') or account.get('pageId')
                    
                    if account_id and platform:
                        account_platform_map[account_id] = platform
                        # Also map by platform user ID if available
                        if platform_user_id:
                            account_platform_map[str(platform_user_id)] = platform
                
                logger.info(f"[SOCIAL POSTS] Account platform map: {account_platform_map}")
                        
    except Exception as e:
        logger.warning(f"[SOCIAL POSTS] Error fetching connected accounts: {e}")
    
    return account_platform_map


def resolve_platform_from_account(post: dict, account_platform_map: dict) -> str:
    """
    Resolve the correct platform by checking accountIds against connected accounts
    Post accountIds format: {accountId}_{locationId}_{platformUserId}[_page]
    """
    account_ids = post.get('accountIds', [])
    
    if account_ids:
        for account_id in account_ids:
            # Check direct match first
            if account_id in account_platform_map:
                return account_platform_map[account_id]
            
            # Parse the composite accountId and check each part
            # Format: {accountId}_{locationId}_{platformUserId}[_page]
            parts = account_id.split('_')
            for part in parts:
                if part in account_platform_map:
                    return account_platform_map[part]
            
            # Check if any key in the map is contained in the accountId
            for map_key, platform in account_platform_map.items():
                if map_key in account_id:
                    return platform
            
            # Check for platform suffix indicators
            account_id_lower = account_id.lower()
            if account_id_lower.endswith('_page'):
                return 'facebook'
            
            # Check the last part of the composite ID - Instagram IDs are long numeric (17+ digits)
            # Facebook page IDs are shorter numeric
            if len(parts) >= 3:
                platform_user_id = parts[-1] if not parts[-1] == 'page' else parts[-2]
                # Instagram user IDs typically start with 178... and are 17+ digits
                if platform_user_id.isdigit() and len(platform_user_id) >= 17 and platform_user_id.startswith('178'):
                    return 'instagram'
            
    # Fallback to original platform field (but not 'google' which is wrong)
    original_platform = post.get('platform', '').lower()
    if original_platform and original_platform != 'google':
        return original_platform
    
    return 'unknown'


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
        
        # First, fetch connected accounts to build platform mapping
        account_platform_map = await get_connected_accounts(location_id, pit_token)
        
        # Call GHL API to get posts
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
            
            # Resolve correct platform for each post using accountIds
            for post in posts:
                resolved_platform = resolve_platform_from_account(post, account_platform_map)
                post['platform'] = resolved_platform
            
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


class DeletePostRequest(BaseModel):
    firm_user_id: str
    post_id: str
    agent_id: Optional[str] = "SOL"


@router.delete("/posts/{post_id}")
async def delete_social_post(
    post_id: str,
    firm_user_id: str = Query(..., description="User ID"),
    agent_id: str = Query(default="SOL", description="Agent ID")
):
    """
    Delete a scheduled social media post from GHL
    """
    try:
        credentials = await get_ghl_credentials(firm_user_id, agent_id)
        
        if not credentials:
            raise HTTPException(status_code=404, detail="GHL account not found. Please complete GHL setup.")
        
        location_id = credentials.get('location_id')
        pit_token = credentials.get('pit_token')
        
        if not location_id or not pit_token:
            raise HTTPException(status_code=400, detail="Missing GHL credentials. Please complete setup in Settings.")
        
        # Call GHL API to delete the post
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/{post_id}",
                headers={
                    "Authorization": f"Bearer {pit_token}",
                    "Version": "2021-07-28",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            
            if not response.is_success:
                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail="GHL authentication failed. Please reconnect your GHL account.")
                if response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Post not found or already deleted.")
                raise HTTPException(status_code=response.status_code, detail=f"GHL API error: {response.text}")
            
            logger.info(f"[SOCIAL POSTS] Post {post_id} deleted successfully for user {firm_user_id}")
            
            return {
                "success": True,
                "message": "Post deleted successfully",
                "post_id": post_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOCIAL POSTS] Error deleting post: {e}")
        raise HTTPException(status_code=500, detail=str(e))
