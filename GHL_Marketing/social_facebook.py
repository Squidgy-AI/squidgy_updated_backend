"""
Social Media - Facebook API Routes
Handles Facebook OAuth, pages fetching, and account connections for social media posting
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social/facebook", tags=["social_facebook"])

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class SocialMediaResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class StartOAuthRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"


class GetPagesRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"
    oauth_id: str


class ConnectPageRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"
    oauth_id: str
    origin_id: str
    name: str
    avatar: Optional[str] = None


async def get_ghl_tokens(firm_user_id: str, agent_id: str = "SOL"):
    """
    Fetch GHL location_id, Firebase Token, and Access Token from ghl_subaccounts table
    """
    try:
        logger.info(f"[SOCIAL FB] Fetching GHL tokens for user: {firm_user_id}, agent: {agent_id}")

        # Get all tokens from ghl_subaccounts table
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('ghl_location_id, firebase_token, pit_token, soma_ghl_user_id, agency_user_id, access_token')\
            .eq('firm_user_id', firm_user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not ghl_result.data:
            logger.warning(f"[SOCIAL FB] No ghl_subaccounts record found for user: {firm_user_id}")
            return None

        logger.info(f"[SOCIAL FB] Found GHL location: {ghl_result.data.get('ghl_location_id')}")

        return {
            'location_id': ghl_result.data.get('ghl_location_id'),
            'firebase_token': ghl_result.data.get('firebase_token'),
            'access_token': ghl_result.data.get('access_token') or ghl_result.data.get('pit_token'),
            'soma_ghl_user_id': ghl_result.data.get('soma_ghl_user_id'),  # Reference only
            'agency_user_id': ghl_result.data.get('agency_user_id')  # For API calls
        }
    except Exception as e:
        logger.error(f"Error fetching GHL tokens: {e}")
        return None


@router.post("/start-oauth")
async def start_facebook_oauth(request: StartOAuthRequest):
    """
    Generate Facebook OAuth URL for social media posting

    Args:
        request: StartOAuthRequest with firm_user_id and agent_id

    Returns:
        OAuth URL to open in popup window
    """
    try:
        # Get GHL credentials
        tokens = await get_ghl_tokens(request.firm_user_id, request.agent_id)

        if not tokens or not tokens.get('location_id'):
            raise HTTPException(
                status_code=404,
                detail="GHL account not found or missing required data"
            )

        location_id = tokens['location_id']
        soma_ghl_user_id = tokens.get('soma_ghl_user_id')

        if not soma_ghl_user_id:
            raise HTTPException(
                status_code=404,
                detail="Missing soma_ghl_user_id - GHL user not created"
            )

        # Construct OAuth URL with soma_ghl_user_id (created during subaccount setup)
        # NOTE: agency_user_id is used for Facebook accounts API endpoint, NOT OAuth start URL
        oauth_url = f"https://backend.leadconnectorhq.com/social-media-posting/oauth/facebook/start?locationId={location_id}&userId={soma_ghl_user_id}"

        return {
            "success": True,
            "oauth_url": oauth_url,
            "location_id": location_id,
            "user_id": soma_ghl_user_id  # Return soma_ghl_user_id for OAuth
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Facebook OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connected-accounts")
async def get_connected_facebook_accounts(request: StartOAuthRequest):
    """
    Get all connected Facebook accounts from GHL

    Args:
        request: StartOAuthRequest with firm_user_id and agent_id

    Returns:
        List of connected Facebook accounts with their OAuth IDs
    """
    try:
        # Get GHL credentials
        tokens = await get_ghl_tokens(request.firm_user_id, request.agent_id)

        if not tokens:
            raise HTTPException(
                status_code=404,
                detail="GHL account not found"
            )

        location_id = tokens['location_id']
        firebase_token = tokens['firebase_token']

        if not location_id or not firebase_token:
            # Provide helpful error message for users without tokens
            raise HTTPException(
                status_code=400,
                detail="Missing firebase_token. Please refresh your GHL connection. Call POST /api/ghl/refresh-tokens/{firm_user_id} to fix this."
            )

        logger.info(f"[SOCIAL FB] Fetching connected accounts for location: {location_id}")

        # Call GHL API to get all accounts
        # NOTE: Using token-id ONLY (no authorization header needed - verified via testing)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://backend.leadconnectorhq.com/social-media-posting/{location_id}/accounts",
                params={"fetchAll": "true"},
                headers={
                    "token-id": firebase_token,
                    "version": "2021-07-28",
                    "channel": "APP",
                    "source": "WEB_USER",
                    "accept": "application/json"
                },
                timeout=30.0
            )

            if not response.is_success:
                logger.error(f"[SOCIAL FB] GHL API returned {response.status_code}: {response.text}")

                # Provide more helpful error messages
                if response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="GHL authentication failed. Your access tokens may be expired. Please reconnect your GHL account in Settings."
                    )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"GHL API error: {response.text}"
                    )

            data = response.json()

            # Filter for Facebook accounts only
            facebook_accounts = []
            if data.get('success') and data.get('results', {}).get('accounts'):
                facebook_accounts = [
                    acc for acc in data['results']['accounts']
                    if acc.get('platform') == 'facebook'
                ]

            return {
                "success": True,
                "accounts": facebook_accounts,
                "total_count": len(facebook_accounts)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching connected Facebook accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/available-pages")
async def get_available_facebook_pages(request: GetPagesRequest):
    """
    Get available Facebook pages for a specific OAuth ID

    Args:
        request: GetPagesRequest with firm_user_id, agent_id, and oauth_id

    Returns:
        List of available Facebook pages that can be connected
    """
    try:
        # Get GHL credentials
        tokens = await get_ghl_tokens(request.firm_user_id, request.agent_id)

        if not tokens:
            raise HTTPException(
                status_code=404,
                detail="GHL account not found"
            )

        location_id = tokens['location_id']
        firebase_token = tokens['firebase_token']

        if not location_id or not firebase_token:
            # Provide helpful error message for users without tokens
            raise HTTPException(
                status_code=400,
                detail="Missing firebase_token. Please refresh your GHL connection. Call POST /api/ghl/refresh-tokens/{firm_user_id} to fix this."
            )

        # Call GHL API to get available pages
        # NOTE: Using token-id ONLY (no authorization header needed - verified via testing)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://backend.leadconnectorhq.com/social-media-posting/oauth/{location_id}/facebook/accounts/{request.oauth_id}",
                headers={
                    "token-id": firebase_token,
                    "version": "2021-07-28",
                    "channel": "APP",
                    "source": "WEB_USER",
                    "accept": "application/json"
                },
                timeout=30.0
            )

            if not response.is_success:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GHL API error: {response.text}"
                )

            data = response.json()

            pages = []
            if data.get('success') and data.get('results', {}).get('pages'):
                pages = data['results']['pages']

            # Save fetched pages to ghl_subaccounts table
            try:
                supabase.table('ghl_subaccounts').update({
                    'pages': pages,
                    'updated_at': __import__('datetime').datetime.now().isoformat()
                }).eq('firm_user_id', request.firm_user_id).eq('agent_id', request.agent_id).execute()
                logger.info(f"[SOCIAL FB] Saved {len(pages)} available pages to database")
            except Exception as db_error:
                logger.warning(f"[SOCIAL FB] Could not save pages to database: {db_error}")
                # Don't fail the request if database save fails

            return {
                "success": True,
                "pages": pages,
                "total_count": len(pages),
                "oauth_id": request.oauth_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching available Facebook pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect-page")
async def connect_facebook_page(request: ConnectPageRequest):
    """
    Connect a specific Facebook page for social media posting

    Args:
        request: ConnectPageRequest with firm_user_id, agent_id, oauth_id, and page details

    Returns:
        Success response with connected page details
    """
    try:
        # Get GHL credentials
        tokens = await get_ghl_tokens(request.firm_user_id, request.agent_id)

        if not tokens:
            raise HTTPException(
                status_code=404,
                detail="GHL account not found"
            )

        location_id = tokens['location_id']
        firebase_token = tokens['firebase_token']

        if not location_id or not firebase_token:
            # Provide helpful error message for users without tokens
            raise HTTPException(
                status_code=400,
                detail="Missing firebase_token. Please refresh your GHL connection. Call POST /api/ghl/refresh-tokens/{firm_user_id} to fix this."
            )

        # Prepare request body
        connect_body = {
            "originId": request.origin_id,
            "platform": "facebook",
            "type": "page",
            "name": request.name,
            "avatar": request.avatar or ""
        }

        # Call GHL API to connect the page
        # NOTE: Using token-id ONLY (no authorization header needed - verified via testing)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://backend.leadconnectorhq.com/social-media-posting/oauth/{location_id}/facebook/accounts/{request.oauth_id}",
                json=connect_body,
                headers={
                    "token-id": firebase_token,
                    "version": "2021-07-28",
                    "channel": "APP",
                    "source": "WEB_USER",
                    "accept": "application/json",
                    "content-type": "application/json"
                },
                timeout=30.0
            )

            if not response.is_success:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"message": response.text}
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get('message', f"GHL API error: {response.status_code}")
                )

            data = response.json()

            # Save connected page to ghl_subaccounts table
            try:
                # Get current connected_pages
                ghl_result = supabase.table('ghl_subaccounts').select(
                    'connected_pages'
                ).eq('firm_user_id', request.firm_user_id).eq('agent_id', request.agent_id).execute()

                current_connected_pages = []
                if ghl_result.data and ghl_result.data[0].get('connected_pages'):
                    current_connected_pages = ghl_result.data[0]['connected_pages']

                # Create page data object
                new_page = {
                    "originId": request.origin_id,
                    "name": request.name,
                    "avatar": request.avatar or "",
                    "platform": "facebook",
                    "type": "page",
                    "oauth_id": request.oauth_id,
                    "connected_at": __import__('datetime').datetime.now().isoformat()
                }

                # Check if page already exists (by originId)
                page_exists = any(
                    page.get('originId') == request.origin_id
                    for page in current_connected_pages
                )

                if not page_exists:
                    current_connected_pages.append(new_page)

                # Update database
                supabase.table('ghl_subaccounts').update({
                    'connected_pages': current_connected_pages,
                    'updated_at': __import__('datetime').datetime.now().isoformat()
                }).eq('firm_user_id', request.firm_user_id).eq('agent_id', request.agent_id).execute()

                logger.info(f"[SOCIAL FB] Saved connected page {request.name} to database")
            except Exception as db_error:
                logger.warning(f"[SOCIAL FB] Could not save connected page to database: {db_error}")
                # Don't fail the request if database save fails

            return {
                "success": True,
                "data": data,
                "message": f"Successfully connected {request.name}"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Facebook page: {e}")
        raise HTTPException(status_code=500, detail=str(e))
