# n8n_integration.py
import os
import json
import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Base URL for n8n webhook
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', '')

async def send_to_n8n(
    agent: str,
    message: str,
    session_id: str,
    request_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Send a message to n8n workflow"""
    if not N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL not configured")
        return {"success": False, "error": "N8N webhook URL not configured"}
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "agent": agent,
                "message": message,
                "sessionId": session_id,
                "timestamp": datetime.now().isoformat(),
                "requestId": request_id
            }
            
            if additional_data:
                payload.update(additional_data)
                
            async with session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error from n8n: {response.status} - {error_text}")
                    return {
                        "success": False, 
                        "status": response.status,
                        "error": error_text
                    }
                
                data = await response.json()
                return {"success": True, "data": data}
                
    except Exception as e:
        logger.error(f"Error sending to n8n: {str(e)}")
        return {"success": False, "error": str(e)}