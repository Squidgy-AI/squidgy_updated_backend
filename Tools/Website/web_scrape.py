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

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create a thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=3)

# Create a lock for browser instances to prevent concurrent usage
browser_lock = threading.Lock()

async def capture_website_screenshot(url: str, session_id: str = None) -> dict:
    """
    Captures a screenshot of the entire website using Playwright.
    Enhanced with bot detection avoidance for big websites.
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
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        async with async_playwright() as p:
            # Enhanced browser args to avoid bot detection
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
                "--disable-features=VizDisplayCompositor",
                # Anti-detection measures
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--accept-lang=en-US,en;q=0.9",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ]
            
            # Check if we're on Heroku and use buildpack-installed chromium
            executable_path = None
            if os.environ.get('DYNO'):
                executable_path = '/app/.apt/usr/bin/chromium-browser'
            
            browser = await p.chromium.launch(
                headless=True,
                args=browser_args,
                executable_path=executable_path
            )
            
            # Create page with stealth settings
            page = await browser.new_page()
            
            # Set realistic viewport size
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Set extra headers to mimic real browser
            await page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Override navigator.webdriver to avoid detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Remove automation indicators
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Override Chrome runtime
                window.chrome = {
                    runtime: {},
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            print(f"Navigating to URL: {url}")
            
            # Try multiple strategies for navigation
            page_loaded = False
            
            # Strategy 1: Normal navigation with longer timeout
            try:
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page_loaded = True
                print("✅ Page loaded successfully with domcontentloaded")
            except Exception as e:
                print(f"Strategy 1 failed: {e}")
            
            # Strategy 2: Try with networkidle if domcontentloaded failed
            if not page_loaded:
                try:
                    await page.goto(url, timeout=60000, wait_until="networkidle")
                    page_loaded = True
                    print("✅ Page loaded successfully with networkidle")
                except Exception as e:
                    print(f"Strategy 2 failed: {e}")
                    
            # Strategy 3: Just load and continue even if errors
            if not page_loaded:
                try:
                    await page.goto(url, timeout=30000)
                    print("⚠️ Page loaded with potential errors, continuing...")
                    page_loaded = True
                except Exception as e:
                    print(f"Strategy 3 failed: {e}")
                    
            if not page_loaded:
                raise Exception("Failed to load page with all strategies")
            
            # Wait for page to stabilize and handle any popups/overlays
            await page.wait_for_timeout(5000)
            
            # Try to dismiss common overlays/popups
            try:
                # Common cookie/privacy notice selectors
                cookie_selectors = [
                    '[id*="cookie"] button',
                    '[class*="cookie"] button',
                    '[id*="privacy"] button',
                    '[class*="privacy"] button',
                    'button:has-text("Accept")',
                    'button:has-text("Agree")',
                    'button:has-text("Continue")',
                    'button:has-text("OK")',
                    '[aria-label*="close"]',
                    '[aria-label*="dismiss"]'
                ]
                
                for selector in cookie_selectors:
                    try:
                        elements = await page.locator(selector).all()
                        for element in elements[:2]:  # Only click first 2 matches
                            if await element.is_visible():
                                await element.click(timeout=2000)
                                await page.wait_for_timeout(1000)
                                break
                    except:
                        continue
                        
            except Exception as e:
                print(f"Warning: Could not dismiss overlays: {e}")
            
            # Additional wait for dynamic content
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
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Enhanced headers to mimic real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
        
        # Set reasonable timeout and handle compression
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300, use_dns_cache=True)
        
        # Remove problematic headers that might trigger encoding issues
        safe_headers = headers.copy()
        safe_headers.pop('Accept-Encoding', None)  # Let aiohttp handle compression
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Get the website HTML with retry logic
            html_text = None
            for attempt in range(3):
                try:
                    print(f"Attempt {attempt + 1}: Fetching HTML from {url}")
                    async with session.get(url, headers=safe_headers, ssl=False, allow_redirects=True) as response:
                        if response.status == 200:
                            html_text = await response.text()
                            print(f"✅ Successfully fetched HTML (status: {response.status})")
                            break
                        elif response.status == 403:
                            print(f"⚠️ HTTP {response.status} (Access denied), trying with minimal headers...")
                            # Try with just user agent
                            minimal_headers = {'User-Agent': safe_headers['User-Agent']}
                            async with session.get(url, headers=minimal_headers, ssl=False) as retry_response:
                                if retry_response.status == 200:
                                    html_text = await retry_response.text()
                                    print(f"✅ Success with minimal headers (status: {retry_response.status})")
                                    break
                        else:
                            print(f"⚠️ HTTP {response.status} received, retrying...")
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        await asyncio.sleep(2)
                    
            if not html_text:
                raise Exception("Failed to fetch HTML after 3 attempts")
                
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
            
            # Download favicon with retry logic
            if favicon_url:
                favicon_downloaded = False
                for attempt in range(3):
                    try:
                        print(f"Attempt {attempt + 1}: Downloading favicon from {favicon_url}")
                        # Add specific headers for image requests
                        img_headers = headers.copy()
                        img_headers.update({
                            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                            'Sec-Fetch-Dest': 'image',
                            'Sec-Fetch-Mode': 'no-cors',
                            'Referer': url
                        })
                        
                        async with session.get(favicon_url, headers=img_headers, ssl=False, allow_redirects=True) as favicon_response:
                            if favicon_response.status == 200:
                                favicon_content = await favicon_response.read()
                                print(f"✅ Successfully downloaded favicon ({len(favicon_content)} bytes)")
                                favicon_downloaded = True
                                break
                            elif favicon_response.status == 403:
                                print(f"⚠️ Favicon HTTP {favicon_response.status} (Access denied), trying with minimal headers...")
                                # Try with minimal headers
                                minimal_img_headers = {'User-Agent': img_headers['User-Agent']}
                                async with session.get(favicon_url, headers=minimal_img_headers, ssl=False) as retry_favicon:
                                    if retry_favicon.status == 200:
                                        favicon_content = await retry_favicon.read()
                                        print(f"✅ Favicon success with minimal headers ({len(favicon_content)} bytes)")
                                        favicon_downloaded = True
                                        break
                            else:
                                print(f"⚠️ Favicon HTTP {favicon_response.status}, retrying...")
                    except Exception as e:
                        print(f"Favicon download attempt {attempt + 1} failed: {e}")
                        if attempt < 2:
                            await asyncio.sleep(1)
                            
                if not favicon_downloaded:
                    print("❌ Failed to download favicon after 3 attempts")
                    return {
                        "status": "error",
                        "message": "Failed to download favicon",
                        "path": None
                    }
                
                # Convert to JPG using PIL
                try:
                    img = Image.open(BytesIO(favicon_content))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        img.save(tmp_path, 'JPEG', quality=85, optimize=True)
                    
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
                    print(f"Error processing favicon image: {e}")
                    return {
                        "status": "error",
                        "message": f"Image processing error: {e}",
                        "path": None
                    }
                    
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