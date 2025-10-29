# Website/web_scrape.py - FINAL VERSION
import os
import asyncio
import aiohttp
from supabase import create_client, Client
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import time
import traceback
import tempfile
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import threading
from datetime import datetime

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Create a thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=3)

# Create a lock for browser instances to prevent concurrent usage
browser_lock = threading.Lock()

async def capture_website_screenshot(url: str, session_id: str = None) -> dict:
    """
    Captures a screenshot of the entire website using Playwright.
    Optimized for Heroku environment.
    """
    browser = None
    tmp_path = None
    
    try:
        # Use session_id in filename if provided
        if session_id:
            filename = f"{session_id}_screenshot.jpg"
        else:
            filename = f"screenshot_{int(time.time())}.jpg"
        
        print(f"Attempting to capture screenshot for URL: {url}")
        
        async with async_playwright() as p:
            # Launch browser with optimized settings for Heroku
            browser_args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-background-networking",
                "--disable-client-side-phishing-detection",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-sync",
                "--disable-translate",
                "--hide-scrollbars",
                "--metrics-recording-only",
                "--mute-audio",
                "--no-default-browser-check",
                "--safebrowsing-disable-auto-update",
                "--disable-features=VizDisplayCompositor"
            ]
            
            # Launch browser - Playwright buildpack should handle everything
            print("Launching Playwright browser...")
            browser = await p.chromium.launch(
                headless=True,
                args=browser_args
            )
            
            # Create page
            page = await browser.new_page()
            
            # Set viewport size
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            print(f"Navigating to URL: {url}")
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"Page load timeout/error, continuing anyway: {e}")
            
            # Wait for page to stabilize
            await page.wait_for_timeout(3000)
            
            # Take screenshot
            print("Taking screenshot...")
            screenshot_bytes = await page.screenshot(
                type="jpeg",
                quality=80,
                full_page=True
            )
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(screenshot_bytes)
            
            file_content = screenshot_bytes
            
            storage_path = f"screenshots/{filename}"
            
            # Remove existing file if present
            try:
                supabase.storage.from_('static').remove([storage_path])
            except:
                pass
            
            response = supabase.storage.from_('static').upload(
                storage_path,
                file_content,
                {
                    "content-type": "image/jpeg",
                    "upsert": "true"
                }
            )
            
            # Handle the response
            if hasattr(response, 'error') and response.error:
                if "already exists" in str(response.error):
                    public_url = supabase.storage.from_('static').get_public_url(storage_path)
                    return {
                        "status": "success",
                        "message": "Screenshot captured successfully",
                        "path": storage_path,
                        "public_url": public_url,
                        "filename": filename
                    }
                else:
                    raise Exception(f"Failed to upload: {response.error}")
            else:
                public_url = supabase.storage.from_('static').get_public_url(storage_path)
                return {
                    "status": "success",
                    "message": "Screenshot captured successfully",
                    "path": storage_path,
                    "public_url": public_url,
                    "filename": filename
                }
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error capturing screenshot: {e}")
        print(f"Traceback: {error_traceback}")
        
        return {
            "status": "error",
            "message": str(e),
            "error_details": error_traceback,
            "path": None
        }
    
    finally:
        # Cleanup
        if browser:
            try:
                await browser.close()
            except Exception as e:
                print(f"Error closing browser: {e}")
        
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Error removing temp file: {e}")

def capture_website_screenshot_sync(url: str, session_id: str = None) -> dict:
    """Sync wrapper for capturing website screenshot"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(capture_website_screenshot(url, session_id))
    finally:
        loop.close()

def get_website_favicon(url: str, session_id: str = None) -> dict:
    """
    Gets the favicon from a website and saves it to Supabase Storage.
    Synchronous version for backward compatibility.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_website_favicon_async(url, session_id))
    finally:
        loop.close()

async def get_website_favicon_async(url: str, session_id: str = None) -> dict:
    """
    Async function to get website favicon
    """
    print(f"Getting favicon for URL: {url}, session_id: {session_id}")
    
    try:
        # Create filename
        if session_id:
            filename = f"{session_id}_logo.jpg"
        else:
            filename = f"logo_{int(time.time())}.jpg"
        
        # Use aiohttp for async HTTP requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # NO TIMEOUT - let it take as long as needed
        timeout = aiohttp.ClientTimeout(total=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Get the website HTML
            async with session.get(url, headers=headers) as response:
                html_text = await response.text()
                
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Look for favicon
            favicon_url = None
            for link in soup.find_all('link'):
                rel = link.get('rel', [])
                if isinstance(rel, list):
                    rel = ' '.join(rel).lower()
                else:
                    rel = rel.lower()
                    
                if 'icon' in rel or 'shortcut icon' in rel or 'apple-touch-icon' in rel:
                    favicon_url = link.get('href')
                    print(f"Found favicon link: {favicon_url}")
                    break
            
            # Default favicon location
            if not favicon_url:
                favicon_url = f"{url}/favicon.ico"
                print(f"No favicon link found, trying default: {favicon_url}")
            
            # Fix relative URLs
            if favicon_url and not favicon_url.startswith('http'):
                if favicon_url.startswith('//'):
                    favicon_url = 'https:' + favicon_url
                elif favicon_url.startswith('/'):
                    base_url = '/'.join(url.split('/')[0:3])
                    favicon_url = base_url + favicon_url
                else:
                    base_url = '/'.join(url.split('/')[0:3])
                    favicon_url = f"{base_url}/{favicon_url}"
            
            # Download favicon
            if favicon_url:
                try:
                    async with session.get(favicon_url, headers=headers) as favicon_response:
                        if favicon_response.status == 200:
                            favicon_content = await favicon_response.read()
                            
                            # Convert to JPG using PIL
                            img = Image.open(BytesIO(favicon_content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Save to temporary file
                            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                                tmp_path = tmp_file.name
                                img.save(tmp_path, 'JPEG')
                            
                            # Upload to Supabase
                            with open(tmp_path, 'rb') as f:
                                file_content = f.read()
                            
                            storage_path = f"favicons/{filename}"
                            
                            # Remove existing file if present
                            try:
                                supabase.storage.from_('static').remove([storage_path])
                            except:
                                pass
                            
                            response = supabase.storage.from_('static').upload(
                                storage_path,
                                file_content,
                                {
                                    "content-type": "image/jpeg",
                                    "upsert": "true"
                                }
                            )
                            
                            # Clean up
                            os.unlink(tmp_path)
                            
                            # Handle the response properly
                            if hasattr(response, 'error') and response.error:
                                # Check if it's just a duplicate file error
                                if "already exists" in str(response.error):
                                    public_url = supabase.storage.from_('static').get_public_url(storage_path)
                                    return {
                                        "status": "success",
                                        "message": "Favicon captured successfully",
                                        "path": storage_path,
                                        "public_url": public_url,
                                        "filename": filename
                                    }
                                else:
                                    return {
                                        "status": "error",
                                        "message": f"Upload error: {response.error}",
                                        "path": None
                                    }
                            else:
                                # Success case
                                public_url = supabase.storage.from_('static').get_public_url(storage_path)
                                return {
                                    "status": "success",
                                    "message": "Favicon captured successfully",
                                    "path": storage_path,
                                    "public_url": public_url,
                                    "filename": filename
                                }
                except Exception as e:
                    print(f"Error downloading favicon: {e}")
                    
        return {
            "status": "error",
            "message": "No favicon found",
            "path": None
        }
        
    except Exception as e:
        print(f"Error fetching favicon: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "path": None
        }