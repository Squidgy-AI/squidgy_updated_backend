"""
Templated.io API Routes
Handles fetching templates and updating template tags for user businesses
"""

import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templated", tags=["templated"])

# Templated.io API configuration
TEMPLATED_API_KEY = os.getenv('TEMPLATED_API_KEY')
TEMPLATED_API_URL = "https://api.templated.io/v1"

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

class TemplateLayer(BaseModel):
    name: str
    type: str
    description: Optional[str] = ""
    text: Optional[str] = None
    fontFamily: Optional[str] = None
    color: Optional[str] = None
    imageUrl: Optional[str] = None

class Template(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    preview: Optional[str] = ""
    size: Dict[str, int]
    layers: List[TemplateLayer]
    isEnabled: bool = False

class TemplatesResponse(BaseModel):
    success: bool
    templates: List[Template]
    message: Optional[str] = None

class UpdateTagsRequest(BaseModel):
    template_id: str
    user_id: str
    enable: bool  # True to add user's tag, False to remove

class UpdateTagsResponse(BaseModel):
    success: bool
    message: str
    template_id: str
    tags: List[str]

# ============================================================================
# Helper Functions
# ============================================================================

def get_templated_headers() -> Dict[str, str]:
    """Get headers for Templated.io API requests"""
    if not TEMPLATED_API_KEY:
        raise HTTPException(status_code=500, detail="Templated.io API key not configured")
    return {
        "Authorization": f"Bearer {TEMPLATED_API_KEY}",
        "Content-Type": "application/json"
    }

def process_template_layers(layers: List[Dict]) -> List[Dict]:
    """Process layers and extract type-specific fields only"""
    processed = []
    for layer in layers:
        base = {
            "name": layer.get("layer", ""),
            "type": layer.get("type", ""),
            "description": layer.get("description", "")
        }
        
        layer_type = layer.get("type", "")
        if layer_type == "text":
            base["text"] = layer.get("text", "")
            base["fontFamily"] = layer.get("font_family")
            base["color"] = layer.get("color")
        elif layer_type == "image":
            base["imageUrl"] = layer.get("image_url")
        elif layer_type == "shape":
            base["color"] = layer.get("color")
        
        processed.append(base)
    return processed

def process_template(template: Dict, user_id: str = None) -> Dict:
    """Process a single template and check if user's tag is present"""
    tags = template.get("tags", [])
    is_enabled = user_id in tags if user_id else False
    
    return {
        "id": template.get("id", ""),
        "name": template.get("name", ""),
        "description": template.get("description", ""),
        "preview": template.get("thumbnail", ""),
        "size": {
            "width": template.get("width", 0),
            "height": template.get("height", 0)
        },
        "layers": process_template_layers(template.get("layers", [])),
        "isEnabled": is_enabled,
        "tags": tags
    }

# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/templates")
async def get_all_templates(user_id: Optional[str] = None, tag: Optional[str] = None):
    """
    Get all templates from Templated.io
    Optionally filter by tag and mark which ones are enabled for the user
    """
    try:
        headers = get_templated_headers()
        
        # Build query params
        params = {
            "includeLayers": "true",
            "limit": "100"
        }
        if tag:
            params["tags"] = tag
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TEMPLATED_API_URL}/templates",
                headers=headers,
                params=params,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Templated.io API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Templated.io API error: {response.text}"
                )
            
            data = response.json()
            
            # Handle different response formats
            template_list = data if isinstance(data, list) else data.get("response", data.get("data", data.get("templates", [])))
            
            # Process templates
            templates = [process_template(t, user_id) for t in template_list]
            
            return {
                "success": True,
                "templates": templates,
                "total": len(templates)
            }
            
    except httpx.RequestError as e:
        logger.error(f"Request error fetching templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch templates: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{user_id}")
async def get_templates_for_user(user_id: str):
    """
    Get all templates and mark which ones are enabled for this user
    (user_id is used as a tag on templates)
    """
    try:
        headers = get_templated_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TEMPLATED_API_URL}/templates",
                headers=headers,
                params={"includeLayers": "true", "limit": "100"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Templated.io API error: {response.text}"
                )
            
            data = response.json()
            template_list = data if isinstance(data, list) else data.get("response", data.get("data", data.get("templates", [])))
            
            templates = [process_template(t, user_id) for t in template_list]
            
            enabled_count = sum(1 for t in templates if t["isEnabled"])
            
            return {
                "success": True,
                "templates": templates,
                "total": len(templates),
                "enabledCount": enabled_count,
                "userId": user_id
            }
            
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/toggle")
async def toggle_template_for_user(request: UpdateTagsRequest):
    """
    Enable or disable a template for a user by adding/removing their user_id tag
    """
    try:
        headers = get_templated_headers()
        template_id = request.template_id
        user_id = request.user_id
        enable = request.enable
        
        async with httpx.AsyncClient() as client:
            # First, get current template to see existing tags
            get_response = await client.get(
                f"{TEMPLATED_API_URL}/template/{template_id}",
                headers=headers,
                timeout=30.0
            )
            
            if get_response.status_code != 200:
                raise HTTPException(
                    status_code=get_response.status_code,
                    detail=f"Failed to get template: {get_response.text}"
                )
            
            template_data = get_response.json()
            current_tags = template_data.get("tags", [])
            
            # Modify tags based on enable/disable
            if enable:
                if user_id not in current_tags:
                    current_tags.append(user_id)
            else:
                if user_id in current_tags:
                    current_tags.remove(user_id)
            
            # Update tags on Templated.io
            update_response = await client.put(
                f"{TEMPLATED_API_URL}/template/{template_id}/tags",
                headers=headers,
                json=current_tags,
                timeout=30.0
            )
            
            if update_response.status_code != 200:
                raise HTTPException(
                    status_code=update_response.status_code,
                    detail=f"Failed to update tags: {update_response.text}"
                )
            
            action = "enabled" if enable else "disabled"
            return {
                "success": True,
                "message": f"Template {action} for user",
                "template_id": template_id,
                "tags": current_tags,
                "isEnabled": enable
            }
            
    except httpx.RequestError as e:
        logger.error(f"Request error toggling template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error toggling template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/bulk-toggle")
async def bulk_toggle_templates(
    user_id: str = Body(...),
    template_ids: List[str] = Body(...),
    enable: bool = Body(...)
):
    """
    Enable or disable multiple templates for a user at once
    """
    results = []
    errors = []
    
    for template_id in template_ids:
        try:
            request = UpdateTagsRequest(
                template_id=template_id,
                user_id=user_id,
                enable=enable
            )
            result = await toggle_template_for_user(request)
            results.append({"template_id": template_id, "success": True})
        except Exception as e:
            errors.append({"template_id": template_id, "error": str(e)})
    
    return {
        "success": len(errors) == 0,
        "results": results,
        "errors": errors,
        "totalProcessed": len(results),
        "totalErrors": len(errors)
    }
