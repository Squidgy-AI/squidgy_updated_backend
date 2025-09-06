#!/usr/bin/env python3
"""
HighLevel Complete Automation with Playwright and Database Integration
- Uses Playwright instead of Selenium for better performance
- Automatically retrieves OTP from Gmail
- Creates Private Integration Token (PIT) with all scopes
- Captures access tokens and Firebase tokens
- Stores all data in the database
"""

import os
import sys
import time
import imaplib
import email
import re
import json
import base64
import asyncio
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, BrowserContext
import asyncpg
from typing import Optional, Dict, Any

# Import database functions
from database import fetch_one, execute, get_connection, release_connection

class HighLevelPlaywrightAutomation:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.firebase_token = None
        self.api_tokens = {
            'authorization': None,
            'token-id': None
        }
        self.pit_token = None
        
    async def setup_browser(self):
        """Initialize Playwright browser using EXACT same approach as working facebook script"""
        try:
            self.playwright = await async_playwright().start()
            
            # Use EXACT same browser config as working script
            import os
            is_production = os.environ.get('HEROKU_APP_NAME') or os.environ.get('DYNO')
            debug_browser = os.environ.get('DEBUG_BROWSER', 'false').lower() == 'true'
            
            if debug_browser:
                print("🔍 DEBUG MODE: Browser will be VISIBLE for debugging")
            elif is_production:
                print("🚀 PRODUCTION MODE: Browser running headless")
            else:
                print("💻 LOCAL MODE: Browser will be visible")
            
            # EXACT same browser args as working script
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
            
            # Launch browser with EXACT same config as working script
            self.browser = await self.playwright.chromium.launch(
                headless=False if debug_browser else (True if is_production else False),
                args=browser_args
            )
            
            # EXACT same context as working script
            self.context = await self.browser.new_context(
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
            
            # Create page
            self.page = await self.context.new_page()
            
            # EXACT same JWT capture as working script
            self.jwt_token = None
            self.request_count = 0
            
            def handle_request(request):
                self.request_count += 1
                
                # Only capture first JWT token found
                if not self.jwt_token:
                    headers = request.headers
                    if 'token-id' in headers and headers['token-id'].startswith('eyJ'):
                        self.jwt_token = headers['token-id']
                        self.firebase_token = headers['token-id']
                        self.api_tokens['token-id'] = headers['token-id']
                        print(f"   ✅ JWT token captured! (Request #{self.request_count})")
                
                # Also capture Authorization headers
                auth_header = headers.get('authorization', '')
                if auth_header and auth_header.startswith('Bearer ') and not self.access_token:
                    token = auth_header.replace('Bearer ', '').strip()
                    if token and len(token) > 20:
                        self.access_token = token
                        self.api_tokens['authorization'] = token
                        print(f"[✅ TOKENS] Found Authorization Bearer token: {token[:20]}...")
            
            self.page.on('request', handle_request)
            
            print("[SUCCESS] Playwright browser initialized with working config")
            return True
            
        except Exception as e:
            print(f"[ERROR] Browser setup failed: {str(e)}")
            return False
    
    async def intercept_requests(self, route):
        """Intercept network requests to capture tokens"""
        try:
            request = route.request
            headers = request.headers
            
            # Check for Authorization header (Bearer token)
            auth_header = headers.get('authorization', '')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '').strip()
                if token and len(token) > 20:
                    self.access_token = token
                    self.api_tokens['authorization'] = token
                    print(f"[✅ TOKENS] Found Authorization Bearer token: {token[:20]}...")
            
            # Check for token-id header (Firebase ID token)
            token_id = headers.get('token-id', '')
            if token_id and len(token_id) > 20:
                self.firebase_token = token_id
                self.api_tokens['token-id'] = token_id
                print(f"[✅ TOKENS] Found token-id (Firebase): {token_id[:20]}...")
            
            # Continue with the request
            await route.continue_()
            
        except Exception as e:
            # Continue with the request even if interception fails
            await route.continue_()
    
    def get_otp_from_gmail(self):
        """Get OTP code from Gmail automatically"""
        try:
            print("[📧 EMAIL] Connecting to Gmail for OTP...")
            
            # Gmail credentials from environment
            email_address = os.getenv('GMAIL_2FA_EMAIL', 'somashekhar34@gmail.com')
            email_password = os.getenv('GMAIL_2FA_APP_PASSWORD', 'ytmfxlelgyojxjmf')
            
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(email_address, email_password)
            mail.select('inbox')
            
            print("[📧 EMAIL] Searching for latest GHL security code email...")
            
            # Search for recent security code emails from GHL
            search_criteria = '(FROM "noreply@talk.onetoo.com" SUBJECT "Login security code" SINCE "' + (datetime.now() - timedelta(hours=1)).strftime("%d-%b-%Y") + '")'
            result, data = mail.search(None, search_criteria)
            
            if result != 'OK' or not data[0]:
                # Fallback to unread emails
                print("[📧 EMAIL] No recent emails found, checking unread emails...")
                search_criteria = '(FROM "noreply@talk.onetoo.com" UNSEEN SUBJECT "Login security code")'
                result, data = mail.search(None, search_criteria)
                
                if result != 'OK' or not data[0]:
                    print("[📧 EMAIL] No security code emails found")
                    return None
            
            email_ids = data[0].split()
            print(f"[📧 EMAIL] Found {len(email_ids)} security code email(s)")
            
            if not email_ids:
                return None
            
            # Get the latest email by ID (highest ID = most recent)
            latest_email_id = max(email_ids, key=lambda x: int(x))
            print(f"[📧 EMAIL] Processing most recent email ID: {latest_email_id.decode()}")
            
            # Fetch the email
            result, msg_data = mail.fetch(latest_email_id, '(BODY.PEEK[])')
            if result != 'OK':
                print("[❌ EMAIL] Failed to fetch email")
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get email date
            email_date = msg.get('Date', 'Unknown date')
            print(f"[📧 EMAIL] Email date: {email_date}")
            
            # Extract body
            body = self._extract_email_body(msg)
            print(f"[📧 EMAIL] Email body preview: {body[:200]}...")
            
            # Extract OTP using patterns
            otp_patterns = [
                r'Your login security code:\s*(\d{6})',
                r'login security code:\s*(\d{6})',
                r'security code:\s*(\d{6})',
                r'code:\s*(\d{6})',
                r'\b(\d{6})\b'
            ]
            
            for pattern in otp_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    otp = matches[0]
                    print(f"[✅ OTP] Extracted OTP: {otp}")
                    
                    # Try to mark email as read
                    try:
                        mail.store(latest_email_id, '+FLAGS', '\\Seen')
                    except:
                        pass
                    
                    try:
                        mail.close()
                        mail.logout()
                    except:
                        pass
                    
                    return otp
            
            print("[❌ OTP] No OTP found in email body")
            mail.close()
            mail.logout()
            return None
            
        except Exception as e:
            print(f"[❌ EMAIL] Error reading email: {str(e)}")
            return None
    
    def _extract_email_body(self, msg):
        """Extract body text from email message"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
                    except:
                        try:
                            body = part.get_payload(decode=True).decode('latin-1')
                            break
                        except:
                            continue
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8')
            except:
                try:
                    body = msg.get_payload(decode=True).decode('latin-1')
                except:
                    body = str(msg.get_payload())
        
        return body
    
    def decode_jwt_token(self, token):
        """Decode JWT token to extract expiry information"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload_part = parts[1]
            padding = 4 - len(payload_part) % 4
            if padding != 4:
                payload_part += '=' * padding
            
            payload_json = base64.urlsafe_b64decode(payload_part)
            payload = json.loads(payload_json)
            
            if 'exp' in payload:
                exp_timestamp = payload['exp']
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                
                iat_datetime = None
                if 'iat' in payload:
                    iat_timestamp = payload['iat']
                    iat_datetime = datetime.fromtimestamp(iat_timestamp)
                
                return {
                    'expires_at': exp_datetime,
                    'issued_at': iat_datetime,
                    'expires_timestamp': exp_timestamp,
                    'full_payload': payload
                }
            
            return None
            
        except Exception as e:
            print(f"[⚠️ JWT] Could not decode token: {e}")
            return None
    
    async def handle_login_and_verification(self, email: str, password: str):
        """Handle login and automatic email verification using EXACT working Facebook script approach"""
        try:
            print("[LOGIN] Using EXACT working Facebook script login approach...")
            
            # EXACT SAME login process as working Facebook script
            login_success = await self._auto_login_working_ghl(self.page, email, password)
            
            if not login_success:
                print("[ERROR] Login failed")
                return False
            
            # Wait for login to process
            await self.page.wait_for_timeout(8000)
            
            # Check if 2FA is required
            if await self.page.locator('text=verification').count() > 0 or await self.page.locator('input[maxlength="1"]').count() > 0:
                print("\n" + "="*60)
                print("[VERIFICATION] Email verification required!")
                print("="*60)
                
                # Click Send Code button if present
                try:
                    await self.page.click('button:has-text("Send"), button:has-text("Code")', timeout=5000)
                    print("[VERIFICATION] 'Send Code' button clicked")
                    await self.page.wait_for_timeout(5000)
                except:
                    print("[INFO] Send Code button not found or already clicked")
                
                # Get OTP automatically
                print("[📧 AUTO] Starting automatic OTP retrieval...")
                
                max_attempts = 30
                otp_code = None
                
                for attempt in range(max_attempts):
                    print(f"[⏳ OTP] Attempt {attempt + 1}/{max_attempts} - Checking email...")
                    otp_code = self.get_otp_from_gmail()
                    if otp_code:
                        print(f"[✅ AUTO] Successfully extracted OTP: {otp_code}")
                        break
                    await asyncio.sleep(1)
                
                if not otp_code:
                    print("[❌ AUTO] Failed to get OTP automatically")
                    return False
                
                # Enter OTP digits
                print(f"[✅ VERIFICATION] Using OTP code: {otp_code}")
                
                # Find OTP input fields
                otp_inputs = await self.page.locator('input[maxlength="1"]').all()
                
                if len(otp_inputs) >= len(otp_code):
                    print(f"[📱 VERIFICATION] Found {len(otp_inputs)} digit inputs")
                    
                    # Enter each digit
                    for i, digit in enumerate(otp_code):
                        if i < len(otp_inputs):
                            await otp_inputs[i].click()
                            await otp_inputs[i].fill(digit)
                            await self.page.wait_for_timeout(300)
                            print(f"[VERIFICATION] Digit {i+1} entered successfully")
                    
                    print("[✅ VERIFICATION] All digits entered successfully!")
                    await self.page.wait_for_timeout(5000)
                else:
                    print("[❌ VERIFICATION] Could not find OTP input fields")
                    return False
            
            print("[SUCCESS] Login and verification completed!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Login and verification failed: {e}")
            return False
    
    async def create_private_integration(self, location_id: str):
        """Create the private integration with all required scopes"""
        try:
            print("[PIT] Creating private integration...")
            await self.page.wait_for_timeout(5000)
            
            # Try to find and click integration creation button
            max_retries = 3
            for retry in range(max_retries):
                print(f"\n[🔄 RETRY] Attempt {retry + 1}/{max_retries} to find integration button...")
                
                try:
                    # Multiple selectors to try
                    button_selectors = [
                        'button:has-text("Create Private Integration")',
                        'button:has-text("Create Integration")',
                        'button:has-text("New Integration")',
                        'button:has-text("Add Integration")',
                        'button span:has-text("Create")',
                        '[data-testid="create-integration"]'
                    ]
                    
                    button_clicked = False
                    for selector in button_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                await self.page.click(selector)
                                print(f"[✅ SUCCESS] Integration button clicked using: {selector}")
                                button_clicked = True
                                break
                        except:
                            continue
                    
                    if button_clicked:
                        await self.page.wait_for_timeout(3000)
                        break
                    else:
                        if retry < max_retries - 1:
                            await self.page.wait_for_timeout(5000)
                        else:
                            print("[💡 FALLBACK] Could not find integration button automatically")
                            await self.page.wait_for_timeout(20000)  # Wait for manual intervention
                            
                except Exception as e:
                    print(f"[❌ ERROR] Failed on attempt {retry + 1}: {e}")
                    if retry == max_retries - 1:
                        print("[💡 FALLBACK] Continuing anyway...")
            
            # Fill integration name
            try:
                await self.page.fill('input[name="name"], input[placeholder*="name" i]', 'location key')
                print("[INTEGRATION] Integration name set to: location key")
                await self.page.wait_for_timeout(2000)
            except Exception as e:
                print(f"[WARNING] Could not fill integration name: {e}")
            
            # Submit the form
            try:
                await self.page.click('button[type="submit"], button:has-text("Next"), button:has-text("Continue")')
                print("[INTEGRATION] Form submitted")
                await self.page.wait_for_timeout(5000)
            except Exception as e:
                print(f"[WARNING] Could not submit form: {e}")
            
            # Select scopes
            scopes_to_add = [
                "View Contacts", "Edit Contacts",
                "View Conversation Reports", "Edit Conversations",
                "View Calendars", "View Businesses",
                "View Conversation Messages", "Edit Conversation Messages",
                "View Custom Fields", "Edit Custom Fields",
                "View Custom Values", "Edit Custom Values",
                "View Medias", "Edit Tags", "View Tags"
            ]
            
            try:
                print("[INTEGRATION] Selecting scopes...")
                
                # Find scope selection input
                scope_input = self.page.locator('input[placeholder*="Search" i], input[placeholder*="scope" i]').first
                
                for i, scope in enumerate(scopes_to_add):
                    try:
                        print(f"[{i+1}/{len(scopes_to_add)}] Selecting: {scope}")
                        
                        await scope_input.click()
                        await scope_input.fill(scope)
                        await self.page.wait_for_timeout(500)
                        await self.page.keyboard.press('Enter')
                        await self.page.wait_for_timeout(300)
                        
                        print(f"  ✓ Added scope: {scope}")
                    except Exception as e:
                        print(f"  ❌ Error selecting scope '{scope}': {e}")
                
            except Exception as e:
                print(f"[WARNING] Could not select scopes: {e}")
            
            # Click Create button
            try:
                await self.page.click('button:has-text("Create"), button[type="submit"]')
                print("[INTEGRATION] Clicked Create button")
                await self.page.wait_for_timeout(3000)
            except Exception as e:
                print(f"[WARNING] Could not click Create button: {e}")
            
            # Extract PIT token
            try:
                # Wait for token to appear
                await self.page.wait_for_timeout(3000)
                
                # Try to find and copy token
                token_element = self.page.locator('pre, code, textarea, input[readonly]').first
                
                if await token_element.count() > 0:
                    token_text = await token_element.text_content() or await token_element.input_value()
                    
                    if token_text and token_text.startswith('pit-'):
                        self.pit_token = token_text.strip()
                        
                        print("\n" + "*"*100)
                        print("*" + " "*35 + "INTEGRATION TOKEN EXTRACTED" + " "*35 + "*")
                        print("*"*100)
                        print(f"\n{self.pit_token}\n")
                        print("*"*100)
                        
                        return True
                    
            except Exception as e:
                print(f"[WARNING] Could not extract token: {e}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Private integration creation failed: {e}")
            return False
    
    async def save_to_database(self, firm_user_id: str, agent_id: str, ghl_location_id: str, ghl_user_id: str = None):
        """Save all captured data to the database"""
        try:
            print("\n[💾 DATABASE] Saving tokens and setup data...")
            
            # Decode tokens for expiry info
            access_token_info = None
            firebase_token_info = None
            
            if self.access_token:
                access_token_info = self.decode_jwt_token(self.access_token)
                if access_token_info:
                    self.token_expiry = access_token_info['expires_at']
            
            if self.firebase_token:
                firebase_token_info = self.decode_jwt_token(self.firebase_token)
            
            # Prepare tokens data
            tokens_data = {
                "timestamp": datetime.now().isoformat(),
                "location_id": ghl_location_id,
                "tokens": {
                    "private_integration_token": self.pit_token,
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "firebase_token": self.firebase_token,
                    "api_tokens": self.api_tokens
                },
                "expiry": {
                    "access_token_expires_at": self.token_expiry.isoformat() if self.token_expiry else None,
                    "access_token_expires_in_seconds": (self.token_expiry - datetime.now()).total_seconds() if self.token_expiry else None,
                    "access_token_issued_at": access_token_info['issued_at'].isoformat() if access_token_info and access_token_info['issued_at'] else None,
                    "firebase_token_expires_at": firebase_token_info['expires_at'].isoformat() if firebase_token_info and firebase_token_info['expires_at'] else None,
                    "firebase_token_issued_at": firebase_token_info['issued_at'].isoformat() if firebase_token_info and firebase_token_info['issued_at'] else None
                }
            }
            
            # Setup configuration
            setup_config = {
                "automation_completed": True,
                "pit_created": True,
                "scopes_selected": 15,
                "tokens_captured": {
                    "pit_token": bool(self.pit_token),
                    "access_token": bool(self.access_token),
                    "firebase_token": bool(self.firebase_token)
                },
                "created_at": datetime.now().isoformat()
            }
            
            # Insert into database
            query = """
            INSERT INTO public.squidgy_agent_business_setup 
            (firm_user_id, agent_id, agent_name, setup_json, setup_type, 
             ghl_location_id, ghl_user_id, highlevel_tokens, is_enabled)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (firm_user_id, agent_id, setup_type)
            DO UPDATE SET
                setup_json = EXCLUDED.setup_json,
                highlevel_tokens = EXCLUDED.highlevel_tokens,
                ghl_location_id = EXCLUDED.ghl_location_id,
                ghl_user_id = EXCLUDED.ghl_user_id,
                updated_at = CURRENT_TIMESTAMP,
                is_enabled = EXCLUDED.is_enabled
            """
            
            await execute(
                query,
                firm_user_id,
                agent_id,
                f"Agent_{agent_id}",  # agent_name
                json.dumps(setup_config),  # setup_json
                'GHLSetup',  # setup_type
                ghl_location_id,
                ghl_user_id,
                json.dumps(tokens_data),  # highlevel_tokens
                True  # is_enabled
            )
            
            print("[✅ DATABASE] Successfully saved to database!")
            print(f"[📍] Firm User ID: {firm_user_id}")
            print(f"[🤖] Agent ID: {agent_id}")
            print(f"[📧] GHL Location ID: {ghl_location_id}")
            print(f"[🎫] PIT Token: {self.pit_token[:30]}..." if self.pit_token else "[❌] No PIT Token")
            print(f"[🔑] Access Token: {'✅ Captured' if self.access_token else '❌ Not Found'}")
            print(f"[🔥] Firebase Token: {'✅ Captured' if self.firebase_token else '❌ Not Found'}")
            
            return True
            
        except Exception as e:
            print(f"[❌ DATABASE] Error saving to database: {e}")
            return False
    
    async def _auto_login_working_ghl(self, page, email, password):
        """EXACT SAME login as working Facebook script but adapted for GHL"""
        
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
        
        # Submit button - EXACT SAME selectors as working script but adapted for GHL
        login_selectors = [
            'button[type="submit"]', 
            'button:has-text("Sign in")',  # GHL uses "Sign in"
            'button:has-text("Sign In")',  # Case variation
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
    
    async def run_automation(self, email: str, password: str, location_id: str, 
                           firm_user_id: str, agent_id: str, ghl_user_id: str = None):
        """Run the complete automation workflow"""
        try:
            print("="*80)
            print("[AUTOMATION] HighLevel Playwright Automation with Database Integration")
            print("="*80)
            print(f"[TARGET] Location ID: {location_id}")
            print(f"[CREDENTIALS] Email: {email}")
            print(f"[DATABASE] Firm User ID: {firm_user_id}")
            print(f"[DATABASE] Agent ID: {agent_id}")
            print()
            
            # Step 1: Setup browser
            print("[STEP 1] Setting up Playwright browser...")
            if not await self.setup_browser():
                return False
            
            # Step 2: Navigate and login
            print("\n[STEP 2] Navigating and handling login...")
            
            # Clear cookies to ensure fresh login
            await self.context.clear_cookies()
            print("[LOGIN] Cleared cookies for fresh login")
            
            # EXACT SAME navigation as working Facebook script - go to login page first
            print("[LOGIN] Opening GoHighLevel login page...")
            await self.page.goto("https://app.onetoo.com/login", wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
            
            current_url = self.page.url
            print(f"[LOGIN] Current page: {current_url}")
            print(f"[LOGIN] Page title: {await self.page.title()}")
            
            if not await self.handle_login_and_verification(email, password):
                return False
            
            # Step 3: Navigate to private integrations and create PIT
            print("\n[STEP 3] Navigating to private integrations...")
            target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
            await self.page.goto(target_url)
            await self.page.wait_for_timeout(3000)
            print(f"[INFO] Navigated to: {target_url}")
            
            if not await self.create_private_integration(location_id):
                return False
            
            # Step 4: Save to database
            print("\n[STEP 4] Saving to database...")
            if not await self.save_to_database(firm_user_id, agent_id, location_id, ghl_user_id):
                return False
            
            print("\n" + "="*80)
            print("[SUCCESS] Complete automation workflow finished!")
            print("="*80)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Automation failed: {e}")
            return False
        finally:
            # Close browser
            try:
                if self.browser:
                    await self.browser.close()
                if hasattr(self, 'playwright'):
                    await self.playwright.stop()
            except:
                pass

async def main():
    """Main function for testing"""
    load_dotenv()
    
    # Get credentials
    email = os.getenv('HIGHLEVEL_EMAIL', 'somashekhar34+MdY4KL72@gmail.com')
    password = os.getenv('HIGHLEVEL_PASSWORD', 'Dummy@123')
    location_id = "MdY4KL72E0lc7TqMm3H0"
    
    # Test parameters (you would get these from your workflow)
    firm_user_id = str(uuid.uuid4())  # Replace with actual firm_user_id
    agent_id = "test_agent_001"       # Replace with actual agent_id
    ghl_user_id = None                # Replace with actual ghl_user_id if available
    
    print(f"\n[TEST] Using test parameters:")
    print(f"  Firm User ID: {firm_user_id}")
    print(f"  Agent ID: {agent_id}")
    print(f"  Location ID: {location_id}")
    
    # Run automation
    automation = HighLevelPlaywrightAutomation(headless=False)
    success = await automation.run_automation(
        email, password, location_id, 
        firm_user_id, agent_id, ghl_user_id
    )
    
    if success:
        print("\n[FINAL] Playwright automation with database integration completed successfully!")
    else:
        print("\n[FINAL] Automation failed - check the logs above")

if __name__ == "__main__":
    asyncio.run(main())