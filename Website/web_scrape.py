# Website/web_scrape.py - Refactored to use external BackgroundAutomationUser1 service
import os
import asyncio
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import traceback
from datetime import datetime

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# External automation service URL
AUTOMATION_SERVICE_URL = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')

async def capture_website_screenshot(url: str, session_id: str = None) -> dict:
    """
    Captures a screenshot by calling external BackgroundAutomationUser1 service.
    The service handles browser automation and returns the Supabase storage URL.
    """
    try:
        print(f"[SCREENSHOT] 📸 Requesting screenshot for URL: {url}")
        print(f"[SCREENSHOT] 📞 Calling external automation service at: {AUTOMATION_SERVICE_URL}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AUTOMATION_SERVICE_URL}/website/screenshot",
                json={
                    "url": url,
                    "session_id": session_id
                }
            )

            if response.status_code == 200:
                result = response.json()
                print(f"[SCREENSHOT] ✅ Screenshot captured successfully")
                return result
            else:
                error_msg = f"Service returned {response.status_code}: {response.text}"
                print(f"[SCREENSHOT] ❌ Error: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "path": None
                }

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"[SCREENSHOT] ❌ Error: {e}")
        print(f"[SCREENSHOT] Traceback: {error_traceback}")

        return {
            "status": "error",
            "message": str(e),
            "error_details": error_traceback,
            "path": None
        }


async def get_website_favicon_async(url: str, session_id: str = None) -> dict:
    """
    Gets favicon by calling external BackgroundAutomationUser1 service.
    The service handles browser automation and returns the Supabase storage URL.
    """
    try:
        print(f"[FAVICON] 🎨 Requesting favicon for URL: {url}")
        print(f"[FAVICON] 📞 Calling external automation service at: {AUTOMATION_SERVICE_URL}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AUTOMATION_SERVICE_URL}/website/favicon",
                json={
                    "url": url,
                    "session_id": session_id
                }
            )

            if response.status_code == 200:
                result = response.json()
                print(f"[FAVICON] ✅ Favicon captured successfully")
                return result
            else:
                error_msg = f"Service returned {response.status_code}: {response.text}"
                print(f"[FAVICON] ❌ Error: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "path": None
                }

    except Exception as e:
        print(f"[FAVICON] ❌ Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "path": None
        }

