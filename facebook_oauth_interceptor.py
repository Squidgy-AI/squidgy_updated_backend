"""
Facebook OAuth Token Interceptor
Starts a Playwright browser session that intercepts OAuth tokens during the Facebook login flow
"""
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from datetime import datetime
import os

class FacebookOAuthInterceptor:
    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.playwright = None
        self.access_token = None
        self.firebase_token = None
        self.pit_token = None
        self.session_active = False
        
    async def start_session(self, oauth_url: str):
        """Start browser session with token interception"""
        try:
            print(f"[OAUTH INTERCEPTOR] 🚀 Starting browser session...")
            
            # Launch Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser in headless mode (Heroku doesn't have display server)
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            
            # Create context
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set up request interception
            await self.page.route('**/*', self.intercept_requests)
            
            print(f"[OAUTH INTERCEPTOR] ✅ Browser session started")
            print(f"[OAUTH INTERCEPTOR] 🔗 Opening OAuth URL: {oauth_url[:50]}...")
            
            # Navigate to OAuth URL
            await self.page.goto(oauth_url, wait_until='networkidle', timeout=60000)
            
            self.session_active = True
            
            print(f"[OAUTH INTERCEPTOR] ✅ OAuth page loaded, waiting for user to complete login...")
            
            return {
                'success': True,
                'message': 'Browser session started. Please complete OAuth in the browser window.',
                'session_id': id(self)
            }
            
        except Exception as e:
            print(f"[OAUTH INTERCEPTOR] ❌ Error starting session: {e}")
            await self.cleanup()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def intercept_requests(self, route):
        """Intercept network requests to capture tokens"""
        try:
            request = route.request
            headers = request.headers
            url = request.url
            
            # Capture Authorization Bearer token
            auth_header = headers.get('authorization', '')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '').strip()
                if token and len(token) > 20:
                    self.access_token = token
                    print(f"[OAUTH INTERCEPTOR] ✅ Captured Access Token: {token[:30]}...")
            
            # Capture Firebase token (token-id header)
            token_id = headers.get('token-id', '')
            if token_id and len(token_id) > 20:
                self.firebase_token = token_id
                print(f"[OAUTH INTERCEPTOR] ✅ Captured Firebase Token: {token_id[:30]}...")
            
            # Capture PIT token from GHL API calls
            if 'leadconnectorhq.com' in url or 'gohighlevel.com' in url:
                if auth_header and 'Bearer' in auth_header:
                    pit_token = auth_header.replace('Bearer ', '').strip()
                    if pit_token and len(pit_token) > 20 and not self.pit_token:
                        self.pit_token = pit_token
                        print(f"[OAUTH INTERCEPTOR] ✅ Captured PIT Token: {pit_token[:30]}...")
            
            # Continue with the request
            await route.continue_()
            
        except Exception as e:
            print(f"[OAUTH INTERCEPTOR] ⚠️ Interception error: {e}")
            await route.continue_()
    
    async def wait_for_completion(self, timeout_seconds: int = 300):
        """Wait for OAuth completion and token capture"""
        try:
            print(f"[OAUTH INTERCEPTOR] ⏳ Waiting for OAuth completion (timeout: {timeout_seconds}s)...")
            
            start_time = datetime.now()
            check_interval = 2  # Check every 2 seconds
            
            while (datetime.now() - start_time).seconds < timeout_seconds:
                # Check if we've captured tokens
                if self.access_token or self.firebase_token:
                    print(f"[OAUTH INTERCEPTOR] ✅ Tokens captured!")
                    await asyncio.sleep(5)  # Wait a bit more to capture any additional tokens
                    break
                
                # Check if browser is still open
                if not self.session_active or not self.page:
                    print(f"[OAUTH INTERCEPTOR] ⚠️ Browser session closed")
                    break
                
                await asyncio.sleep(check_interval)
            
            return {
                'success': True,
                'tokens_captured': {
                    'access_token': bool(self.access_token),
                    'firebase_token': bool(self.firebase_token),
                    'pit_token': bool(self.pit_token)
                },
                'access_token': self.access_token,
                'firebase_token': self.firebase_token,
                'pit_token': self.pit_token
            }
            
        except Exception as e:
            print(f"[OAUTH INTERCEPTOR] ❌ Error waiting for completion: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def extract_tokens_from_storage(self):
        """Extract tokens from browser storage as fallback"""
        try:
            if not self.page:
                return
            
            print(f"[OAUTH INTERCEPTOR] 🔍 Extracting tokens from browser storage...")
            
            # Get localStorage
            local_storage = await self.page.evaluate("() => Object.entries(localStorage)")
            
            for key, value in local_storage:
                try:
                    import json
                    data = json.loads(value)
                    if isinstance(data, dict):
                        if 'access_token' in data and not self.access_token:
                            self.access_token = data['access_token']
                            print(f"[OAUTH INTERCEPTOR] ✅ Found access_token in localStorage")
                        if 'firebase_token' in data and not self.firebase_token:
                            self.firebase_token = data['firebase_token']
                            print(f"[OAUTH INTERCEPTOR] ✅ Found firebase_token in localStorage")
                except:
                    pass
            
            # Get sessionStorage
            session_storage = await self.page.evaluate("() => Object.entries(sessionStorage)")
            
            for key, value in session_storage:
                try:
                    import json
                    data = json.loads(value)
                    if isinstance(data, dict):
                        if 'access_token' in data and not self.access_token:
                            self.access_token = data['access_token']
                            print(f"[OAUTH INTERCEPTOR] ✅ Found access_token in sessionStorage")
                except:
                    pass
                    
        except Exception as e:
            print(f"[OAUTH INTERCEPTOR] ⚠️ Error extracting from storage: {e}")
    
    async def get_captured_tokens(self):
        """Get all captured tokens"""
        # Try to extract from storage as fallback
        await self.extract_tokens_from_storage()
        
        return {
            'access_token': self.access_token,
            'firebase_token': self.firebase_token,
            'pit_token': self.pit_token,
            'tokens_captured': {
                'access_token': bool(self.access_token),
                'firebase_token': bool(self.firebase_token),
                'pit_token': bool(self.pit_token)
            }
        }
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            print(f"[OAUTH INTERCEPTOR] 🧹 Cleaning up browser session...")
            
            self.session_active = False
            
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            print(f"[OAUTH INTERCEPTOR] ✅ Cleanup complete")
            
        except Exception as e:
            print(f"[OAUTH INTERCEPTOR] ⚠️ Cleanup error: {e}")
