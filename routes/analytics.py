"""
PostHog Analytics API Routes
Securely fetches analytics data from PostHog API
"""

import os
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/admin/analytics", tags=["analytics"])

# PostHog configuration
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_PROJECT_ID = os.getenv("POSTHOG_PROJECT_ID", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://app.posthog.com")


class AnalyticsResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


async def verify_admin(authorization: str) -> bool:
    """Verify the user is an admin via Supabase"""
    # This should be implemented based on your auth system
    # For now, we'll check if authorization header exists
    return bool(authorization)


async def posthog_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make authenticated request to PostHog API"""
    if not POSTHOG_API_KEY:
        raise HTTPException(status_code=500, detail="PostHog API key not configured")
    
    headers = {
        "Authorization": f"Bearer {POSTHOG_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
        else:
            response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"PostHog API error: {response.text}"
            )
        
        return response.json()


@router.get("/config")
async def get_analytics_config():
    """Check if PostHog is configured"""
    return {
        "configured": bool(POSTHOG_API_KEY and POSTHOG_PROJECT_ID),
        "host": POSTHOG_HOST if POSTHOG_API_KEY else None
    }


@router.get("/overview")
async def get_analytics_overview(
    authorization: Optional[str] = Header(None)
):
    """Get overview analytics using PostHog Insights API"""
    if not POSTHOG_API_KEY or not POSTHOG_PROJECT_ID:
        return {
            "success": False,
            "error": "PostHog not configured",
            "data": {}
        }
    
    try:
        now = datetime.utcnow()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {POSTHOG_API_KEY}",
                "Content-Type": "application/json"
            }
            base_url = f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}"
            
            # Get saved insights with their results
            insights_response = await client.get(
                f"{base_url}/insights/",
                headers=headers,
                params={"limit": 50, "saved": "true"}
            )
            
            insights_data = []
            total_insights = 0
            
            if insights_response.status_code == 200:
                insights_list = insights_response.json()
                total_insights = insights_list.get("count", 0)
                results = insights_list.get("results", [])
                
                for insight in results:
                    insight_info = {
                        "id": insight.get("id"),
                        "short_id": insight.get("short_id"),
                        "name": insight.get("name") or insight.get("derived_name") or "Unnamed Insight",
                        "description": insight.get("description", ""),
                        "insight_type": insight.get("filters", {}).get("insight", "TRENDS"),
                        "last_refresh": insight.get("last_refresh"),
                        "created_at": insight.get("created_at"),
                    }
                    
                    # Extract result data if available
                    result = insight.get("result")
                    if result and isinstance(result, list) and len(result) > 0:
                        first_result = result[0]
                        if isinstance(first_result, dict):
                            insight_info["aggregated_value"] = first_result.get("aggregated_value")
                            insight_info["count"] = first_result.get("count")
                            data = first_result.get("data", [])
                            labels = first_result.get("labels", [])
                            if data:
                                insight_info["latest_value"] = data[-1] if data else 0
                                insight_info["data_points"] = len(data)
                                insight_info["trend_data"] = data[-7:] if len(data) > 7 else data
                                insight_info["trend_labels"] = labels[-7:] if len(labels) > 7 else labels
                    
                    insights_data.append(insight_info)
            
            # Get event definitions for additional context
            events_response = await client.get(
                f"{base_url}/event_definitions/",
                headers=headers,
                params={"limit": 10}
            )
            
            event_count = 0
            top_events = []
            if events_response.status_code == 200:
                events_data = events_response.json()
                event_count = events_data.get("count", 0)
                for event in events_data.get("results", [])[:5]:
                    top_events.append({
                        "name": event.get("name"),
                        "volume_30_day": event.get("volume_30_day"),
                        "query_usage_30_day": event.get("query_usage_30_day")
                    })
            
            return {
                "success": True,
                "data": {
                    "total_insights": total_insights,
                    "insights": insights_data[:10],  # Return top 10 insights
                    "event_count": event_count,
                    "top_events": top_events,
                    "last_updated": now.isoformat()
                }
            }
        
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "PostHog API timeout",
            "data": {}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }


@router.get("/events")
async def get_top_events(
    days: int = 7,
    limit: int = 10,
    authorization: Optional[str] = Header(None)
):
    """Get top events by count"""
    if not POSTHOG_API_KEY or not POSTHOG_PROJECT_ID:
        return {
            "success": False,
            "error": "PostHog not configured",
            "data": {}
        }
    
    try:
        now = datetime.utcnow()
        date_from = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {POSTHOG_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get event definitions
            response = await client.get(
                f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/event_definitions/",
                headers=headers,
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                events_data = response.json()
                return {
                    "success": True,
                    "data": {
                        "events": events_data.get("results", []),
                        "date_range": {"from": date_from, "to": date_to}
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"PostHog API error: {response.status_code}",
                    "data": {}
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }


@router.get("/retention")
async def get_retention_data(
    authorization: Optional[str] = Header(None)
):
    """Get user retention data"""
    if not POSTHOG_API_KEY or not POSTHOG_PROJECT_ID:
        return {
            "success": False,
            "error": "PostHog not configured", 
            "data": {}
        }
    
    try:
        now = datetime.utcnow()
        date_from = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")
        
        retention_query = {
            "insight": "RETENTION",
            "target_entity": {"id": "$pageview", "type": "events"},
            "returning_entity": {"id": "$pageview", "type": "events"},
            "date_from": date_from,
            "date_to": date_to,
            "retention_type": "retention_first_time",
            "period": "Day"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {POSTHOG_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/insights/retention/",
                headers=headers,
                json=retention_query
            )
            
            if response.status_code == 200:
                retention_data = response.json()
                return {
                    "success": True,
                    "data": retention_data.get("result", [])
                }
            else:
                return {
                    "success": False,
                    "error": f"PostHog API error: {response.status_code}",
                    "data": {}
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }
