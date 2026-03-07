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
from supabase.lib.client_options import SyncClientOptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templated", tags=["templated"])

# Templated.io API configuration
TEMPLATED_API_KEY = os.getenv('TEMPLATED_API_KEY')
TEMPLATED_API_URL = "https://api.templated.io/v1"

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
SUPABASE_SCHEMA = os.getenv('SUPABASE_SCHEMA', 'public')

def get_supabase_client() -> Client:
    """Create and return a Supabase client"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=500, detail="Supabase configuration missing")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=SyncClientOptions(schema=SUPABASE_SCHEMA))

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
    """
    Process a single template and check if user's tag is present.

    isEnabled = True when user's ID is in the template's tags (activated)
    isEnabled = False when template only has "showeveryone" tag (available but not activated)
    """
    tags = template.get("tags", [])
    is_enabled = user_id in tags if user_id else False
    has_showeveryone = "showeveryone" in tags

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
        "isEnabled": is_enabled,  # True only if user's ID is in tags
        "isAvailable": has_showeveryone,  # True if has "showeveryone" tag
        "tags": tags  # Include for debugging
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
    Get templates that are visible to this user.
    Templates are visible if they have:
    - "showeveryone" tag (available for all users to activate)
    - user's business ID as a tag (already activated for this user)

    Templates are marked as "enabled" (activated) only if user's ID is in tags.
    """
    try:
        headers = get_templated_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TEMPLATED_API_URL}/templates",
                headers=headers,
                params={"includeLayers": "true", "limit": "200"},
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Templated.io API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Templated.io API error: {response.text}"
                )

            data = response.json()
            template_list = data if isinstance(data, list) else data.get("response", data.get("data", data.get("templates", [])))

            logger.info(f"Fetched {len(template_list)} total templates from Templated.io")

            # Filter templates: show if has "showeveryone" tag OR user's business ID tag
            filtered_templates = []
            showeveryone_count = 0
            user_specific_count = 0

            for t in template_list:
                tags = t.get("tags", [])
                has_showeveryone = "showeveryone" in tags
                has_user_tag = user_id in tags

                if has_showeveryone or has_user_tag:
                    filtered_templates.append(t)
                    if has_showeveryone:
                        showeveryone_count += 1
                    if has_user_tag:
                        user_specific_count += 1

            logger.info(f"Filtered to {len(filtered_templates)} templates for user {user_id}")
            logger.info(f"  - {showeveryone_count} with 'showeveryone' tag")
            logger.info(f"  - {user_specific_count} with user's ID tag")
            
            # Group templates by prefix (text before '-' in name)
            groups = {}
            for t in filtered_templates:
                name = t.get("name", "")
                if "-" in name:
                    prefix = name.split("-")[0].strip()
                else:
                    prefix = name
                
                if prefix not in groups:
                    groups[prefix] = []
                groups[prefix].append(t)
            
            # Build grouped response
            grouped_templates = []
            for prefix, group_items in groups.items():
                # Process all templates in the group (without groupTemplates to avoid recursion)
                processed_items = []
                for t in group_items:
                    item = process_template(t, user_id)
                    # Remove any nested group fields to prevent recursion
                    item.pop("groupTemplates", None)
                    item.pop("groupName", None)
                    item.pop("groupCount", None)
                    processed_items.append(item)
                
                # Find square template to use as representative (prefer "Square" in name)
                representative = processed_items[0]  # Default to first
                for item in processed_items:
                    item_name = item.get("name", "").lower()
                    if "square" in item_name:
                        representative = item
                        break
                
                main_template = dict(representative)  # Create a copy
                main_template["groupName"] = prefix
                main_template["groupTemplates"] = processed_items
                main_template["groupCount"] = len(processed_items)
                
                grouped_templates.append(main_template)
            
            # Calculate statistics
            enabled_count = sum(1 for g in grouped_templates if g["isEnabled"])
            available_count = sum(1 for g in grouped_templates if g.get("isAvailable", False))

            logger.info(f"Returning {len(grouped_templates)} template groups")
            logger.info(f"  - {enabled_count} groups enabled (activated by user)")
            logger.info(f"  - {available_count} groups available (have 'showeveryone' tag)")

            return {
                "success": True,
                "templates": grouped_templates,
                "total": len(grouped_templates),
                "enabledCount": enabled_count,
                "availableCount": available_count,
                "userId": user_id,
                "debug": {
                    "totalFetched": len(template_list),
                    "afterFilter": len(filtered_templates),
                    "showeveryoneTemplates": showeveryone_count,
                    "userSpecificTemplates": user_specific_count
                }
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
    Enable or disable a template for a user by adding/removing their user_id tag.

    Uses Templated.io's dedicated add-tags (POST) and remove-tags (DELETE) endpoints
    for efficient tag management without replacing all tags.

    ALSO stores in Supabase business_settings.enabled_templates for our records.
    """
    try:
        headers = get_templated_headers()
        template_id = request.template_id
        user_id = request.user_id
        enable = request.enable

        async with httpx.AsyncClient() as client:
            if enable:
                # Add user_id tag using POST /template/{id}/tags
                response = await client.post(
                    f"{TEMPLATED_API_URL}/template/{template_id}/tags",
                    headers=headers,
                    json=[user_id],  # Array of tags to add
                    timeout=30.0
                )
            else:
                # Remove user_id tag using DELETE /template/{id}/tags
                response = await client.delete(
                    f"{TEMPLATED_API_URL}/template/{template_id}/tags",
                    headers=headers,
                    json=[user_id],  # Array of tags to remove
                    timeout=30.0
                )

            if response.status_code != 200:
                logger.error(f"Tag operation failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to {'add' if enable else 'remove'} tag: {response.text}"
                )

            # Get updated template to return current tags
            get_response = await client.get(
                f"{TEMPLATED_API_URL}/template/{template_id}",
                headers=headers,
                timeout=30.0
            )

            updated_tags = []
            if get_response.status_code == 200:
                template_data = get_response.json()
                updated_tags = template_data.get("tags", [])

            action = "enabled" if enable else "disabled"
            logger.info(f"Template {template_id} {action} for user {user_id}")

            # ALSO store in Supabase for our records (non-critical)
            try:
                supabase = get_supabase_client()

                # Get current enabled_templates array
                current = supabase.from_('business_settings').select('enabled_templates').eq('id', user_id).single().execute()

                if current.data:
                    current_templates = current.data.get('enabled_templates') or []

                    if enable:
                        # Add template_id if not already in array
                        if template_id not in current_templates:
                            updated_templates = current_templates + [template_id]
                            supabase.from_('business_settings').update({
                                'enabled_templates': updated_templates
                            }).eq('id', user_id).execute()
                            logger.info(f"📝 Stored enabled template in Supabase")
                    else:
                        # Remove template_id from array
                        if template_id in current_templates:
                            updated_templates = [t for t in current_templates if t != template_id]
                            supabase.from_('business_settings').update({
                                'enabled_templates': updated_templates
                            }).eq('id', user_id).execute()
                            logger.info(f"📝 Removed template from Supabase")

            except Exception as supabase_error:
                # Non-critical - just log the error
                logger.warning(f"⚠️ Failed to update Supabase (non-critical): {supabase_error}")

            return {
                "success": True,
                "message": f"Template {action} for user",
                "template_id": template_id,
                "tags": updated_tags,
                "isEnabled": enable
            }

    except httpx.RequestError as e:
        logger.error(f"Request error toggling template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error toggling template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/debug/all")
async def debug_all_templates():
    """
    Debug endpoint to see ALL templates with their tags.
    Use this to verify which templates have "showeveryone" tag.
    """
    try:
        headers = get_templated_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TEMPLATED_API_URL}/templates",
                headers=headers,
                params={"includeLayers": "false", "limit": "200"},
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Templated.io API error: {response.text}"
                )

            data = response.json()
            template_list = data if isinstance(data, list) else data.get("response", data.get("data", data.get("templates", [])))

            # Simplify response to show just id, name, and tags
            simplified = []
            showeveryone_templates = []

            for t in template_list:
                tags = t.get("tags", [])
                template_info = {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "tags": tags,
                    "hasShoweveryone": "showeveryone" in tags
                }
                simplified.append(template_info)

                if "showeveryone" in tags:
                    showeveryone_templates.append(template_info)

            return {
                "success": True,
                "totalTemplates": len(template_list),
                "templatesWithShoweveryone": len(showeveryone_templates),
                "showeveryoneTemplates": showeveryone_templates,
                "allTemplates": simplified
            }

    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
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
