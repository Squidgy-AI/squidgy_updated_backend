#!/usr/bin/env python3
"""
Facebook Pages API - EXACT COPY of working complete_facebook_viewer.py approach
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import httpx
import random
from datetime import datetime, timezone
from supabase import create_client, Client
from playwright.async_api import async_playwright

app = FastAPI()

class FacebookPagesRequest(BaseModel):
    user_id: str
    location_id: str  
    email: str
    password: str
    firm_user_id: Optional[str] = "soma-firm-user-id"
    manual_jwt_token: Optional[str] = None  # Allow manual JWT input

class FacebookPageResponse(BaseModel):
    page_id: str
    page_name: str
    is_connected: bool
    instagram_available: bool

class FacebookPagesResponse(BaseModel):
    success: bool
    message: str
    pages: List[FacebookPageResponse] = []
    total_pages: int = 0
    jwt_token_captured: bool = False
    jwt_token: Optional[str] = None  # Include actual JWT token for frontend use
    manual_mode: bool = False
    manual_instructions: Optional[str] = None

@app.post("/api/facebook/get-pages", response_model=FacebookPagesResponse)
async def get_facebook_pages(request: FacebookPagesRequest):
    """
    Extract JWT token, fetch Facebook pages, and store in database
    Using EXACT SAME approach as working complete_facebook_viewer.py
    """
    
    try:
        print(f"🚀 Starting Facebook pages extraction for user: {request.email}")
        print(f"[FACEBOOK AUTOMATION] 📍 Target Location ID: {request.location_id}")
        print(f"[FACEBOOK AUTOMATION] 👤 User ID: {request.user_id}")
        print(f"[FACEBOOK AUTOMATION] 🏢 Firm User ID: {request.firm_user_id}")
        print("[FACEBOOK AUTOMATION] This process will:")
        print("[FACEBOOK AUTOMATION]   1. Login to GHL")
        print("[FACEBOOK AUTOMATION]   2. Handle 2FA automatically")
        print("[FACEBOOK AUTOMATION]   3. Create Private Integration Token (PIT)")
        print("[FACEBOOK AUTOMATION]   4. Extract Facebook pages")
        print("[FACEBOOK AUTOMATION]   5. Store everything in database")
        
        # Check if manual JWT token provided
        if request.manual_jwt_token:
            print("🔧 Using manually provided JWT token...")
            print("[FACEBOOK AUTOMATION] ⚠️  Manual mode - skipping automation")
            jwt_token = request.manual_jwt_token
        else:
            # Try automated JWT extraction using EXACT SAME approach
            print("🤖 Attempting automated JWT extraction with WORKING approach...")
            print("[FACEBOOK AUTOMATION] 🚀 Starting automated browser workflow...")
            print("[FACEBOOK AUTOMATION] This may take 2-3 minutes to complete")
            jwt_token = await auto_extract_jwt_token_working_approach(request.email, request.password, request.location_id)
        
        if not jwt_token:
            print("[FACEBOOK AUTOMATION] ❌ AUTOMATION FAILED!")
            print("[FACEBOOK AUTOMATION] The automation could not complete successfully")
            print("[FACEBOOK AUTOMATION] Possible reasons:")
            print("[FACEBOOK AUTOMATION]   - 2FA not approved on mobile")
            print("[FACEBOOK AUTOMATION]   - Browser automation blocked")
            print("[FACEBOOK AUTOMATION]   - Network connectivity issues")
            print("[FACEBOOK AUTOMATION]   - GHL interface changes")
            print("[FACEBOOK AUTOMATION] Providing manual instructions as fallback...")
            
            # Return manual mode instructions
            manual_instructions = f"""
MANUAL MODE: Automated browser detection failed. Please follow these steps:

1. Open browser and go to: https://app.gohighlevel.com/login
2. Login with: {request.email} / {request.password}
3. Complete 2FA if required
4. Once logged in, open Developer Tools (F12)
5. Go to Network tab, filter by 'Fetch/XHR'
6. Click on any navigation item (Dashboard, Contacts, etc.)
7. Look for requests to 'backend.leadconnectorhq.com'
8. Find a request with 'token-id' header
9. Copy the token-id value (starts with 'eyJ')
10. Call this API again with manual_jwt_token: "your-token-here"

Location ID: {request.location_id}
User ID: {request.user_id}
"""
            
            return FacebookPagesResponse(
                success=False,
                message="Automated extraction failed - manual mode required",
                manual_mode=True,
                manual_instructions=manual_instructions
            )
        
        print(f"✅ JWT token obtained: {jwt_token[:50]}...")
        print("[FACEBOOK AUTOMATION] ✅ AUTOMATION SUCCESSFUL!")
        print("[FACEBOOK AUTOMATION] 🎉 Private Integration Token (PIT) created successfully!")
        print(f"[FACEBOOK AUTOMATION] 🔑 Token length: {len(jwt_token)} characters")
        print("[FACEBOOK AUTOMATION] Token appears to be valid format")
        
        # Step 2: Fetch Facebook Pages
        print("[FACEBOOK AUTOMATION] 📄 Step 2: Fetching Facebook pages using the PIT...")
        print(f"[FACEBOOK AUTOMATION] 🎯 Using location ID: {request.location_id}")
        pages_data = await fetch_facebook_pages_api(jwt_token, request.location_id)
        
        if not pages_data["success"]:
            print("[FACEBOOK AUTOMATION] ❌ Failed to fetch Facebook pages!")
            print(f"[FACEBOOK AUTOMATION] Error: {pages_data.get('error', 'Unknown error')}")
            print("[FACEBOOK AUTOMATION] This means:")
            print("[FACEBOOK AUTOMATION]   - PIT token was created successfully")
            print("[FACEBOOK AUTOMATION]   - But the Facebook API call failed")
            print("[FACEBOOK AUTOMATION]   - Could be permissions or API issues")
            
            return FacebookPagesResponse(
                success=False,
                message=f"Failed to fetch Facebook pages: {pages_data.get('error', 'Unknown error')}",
                jwt_token_captured=True
            )
        
        pages = pages_data["pages"]
        print(f"✅ Found {len(pages)} Facebook pages")
        print("[FACEBOOK AUTOMATION] ✅ Facebook pages retrieved successfully!")
        print(f"[FACEBOOK AUTOMATION] 📄 Page count: {len(pages)}")
        
        for i, page in enumerate(pages, 1):
            print(f"[FACEBOOK AUTOMATION]   {i}. {page.get('page_name', 'Unknown')} (ID: {page.get('page_id', 'Unknown')})")
        
        if len(pages) == 0:
            print("[FACEBOOK AUTOMATION] ⚠️  WARNING: No Facebook pages found!")
            print("[FACEBOOK AUTOMATION] This could mean:")
            print("[FACEBOOK AUTOMATION]   - No Facebook pages connected to this GHL account")
            print("[FACEBOOK AUTOMATION]   - Facebook integration not set up")
            print("[FACEBOOK AUTOMATION]   - Permission issues")
        
        # Step 3: Store in Database
        print("[FACEBOOK AUTOMATION] 💾 Step 3: Storing pages and tokens in database...")
        db_success = await store_pages_in_database(pages, request, jwt_token)
        
        if db_success:
            print("[FACEBOOK AUTOMATION] ✅ Database storage successful!")
            print("[FACEBOOK AUTOMATION] All Facebook pages and PIT token saved to database")
        else:
            print("[FACEBOOK AUTOMATION] ⚠️  Database storage failed!")
            print("[FACEBOOK AUTOMATION] Pages were found but not saved to database")
        
        if not db_success:
            print("⚠️ Database storage failed, but returning pages anyway")
        
        # Step 4: Format Response for Frontend (with database connection status)
        formatted_pages = []
        for page in pages:
            # Check database for actual connection status
            page_id = page.get("facebookPageId", "unknown")
            
            # Query database for connection status
            try:
                from supabase import create_client, Client
                supabase_url = "https://aoteeitreschwzkbpqyd.supabase.co"
                supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
                supabase_client = create_client(supabase_url, supabase_key)
                
                db_response = supabase_client.table('squidgy_facebook_pages')\
                    .select("is_connected_to_ghl")\
                    .eq('location_id', request.location_id)\
                    .eq('page_id', page_id)\
                    .execute()
                
                # Use database value if available, otherwise default to False
                is_connected = db_response.data[0]['is_connected_to_ghl'] if db_response.data else False
                
            except Exception as e:
                print(f"⚠️ Could not check database connection status: {e}")
                is_connected = False  # Default to False if database check fails
            
            formatted_pages.append(FacebookPageResponse(
                page_id=page_id,
                page_name=page.get("facebookPageName", "Unknown Page"),
                is_connected=is_connected,  # Use database value
                instagram_available=page.get("isInstagramAvailable", False)
            ))
        
        return FacebookPagesResponse(
            success=True,
            message=f"Successfully retrieved {len(pages)} Facebook pages",
            pages=formatted_pages,
            total_pages=len(pages),
            jwt_token_captured=True,
            jwt_token=jwt_token,  # Return actual JWT token for frontend
            manual_mode=bool(request.manual_jwt_token)
        )
        
    except Exception as e:
        print(f"💥 Error in get_facebook_pages: {str(e)}")
        return FacebookPagesResponse(
            success=False,
            message=f"Unexpected error: {str(e)}"
        )

async def auto_extract_jwt_token_working_approach(email: str, password: str, location_id: str) -> Optional[str]:
    """EXACT SAME as working complete_facebook_viewer.py"""
    
    print(f"🔄 AUTOMATIC LOGIN & TOKEN EXTRACTION")
    print("=" * 55)
    print("📱 Opening browser...")
    print("🔐 Handling login automatically...")
    print("📱 If you see MFA, approve it on your mobile")
    print("🔍 Extracting your access token...")
    print()
    
    try:
        async with async_playwright() as p:
            # EXACT SAME browser launch as working script
            # Browser config with debug mode option
            import os
            is_production = os.environ.get('HEROKU_APP_NAME') or os.environ.get('DYNO')
            debug_browser = os.environ.get('DEBUG_BROWSER', 'false').lower() == 'true'
            
            # Debug mode logging
            if debug_browser:
                print("🔍 DEBUG MODE: Browser will be VISIBLE for debugging")
            elif is_production:
                print("🚀 PRODUCTION MODE: Browser running headless")
            else:
                print("💻 LOCAL MODE: Browser will be visible")
            
            browser_args = [
                '--no-sandbox',  # Required for Heroku
                '--disable-setuid-sandbox',  # Required for Heroku
                '--disable-dev-shm-usage',  # Prevents crash in production
                '--disable-extensions',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-sync',
                '--incognito'
            ]
            
            # Add debug-friendly args if debug mode
            if debug_browser:
                browser_args.extend([
                    '--start-maximized',  # Make window large
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ])
            else:
                browser_args.extend([
                    '--disable-gpu',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ])
            
            browser = await p.chromium.launch(
                headless=False if debug_browser else (True if is_production else False),
                args=browser_args
            )
            
            # EXACT SAME context as working script
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                storage_state=None,  # No stored state
                ignore_https_errors=True,  # Ignore SSL issues
                # Clear all cached data
                extra_http_headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            page = await context.new_page()
            
            # EXACT SAME JWT capture as working script
            jwt_token = None
            request_count = 0
            
            def handle_request(request):
                nonlocal jwt_token, request_count
                request_count += 1
                
                # Only capture first JWT token found
                if not jwt_token:
                    headers = request.headers
                    if 'token-id' in headers and headers['token-id'].startswith('eyJ'):
                        jwt_token = headers['token-id']
                        print(f"   ✅ Access token captured! (Request #{request_count})")
            
            page.on('request', handle_request)
            
            # EXACT SAME navigation as working script
            print("   🌐 Opening GoHighLevel login page...")
            await page.goto("https://app.gohighlevel.com/login", wait_until='networkidle')
            
            current_url = page.url
            print(f"   📍 Current page: {current_url}")
            print(f"   📄 Page title: {await page.title()}")
            
            # Enhanced debugging info
            if debug_browser:
                content = await page.content()
                print(f"   📄 Page content length: {len(content)} characters")
                if "login" in content.lower():
                    print("   ✅ Login page content detected")
                else:
                    print("   ⚠️ Login page content not detected")
                print(f"   🔍 Page loaded state: {await page.evaluate('document.readyState')}")
            
            # EXACT SAME wait as working script
            await page.wait_for_timeout(2000)
            
            # EXACT SAME login check as working script
            print("   🔐 Fresh incognito session - entering credentials...")
            
            # Check if we can see login form
            try:
                await page.wait_for_selector('input[type="email"], input[name="email"]', timeout=30000)  # 30 seconds
                print("   ✅ Login form detected")
            except:
                print("   ⚠️ Login form not found, trying alternative approach...")
                if debug_browser:
                    print(f"   🔍 Current URL after form detection: {page.url}")
                    print(f"   🔍 Available input fields: {len(await page.query_selector_all('input'))}")
                
                # Try going to main page and then login
                await page.goto("https://app.gohighlevel.com/", wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                if debug_browser:
                    print(f"   🔍 After redirect to main page: {page.url}")
            
            # EXACT SAME login process as working script
            login_success = await _auto_login_working(page, email, password)
            
            if login_success:
                print("   ⏳ Checking for 2FA requirements...")
                
                # 🔐 ENHANCED 2FA HANDLING - Added as requested
                from enhanced_2fa_service import Enhanced2FAService, GmailEmailConfig
                gmail_config = GmailEmailConfig(location_id=location_id)
                enhanced_2fa = Enhanced2FAService(gmail_config)
                
                # Handle 2FA flow: Send Security Code -> Check Email -> Input Code
                two_fa_result = await enhanced_2fa.handle_ghl_2fa_flow(page)
                
                if two_fa_result["success"]:
                    if two_fa_result.get("2fa_required"):
                        print("   ✅ 2FA completed successfully!")
                        print("   📧 Security code sent, retrieved from email, and inputted automatically")
                    else:
                        print("   ℹ️ No 2FA required")
                else:
                    print(f"   ⚠️ 2FA automation failed: {two_fa_result.get('error', 'Unknown error')}")
                    print("   💡 Continuing to dashboard - you may need to complete 2FA manually")
                
                print("   ⏳ Waiting for dashboard...")
                try:
                    await _wait_for_dashboard_working(page)
                    print("   ✅ Dashboard loaded successfully")
                except:
                    print("   ⚠️ Dashboard timeout, but continuing...")
                
                print("   🔍 Extracting access token...")
                await _trigger_requests_working(page)
                await page.wait_for_timeout(3000)
                
                if not jwt_token:
                    print("   🔄 Trying additional token extraction methods...")
                    try:
                        await page.reload(wait_until='networkidle')
                        await _trigger_requests_working(page)
                        await page.wait_for_timeout(3000)
                    except:
                        print("   ⚠️ Page reload failed, but may have token already...")
            else:
                print("   ❌ Login failed")
            
            await browser.close()
            
            if jwt_token:
                print("   🎉 SUCCESS: Access token extracted!")
                return jwt_token
            else:
                print("   ❌ Could not extract access token")
                return None
                
    except ImportError:
        print("   ❌ Browser automation not available")
        print("   💡 Please install: pip install playwright")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

async def _auto_login_working(page, email, password):
    """EXACT SAME login as working script"""
    
    # Wait for page to be fully loaded
    await page.wait_for_load_state('networkidle')
    
    # Email field - EXACT SAME selectors as working script
    email_selectors = [
        'input[type="email"]', 
        'input[name="email"]', 
        'input[placeholder*="email" i]',
        '#email'
    ]
    
    email_filled = False
    for selector in email_selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.fill(selector, '')  # Clear any existing content
            await page.fill(selector, email)
            print("   📧 Email entered successfully")
            email_filled = True
            break
        except Exception as e:
            print(f"   ⚠️ Email selector {selector} failed: {str(e)[:50]}...")
            continue
    
    if not email_filled:
        print("   ❌ Could not find email field")
        return False
    
    # Small delay between fields
    await page.wait_for_timeout(1000)
    
    # Password field - EXACT SAME selectors as working script
    password_selectors = [
        'input[type="password"]', 
        'input[name="password"]',
        '#password'
    ]
    
    password_filled = False
    for selector in password_selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.fill(selector, '')  # Clear any existing content
            await page.fill(selector, password)
            print("   🔐 Password entered successfully")
            password_filled = True
            break
        except Exception as e:
            print(f"   ⚠️ Password selector {selector} failed: {str(e)[:50]}...")
            continue
    
    if not password_filled:
        print("   ❌ Could not find password field")
        return False
    
    # Small delay before submit
    await page.wait_for_timeout(1000)
    
    # Submit button - EXACT SAME selectors as working script
    login_selectors = [
        'button[type="submit"]', 
        'button:has-text("Sign In")', 
        'button:has-text("Log In")',
        'button:has-text("Login")',
        'input[type="submit"]',
        '.login-btn',
        '#login-button'
    ]
    
    login_submitted = False
    for selector in login_selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.click(selector)
            print("   🔄 Login submitted successfully")
            login_submitted = True
            break
        except Exception as e:
            print(f"   ⚠️ Login selector {selector} failed: {str(e)[:50]}...")
            continue
    
    if not login_submitted:
        print("   ❌ Could not find login button")
        return False
    
    return True

async def _wait_for_dashboard_working(page):
    """EXACT SAME dashboard wait as working script"""
    dashboard_indicators = ['text=Dashboard', 'text=Conversations', 'text=Opportunities']
    for indicator in dashboard_indicators:
        try:
            await page.wait_for_selector(indicator, timeout=120000)  # 2 minutes for MFA
            print("   ✅ Dashboard loaded")
            return
        except:
            continue
    await page.wait_for_load_state('networkidle', timeout=60000)  # 1 minute for network idle

async def _trigger_requests_working(page):
    """EXACT SAME request triggers as working script"""
    elements = [
        'text=Dashboard', 'text=Conversations', 'text=Opportunities', 
        'text=Contacts', 'text=Marketing', 'nav a'
    ]
    
    for element in elements:
        try:
            await page.click(element, timeout=2000)
            await page.wait_for_timeout(500)
        except:
            continue
    
    # Also try scrolling and refreshing
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(2000)
    except:
        pass

async def fetch_facebook_pages_api(jwt_token: str, location_id: str) -> Dict:
    """Fetch Facebook pages using JWT token - this part works reliably"""
    
    headers = {
        "token-id": jwt_token,
        "channel": "APP",
        "source": "WEB_USER",
        "version": "2021-07-28",
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:  # Increased to 2 minutes
            pages_url = f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/allPages?limit=20"
            response = await client.get(pages_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get('pages', [])
                return {"success": True, "pages": pages}
            else:
                return {"success": False, "error": f"API returned {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"success": False, "error": str(e)}

async def store_pages_in_database(pages: List[Dict], request: FacebookPagesRequest, jwt_token: str) -> bool:
    """Store Facebook pages in database - this part works reliably"""
    
    try:
        supabase_url = "https://aoteeitreschwzkbpqyd.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print(f"💾 Attempting to save {len(pages)} pages to database...")
        
        for page in pages:
            page_data = {
                "firm_user_id": request.firm_user_id,
                "location_id": request.location_id,
                "user_id": request.user_id,
                "page_id": page.get("facebookPageId", "unknown"),
                "page_name": page.get("facebookPageName", "Unknown Page"),
                "page_access_token": jwt_token,
                "page_category": "business",
                "instagram_business_account_id": "",
                "is_instagram_available": page.get("isInstagramAvailable", False),
                "is_connected_to_ghl": False,  # Initially false, will be set to true when user connects
                "connected_at": None,  # Will be set when user actually connects
                "raw_page_data": {
                    "page_data": page,
                    "integration_info": {
                        "ghl_login_email": request.email,
                        "user_name": "Soma Addakula",
                        "location_name": f"SolarBusiness_{request.location_id}",
                        "jwt_token": jwt_token,
                        "integration_completed_at": datetime.now(timezone.utc).isoformat(),
                        "ghl_integration_status": "connected"
                    }
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Use upsert with on_conflict to handle duplicate key properly
            response = supabase.table('squidgy_facebook_pages').upsert(
                page_data,
                on_conflict='location_id,page_id'
            ).execute()
            print(f"✅ Saved page: {page.get('facebookPageName')} to database")
        
        return True
        
    except Exception as e:
        print(f"💥 Database error: {e}")
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)  # Different port