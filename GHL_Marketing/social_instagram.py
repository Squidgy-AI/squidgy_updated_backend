"""
Social Media - Instagram API Routes
Handles Instagram OAuth, accounts fetching, and account connections for social media posting
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social/instagram", tags=["social_instagram"])

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


class GetAccountsRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"
    oauth_id: str


class ConnectAccountRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"
    oauth_id: str
    origin_id: str
    name: str
    avatar: Optional[str] = None


async def get_ghl_tokens(firm_user_id: str, agent_id: str = "SOL"):
    """
    Fetch GHL location_id, Firebase Token, and Access Token from database
    """
    try:
        # Get location_id and Firebase Token from ghl_subaccounts
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('ghl_location_id, "Firebase Token", "PIT_Token", soma_ghl_user_id')\
            .eq('firm_user_id', firm_user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not ghl_result.data:
            return None

        # Get access_token from facebook_integrations (fallback to PIT_Token if not available)
        access_token = None
        try:
            fb_result = supabase.table('facebook_integrations')\
                .select('access_token')\
                .eq('firm_user_id', firm_user_id)\
                .single()\
                .execute()

            if fb_result.data and fb_result.data.get('access_token'):
                access_token = fb_result.data.get('access_token')
        except Exception as fb_error:
            # Facebook integration doesn't exist, will use PIT_Token fallback
            logger.info(f"No facebook_integrations record found for {firm_user_id}, using PIT_Token")

        # Fallback to PIT_Token if no access_token from facebook_integrations
        if not access_token:
            access_token = ghl_result.data.get('PIT_Token')

        return {
            'location_id': ghl_result.data.get('ghl_location_id'),
            'firebase_token': ghl_result.data.get('Firebase Token'),
            'access_token': access_token,
            'ghl_user_id': ghl_result.data.get('soma_ghl_user_id')
        }
    except Exception as e:
        logger.error(f"Error fetching GHL tokens: {e}")
        return None


@router.post("/start-oauth")
async def start_instagram_oauth(request: StartOAuthRequest):
    """
    Generate Instagram OAuth URL for social media posting

    Args:
        request: StartOAuthRequest with firm_user_id and agent_id

    Returns:
        OAuth URL to open in popup window
    """
    try:
        # Get GHL credentials
        tokens = await get_ghl_tokens(request.firm_user_id, request.agent_id)

        if not tokens or not tokens.get('location_id') or not tokens.get('ghl_user_id'):
            raise HTTPException(
                status_code=404,
                detail="GHL account not found or missing required data"
            )

        location_id = tokens['location_id']
        ghl_user_id = tokens['ghl_user_id']

        # Construct OAuth URL with loginType=instagram parameter
        oauth_url = f"https://backend.leadconnectorhq.com/social-media-posting/oauth/instagram/start?locationId={location_id}&userId={ghl_user_id}&loginType=instagram"

        return {
            "success": True,
            "oauth_url": oauth_url,
            "location_id": location_id,
            "user_id": ghl_user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Instagram OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connected-accounts")
async def get_connected_instagram_accounts(request: StartOAuthRequest):
    """
    Get all connected Instagram accounts from GHL

    Args:
        request: StartOAuthRequest with firm_user_id and agent_id

    Returns:
        List of connected Instagram accounts with their OAuth IDs
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
        access_token = tokens['access_token']

        if not location_id or not firebase_token or not access_token:
            raise HTTPException(
                status_code=400,
                detail="Missing required tokens"
            )

        # Call GHL API to get all accounts
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://backend.leadconnectorhq.com/social-media-posting/{location_id}/accounts",
                params={"fetchAll": "true"},
                headers={
                    "authorization": f"Bearer {access_token}",
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

            # Filter for Instagram accounts only
            instagram_accounts = []
            if data.get('success') and data.get('results', {}).get('accounts'):
                instagram_accounts = [
                    acc for acc in data['results']['accounts']
                    if acc.get('platform') == 'instagram'
                ]

            return {
                "success": True,
                "accounts": instagram_accounts,
                "total_count": len(instagram_accounts)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching connected Instagram accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/available-accounts")
async def get_available_instagram_accounts(request: GetAccountsRequest):
    """
    Get available Instagram accounts for a specific OAuth ID

    Args:
        request: GetAccountsRequest with firm_user_id, agent_id, and oauth_id

    Returns:
        List of available Instagram accounts that can be connected
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
        access_token = tokens['access_token']

        if not location_id or not firebase_token or not access_token:
            raise HTTPException(
                status_code=400,
                detail="Missing required tokens"
            )

        # Call GHL API to get available accounts
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://backend.leadconnectorhq.com/social-media-posting/oauth/{location_id}/instagram/accounts/{request.oauth_id}",
                headers={
                    "authorization": f"Bearer {access_token}",
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

            accounts = []
            if data.get('success') and data.get('results', {}).get('accounts'):
                accounts = data['results']['accounts']

            return {
                "success": True,
                "accounts": accounts,
                "total_count": len(accounts),
                "oauth_id": request.oauth_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching available Instagram accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect-account")
async def connect_instagram_account(request: ConnectAccountRequest):
    """
    Connect a specific Instagram account for social media posting

    Args:
        request: ConnectAccountRequest with firm_user_id, agent_id, oauth_id, and account details

    Returns:
        Success response with connected account details
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
        access_token = tokens['access_token']

        if not location_id or not firebase_token or not access_token:
            raise HTTPException(
                status_code=400,
                detail="Missing required tokens"
            )

        # Prepare request body
        connect_body = {
            "originId": request.origin_id,
            "name": request.name,
            "avatar": request.avatar or ""
        }

        # Call GHL API to connect the account
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://backend.leadconnectorhq.com/social-media-posting/oauth/{location_id}/instagram/accounts/{request.oauth_id}",
                json=connect_body,
                headers={
                    "authorization": f"Bearer {access_token}",
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

            return {
                "success": True,
                "data": data,
                "message": f"Successfully connected {request.name}"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Instagram account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
