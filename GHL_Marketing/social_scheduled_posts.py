"""
Social Media - Scheduled Posts API Routes
Fetches social media posts from GHL API using pit_token for Authorization
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx
from supabase import create_client, Client
from datetime import datetime

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
            .select('ghl_location_id, pit_token')\
            .eq('firm_user_id', firm_user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not ghl_result.data:
            return None

        return {
            'location_id': ghl_result.data.get('ghl_location_id'),
            'pit_token': ghl_result.data.get('pit_token')
        }
    except Exception as e:
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
                
                        
    except Exception as e:
        pass
    
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
            
            # Check draft status for each post from post_confirmation_checker
            post_ids = [p.get('_id') or p.get('id') for p in posts if p.get('_id') or p.get('id')]
            if post_ids:
                try:
                    draft_check = supabase.table('post_confirmation_checker')\
                        .select('post_id, status')\
                        .eq('user_id', request.firm_user_id)\
                        .in_('post_id', post_ids)\
                        .execute()
                    
                    draft_map = {item['post_id']: item['status'] == 'drafted' for item in draft_check.data} if draft_check.data else {}
                    
                    for post in posts:
                        post_id = post.get('_id') or post.get('id')
                        # Check if post is in draft table OR has 2099 schedule date (fallback for old posts)
                        schedule_date = post.get('scheduleDate', '')
                        if (post_id and draft_map.get(post_id)) or (schedule_date and schedule_date.startswith('2099')):
                            post['isDrafted'] = True
                except Exception as e:
                    pass
            
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/{firm_user_id}")
async def get_social_posts_by_user(
    firm_user_id: str,
    agent_id: str = Query(default="SOL", description="Agent ID")
):
    """GET endpoint for fetching social posts by user ID"""
    return await get_social_posts(ScheduledPostsRequest(firm_user_id=firm_user_id, agent_id=agent_id))


@router.get("/accounts/{firm_user_id}")
async def get_social_accounts(
    firm_user_id: str,
    agent_id: str = Query(default="SOL", description="Agent ID")
):
    """Get connected social media accounts for a user"""
    try:
        credentials = await get_ghl_credentials(firm_user_id, agent_id)
        
        if not credentials:
            raise HTTPException(status_code=404, detail="GHL account not found.")
        
        location_id = credentials.get('location_id')
        pit_token = credentials.get('pit_token')
        
        if not location_id or not pit_token:
            raise HTTPException(status_code=400, detail="Missing GHL credentials.")
        
        # Fetch accounts directly from GHL API
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
            
            accounts = []
            if response.is_success:
                data = response.json()
                
                # Handle nested response: results.accounts
                raw_accounts = []
                if 'results' in data and 'accounts' in data['results']:
                    raw_accounts = data['results']['accounts']
                elif 'accounts' in data:
                    raw_accounts = data['accounts']
                elif 'data' in data:
                    raw_accounts = data['data']
                
                for acc in raw_accounts:
                    acc_id = acc.get('id') or acc.get('_id')
                    platform = acc.get('platform', '').lower()
                    name = acc.get('name') or acc.get('pageName') or acc.get('username') or platform.capitalize()
                    
                    if acc_id:
                        accounts.append({
                            "id": acc_id,
                            "platform": platform,
                            "name": name
                        })
        
        return {
            "success": True,
            "accounts": accounts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DeletePostRequest(BaseModel):
    firm_user_id: str
    post_id: str
    agent_id: Optional[str] = "SOL"


@router.get("/posts/check-draft/{post_id}")
async def check_post_draft_status(
    post_id: str,
    firm_user_id: str = Query(..., description="User ID")
):
    """
    Check if a post is drafted by checking post_confirmation_checker table
    """
    try:
        result = supabase.table('post_confirmation_checker')\
            .select('status')\
            .eq('post_id', post_id)\
            .eq('user_id', firm_user_id)\
            .execute()
        
        if not result.data:
            return {"is_drafted": False}
        
        status = result.data[0].get('status', '')
        return {"is_drafted": status == 'drafted'}
        
    except Exception as e:
        return {"is_drafted": False}


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
            
            
            # Update post_confirmation_checker table
            try:
                # Delete the corresponding record
                supabase.table('post_confirmation_checker')\
                    .delete()\
                    .eq('post_id', post_id)\
                    .execute()
                    
                
            except Exception as e:
                    pass
            
            return {
                "success": True,
                "message": "Post deleted successfully",
                "post_id": post_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EditPostRequest(BaseModel):
    firm_user_id: str
    post_id: str
    summary: Optional[str] = None
    schedule_date: Optional[str] = None
    media: Optional[List[dict]] = None
    account_ids: Optional[List[str]] = None
    post_type: Optional[str] = None
    agent_id: Optional[str] = "SOL"


@router.put("/posts/{post_id}")
async def edit_social_post(
    post_id: str,
    request: EditPostRequest
):
    """
    Edit a scheduled social media post by deleting and recreating it.
    GHL's PUT endpoint publishes immediately, so delete + recreate is required
    to preserve scheduling.
    """
    try:
        credentials = await get_ghl_credentials(request.firm_user_id, request.agent_id)
        
        if not credentials:
            raise HTTPException(status_code=404, detail="GHL account not found. Please complete GHL setup.")
        
        location_id = credentials.get('location_id')
        pit_token = credentials.get('pit_token')
        
        if not location_id or not pit_token:
            raise HTTPException(status_code=400, detail="Missing GHL credentials. Please complete setup in Settings.")
        
        headers = {
            "Authorization": f"Bearer {pit_token}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            # Step 1: Fetch the existing post
            get_response = await client.get(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/{post_id}",
                headers=headers,
                timeout=30.0
            )
            
            if not get_response.is_success:
                raise HTTPException(status_code=get_response.status_code, detail=f"Failed to fetch post: {get_response.text}")
            
            existing_post = get_response.json()
            post_data = existing_post
            if 'results' in existing_post and 'post' in existing_post['results']:
                post_data = existing_post['results']['post']
            elif 'post' in existing_post:
                post_data = existing_post['post']
            
            
            # Check if post is already published - cannot edit published posts
            post_status = post_data.get('status', '').lower()
            if post_status == 'published':
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot edit a published post. This post has already been published to social media."
                )
            
            # Get accountIds
            account_ids = request.account_ids if request.account_ids else post_data.get('accountIds', [])
            if not account_ids:
                single_account_id = post_data.get('accountId')
                if single_account_id:
                    account_ids = [single_account_id]
            
            if not account_ids:
                raise HTTPException(status_code=400, detail="No accountIds found in post data")
            
            # Step 2: Delete the existing post
            delete_response = await client.delete(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/{post_id}",
                headers=headers,
                timeout=30.0
            )
            
            logger.info(f"[SOCIAL POSTS] DELETE response: {delete_response.status_code} - {delete_response.text}")
            
            if not delete_response.is_success:
                raise HTTPException(
                    status_code=delete_response.status_code,
                    detail=f"Failed to delete post: {delete_response.text}"
                )
            
            # Step 3: Recreate with edits applied (fall back to original values)
            create_payload = {
                'userId': location_id,
                'type': request.post_type or post_data.get('type', 'post'),
                'status': 'scheduled',
                'scheduleDate': request.schedule_date or post_data.get('scheduleDate'),
                'accountIds': account_ids,
                'media': request.media if request.media is not None else post_data.get('media', []),
                'summary': request.summary if request.summary is not None else post_data.get('summary', ''),
            }
            
            # Preserve platform-specific details (but exclude problematic fields)
            for detail_key in ['facebookPostDetails', 'instagramPostDetails',
                               'linkedinPostDetails', 'twitterPostDetails',
                               'tiktokPostDetails', 'youtubePostDetails',
                               'googlePostDetails', 'pinterestPostDetails']:
                if post_data.get(detail_key):
                    details = post_data[detail_key].copy() if isinstance(post_data[detail_key], dict) else post_data[detail_key]
                    # Remove shortenedLinks as it can cause issues
                    if isinstance(details, dict) and 'shortenedLinks' in details:
                        del details['shortenedLinks']
                    create_payload[detail_key] = details
            
            # Preserve tags/categories
            if post_data.get('tags'):
                create_payload['tags'] = post_data['tags']
            if post_data.get('categoryId'):
                create_payload['categoryId'] = post_data['categoryId']
            
            logger.info(f"[SOCIAL POSTS] CREATE payload: {create_payload}")
            
            create_response = await client.post(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts",
                headers=headers,
                json=create_payload,
                timeout=30.0
            )
            
            logger.info(f"[SOCIAL POSTS] CREATE response: {create_response.status_code} - {create_response.text}")
            
            if not create_response.is_success:
                logger.error(
                    f"[SOCIAL POSTS] Failed to recreate post after deletion! "
                    f"Original post data preserved in logs. Status: {create_response.status_code}"
                )
                raise HTTPException(
                    status_code=create_response.status_code,
                    detail=f"Post was deleted but failed to recreate: {create_response.text}"
                )
            
            create_result = create_response.json()
            
            # Extract the new post ID from the CREATE response
            new_post_data = create_result
            new_post_id = 'unknown'
            
            # Check if the response has the expected nested structure
            if 'results' in create_result and 'post' in create_result['results']:
                new_post_data = create_result['results']['post']
                new_post_id = new_post_data.get('_id', 'unknown')
            elif 'post' in create_result:
                new_post_data = create_result['post']
                new_post_id = new_post_data.get('_id', 'unknown')
            else:
                # CREATE response doesn't include post data, fetch the latest post
                logger.warning(f"[SOCIAL POSTS] CREATE response missing post ID, fetching latest post")
                
                import asyncio
                await asyncio.sleep(1.5)  # Wait for GHL to process
                
                # Fetch the most recent post
                fetch_response = await client.post(
                    f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/list",
                    headers=headers,
                    json={"skip": "0", "limit": "1"},
                    timeout=30.0
                )
                
                if fetch_response.is_success:
                    fetch_result = fetch_response.json()
                    
                    # Try different response structures
                    posts = fetch_result.get('posts', [])
                    if not posts and 'results' in fetch_result:
                        posts = fetch_result['results'] if isinstance(fetch_result['results'], list) else fetch_result['results'].get('posts', [])
                    
                    if posts:
                        latest_post = posts[0]
                        new_post_id = latest_post.get('_id', 'unknown')
                        new_post_data = latest_post
                    else:
                        logger.error(f"[SOCIAL POSTS] No posts found in fetch response")
                else:
                    logger.error(f"[SOCIAL POSTS] Failed to fetch posts: {fetch_response.status_code}")
            
            
            # Update post_confirmation_checker table
            try:
                # Delete the old record using the old post_id
                delete_result = supabase.table('post_confirmation_checker')\
                    .delete()\
                    .eq('post_id', post_id)\
                    .execute()
                
                
                # Only insert if we successfully got the new post ID
                if new_post_id != 'unknown':
                    # Create new record with the NEW post_id from recreation
                    checker_payload = {
                        'user_id': request.firm_user_id,
                        'payload': create_payload,
                        'scheduled_for': request.schedule_date or post_data.get('displayDate') or post_data.get('scheduleDate'),
                        'ghl_location_id': location_id,
                        'platform': resolve_platform_from_account(post_data, {}),
                        'post_id': new_post_id,  # Use the NEW post ID
                        'status': 'scheduled'
                    }
                    
                    # Insert the new record - should work now since old one is deleted
                    insert_result = supabase.table('post_confirmation_checker')\
                        .insert(checker_payload)\
                        .execute()
                else:
                    logger.warning(f"[SOCIAL POSTS] Skipping post_confirmation_checker insert - could not determine new post ID")
                
            except Exception as e:
                logger.error(f"[SOCIAL POSTS] Failed to update post_confirmation_checker: {e}")
            
            return {
                "success": True,
                "message": "Post updated successfully",
                "old_post_id": post_id,
                "new_post_id": new_post_id,
                "ghl_response": create_result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/posts/{post_id}/postpone")
async def postpone_social_post(
    post_id: str,
    firm_user_id: str = Query(..., description="User ID"),
    agent_id: str = Query(default="SOL", description="Agent ID")
):
    """
    Postpone a scheduled social media post by deleting it and recreating 
    with a far future schedule date. The edit API appears to publish 
    immediately, so delete + recreate is the safer approach.
    """
    try:
        credentials = await get_ghl_credentials(firm_user_id, agent_id)
        
        if not credentials:
            raise HTTPException(status_code=404, detail="GHL account not found. Please complete GHL setup.")
        
        location_id = credentials.get('location_id')
        pit_token = credentials.get('pit_token')
        
        if not location_id or not pit_token:
            raise HTTPException(status_code=400, detail="Missing GHL credentials. Please complete setup in Settings.")
        
        headers = {
            "Authorization": f"Bearer {pit_token}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            # Step 1: Fetch the existing post
            get_response = await client.get(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/{post_id}",
                headers=headers,
                timeout=30.0
            )
            
            if not get_response.is_success:
                raise HTTPException(
                    status_code=get_response.status_code, 
                    detail=f"Failed to fetch post: {get_response.text}"
                )
            
            existing_post = get_response.json()
            
            # Parse nested response
            post_data = existing_post
            if 'results' in existing_post and 'post' in existing_post['results']:
                post_data = existing_post['results']['post']
            elif 'post' in existing_post:
                post_data = existing_post['post']
            
            
            # Check if post is already published - cannot postpone published posts
            post_status = post_data.get('status', '').lower()
            if post_status == 'published':
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot postpone a published post. This post has already been published to social media."
                )
            
            # Get accountIds
            account_ids = post_data.get('accountIds', [])
            if not account_ids:
                single_account_id = post_data.get('accountId')
                if single_account_id:
                    account_ids = [single_account_id]
            
            if not account_ids:
                raise HTTPException(status_code=400, detail="No accountIds found in post data")
            
            # Step 2: Delete the existing post
            delete_response = await client.delete(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/{post_id}",
                headers=headers,
                timeout=30.0
            )
            
            logger.info(f"[SOCIAL POSTS] DELETE response: {delete_response.status_code} - {delete_response.text}")
            
            if not delete_response.is_success:
                raise HTTPException(
                    status_code=delete_response.status_code, 
                    detail=f"Failed to delete post: {delete_response.text}"
                )
            
            # Step 3: Recreate the post with the postponed schedule date (2099)
            schedule_date = "2099-12-31T23:59:59.999Z"
            create_payload = {
                'userId': location_id,
                'type': post_data.get('type', 'post'),
                'status': 'scheduled',
                'scheduleDate': schedule_date,
                'accountIds': account_ids,
                'media': post_data.get('media', []),
                'summary': post_data.get('summary', ''),
            }
            
            # Include platform-specific details if they exist
            for detail_key in ['facebookPostDetails', 'instagramPostDetails', 
                               'linkedinPostDetails', 'twitterPostDetails',
                               'tiktokPostDetails', 'youtubePostDetails',
                               'googlePostDetails', 'pinterestPostDetails']:
                if post_data.get(detail_key):
                    create_payload[detail_key] = post_data[detail_key]
            
            # Include tags/categories if present
            if post_data.get('tags'):
                create_payload['tags'] = post_data['tags']
            if post_data.get('categoryId'):
                create_payload['categoryId'] = post_data['categoryId']
            
            logger.info(f"[SOCIAL POSTS] CREATE payload: {create_payload}")
            
            create_response = await client.post(
                f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts",
                headers=headers,
                json=create_payload,
                timeout=30.0
            )
            
            logger.info(f"[SOCIAL POSTS] CREATE response: {create_response.status_code} - {create_response.text}")
            
            if not create_response.is_success:
                logger.error(
                    f"[SOCIAL POSTS] Failed to recreate post after deletion! "
                    f"Original post data preserved in logs. Status: {create_response.status_code}"
                )
                raise HTTPException(
                    status_code=create_response.status_code, 
                    detail=f"Post was deleted but failed to recreate: {create_response.text}"
                )
            
            create_result = create_response.json()
            
            # Extract the new post ID from the CREATE response
            new_post_data = create_result
            new_post_id = 'unknown'
            
            # Check if the response has the expected nested structure
            if 'results' in create_result and 'post' in create_result['results']:
                new_post_data = create_result['results']['post']
                new_post_id = new_post_data.get('_id', 'unknown')
            elif 'post' in create_result:
                new_post_data = create_result['post']
                new_post_id = new_post_data.get('_id', 'unknown')
            else:
                # CREATE response doesn't include post data, fetch the latest post
                logger.warning(f"[SOCIAL POSTS] CREATE response missing post ID, fetching latest post")
                
                import asyncio
                await asyncio.sleep(1.5)  # Wait for GHL to process
                
                # Fetch the most recent post
                fetch_response = await client.post(
                    f"https://services.leadconnectorhq.com/social-media-posting/{location_id}/posts/list",
                    headers=headers,
                    json={"skip": "0", "limit": "1"},
                    timeout=30.0
                )
                
                if fetch_response.is_success:
                    fetch_result = fetch_response.json()
                    
                    # Try different response structures
                    posts = fetch_result.get('posts', [])
                    if not posts and 'results' in fetch_result:
                        posts = fetch_result['results'] if isinstance(fetch_result['results'], list) else fetch_result['results'].get('posts', [])
                    
                    if posts:
                        latest_post = posts[0]
                        new_post_id = latest_post.get('_id', 'unknown')
                        new_post_data = latest_post
                    else:
                        logger.error(f"[SOCIAL POSTS] No posts found in fetch response")
                else:
                    logger.error(f"[SOCIAL POSTS] Failed to fetch posts: {fetch_response.status_code}")
            
            
            # Update post_confirmation_checker table
            try:
                # Delete the old record using the old post_id
                delete_result = supabase.table('post_confirmation_checker')\
                    .delete()\
                    .eq('post_id', post_id)\
                    .execute()
                
                
                # Only insert if we successfully got the new post ID
                if new_post_id != 'unknown':
                    # Create new record with the NEW post_id from recreation
                    checker_payload = {
                        'user_id': firm_user_id,
                        'payload': create_payload,
                        'scheduled_for': schedule_date,
                        'ghl_location_id': location_id,
                        'platform': resolve_platform_from_account(post_data, {}),
                        'post_id': new_post_id,  # Use the NEW post ID
                        'status': 'drafted'
                    }
                    
                    # Insert the new record - should work now since old one is deleted
                    insert_result = supabase.table('post_confirmation_checker')\
                        .insert(checker_payload)\
                        .execute()
                else:
                    logger.warning(f"[SOCIAL POSTS] Skipping post_confirmation_checker insert - could not determine new post ID")
                
            except Exception as e:
                logger.error(f"[SOCIAL POSTS] Failed to update post_confirmation_checker: {e}")
            
            return {
                "success": True,
                "message": f"Post postponed successfully to {schedule_date}",
                "old_post_id": post_id,
                "new_post_id": new_post_id,
                "new_schedule_date": schedule_date,
                "ghl_response": create_result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))