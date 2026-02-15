"""
Social Media - Slack API Routes
Handles Slack OAuth and workspace integrations for team collaboration
"""

import os
import logging
import secrets
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social/slack", tags=["social_slack"])

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# GHL's Slack App Configuration
GHL_SLACK_CLIENT_ID = "394243081714.4376892619942"
GHL_SLACK_REDIRECT_URI = "https://services.leadconnectorhq.com/appengine/slack/oauth-connect"

# Slack OAuth Scopes (matching GHL's configuration)
SLACK_BOT_SCOPES = [
    'channels:manage', 'channels:read', 'channels:join',
    'chat:write', 'chat:write.customize', 'chat:write.public',
    'commands', 'files:write',
    'im:read', 'im:write',
    'mpim:read', 'mpim:write',
    'team:read',
    'users.profile:read', 'users:read', 'users:read.email',
    'workflow.steps:execute'
]

SLACK_USER_SCOPES = [
    'channels:history', 'channels:read', 'channels:write',
    'chat:write', 'emoji:read',
    'files:read', 'files:write',
    'groups:history', 'groups:read', 'groups:write',
    'im:read', 'im:write',
    'mpim:read', 'mpim:write',
    'reactions:read', 'reminders:write',
    'search:read', 'stars:read',
    'team:read',
    'users.profile:write', 'users:read', 'users:read.email'
]


class SlackResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class StartOAuthRequest(BaseModel):
    firm_user_id: str
    agent_id: Optional[str] = "SOL"


async def get_ghl_tokens(firm_user_id: str, agent_id: str = "SOL"):
    """
    Fetch GHL location_id, Firebase Token, and Access Token from ghl_subaccounts table
    """
    try:
        logger.info(f"[SLACK] Fetching GHL tokens for user: {firm_user_id}, agent: {agent_id}")

        # Get all tokens from ghl_subaccounts table
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('ghl_location_id, firebase_token, firebase_token_time, pit_token, soma_ghl_user_id, agency_user_id, access_token')\
            .eq('firm_user_id', firm_user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not ghl_result.data:
            logger.warning(f"[SLACK] No ghl_subaccounts record found for user: {firm_user_id}")
            return None

        logger.info(f"[SLACK] Found GHL location: {ghl_result.data.get('ghl_location_id')}")

        return {
            'location_id': ghl_result.data.get('ghl_location_id'),
            'firebase_token': ghl_result.data.get('firebase_token'),
            'firebase_token_time': ghl_result.data.get('firebase_token_time'),
            'access_token': ghl_result.data.get('access_token') or ghl_result.data.get('pit_token'),
            'soma_ghl_user_id': ghl_result.data.get('soma_ghl_user_id'),
            'agency_user_id': ghl_result.data.get('agency_user_id')
        }
    except Exception as e:
        logger.error(f"[SLACK] Error fetching GHL tokens: {e}")
        return None


@router.post("/start-oauth")
async def start_slack_oauth(request: StartOAuthRequest):
    """
    Generate Slack OAuth URL for workspace integration

    Uses GHL's Slack app infrastructure (similar to Facebook/Instagram pattern)

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

        # Generate random state (matching GHL's pattern: locationId,randomString)
        random_string = secrets.token_urlsafe(16)
        state = f"{location_id},{random_string}"

        # Build Slack OAuth URL (using GHL's Slack app)
        bot_scopes = ','.join(SLACK_BOT_SCOPES)
        user_scopes = ','.join(SLACK_USER_SCOPES)

        oauth_params = {
            'client_id': GHL_SLACK_CLIENT_ID,
            'scope': bot_scopes,
            'user_scope': user_scopes,
            'redirect_uri': GHL_SLACK_REDIRECT_URI,
            'state': state,
            'granular_bot_scope': '1',
            'single_channel': '0'
        }

        # Construct OAuth URL
        from urllib.parse import urlencode
        oauth_url = f"https://slack.com/oauth/v2/authorize?{urlencode(oauth_params)}"

        logger.info(f"[SLACK] Generated OAuth URL for location: {location_id}")

        return {
            "success": True,
            "oauth_url": oauth_url,
            "location_id": location_id,
            "state": state
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SLACK] Error starting Slack OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connected-workspaces")
async def get_connected_slack_workspaces(request: StartOAuthRequest):
    """
    Get all connected Slack workspaces from GHL

    Args:
        request: StartOAuthRequest with firm_user_id and agent_id

    Returns:
        List of connected Slack workspaces
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
        access_token = tokens.get('access_token')

        # Check if firebase_token exists
        if not location_id or not firebase_token:
            raise HTTPException(
                status_code=400,
                detail="Missing firebase_token. Please refresh your GHL connection."
            )

        logger.info(f"[SLACK] Fetching connected workspaces for location: {location_id}")

        # Call GHL API to get Slack integrations
        # Endpoint: https://api.leadconnectorhq.com/slack/{locationId}/integrations
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.leadconnectorhq.com/slack/{location_id}/integrations",
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Authorization": f"Bearer {access_token}" if access_token else "",
                    "token-id": firebase_token,
                    "channel": "APP"
                },
                timeout=30.0
            )

            # Handle 404 - no integrations yet
            if response.status_code == 404:
                logger.info(f"[SLACK] No Slack integrations found for location: {location_id}")
                return {
                    "success": True,
                    "integrations": [],
                    "total_count": 0
                }

            if not response.is_success:
                logger.error(f"[SLACK] GHL API returned {response.status_code}: {response.text}")

                if response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="GHL authentication failed. Your access tokens may be expired."
                    )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"GHL API error: {response.text}"
                    )

            data = response.json()

            # Extract integrations array
            integrations = data.get('integrations', [])

            logger.info(f"[SLACK] Found {len(integrations)} Slack workspace(s)")

            return {
                "success": True,
                "integrations": integrations,
                "total_count": len(integrations)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SLACK] Error fetching connected Slack workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect-workspace")
async def disconnect_slack_workspace(request: dict):
    """
    Disconnect a Slack workspace

    Args:
        request: Dict with firm_user_id, agent_id, and integration_id

    Returns:
        Success status
    """
    try:
        firm_user_id = request.get('firm_user_id')
        agent_id = request.get('agent_id', 'SOL')
        integration_id = request.get('integration_id')

        if not firm_user_id or not integration_id:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: firm_user_id, integration_id"
            )

        # Get GHL credentials
        tokens = await get_ghl_tokens(firm_user_id, agent_id)

        if not tokens:
            raise HTTPException(
                status_code=404,
                detail="GHL account not found"
            )

        location_id = tokens['location_id']
        firebase_token = tokens['firebase_token']
        access_token = tokens.get('access_token')

        if not firebase_token:
            raise HTTPException(
                status_code=400,
                detail="Missing firebase_token"
            )

        logger.info(f"[SLACK] Disconnecting workspace {integration_id} for location: {location_id}")

        # Call GHL API to delete integration
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.leadconnectorhq.com/slack/{location_id}/oauth-delete/{integration_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {access_token}" if access_token else "",
                    "token-id": firebase_token,
                    "channel": "APP"
                },
                timeout=30.0
            )

            if not response.is_success:
                logger.error(f"[SLACK] Delete failed {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to disconnect workspace: {response.text}"
                )

            logger.info(f"[SLACK] Successfully disconnected workspace {integration_id}")

            return {
                "success": True,
                "message": "Workspace disconnected successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SLACK] Error disconnecting workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
