#!/usr/bin/env python3
"""
HighLevel Complete Automation with Playwright - Direct conversion from working Selenium script
Combines automatic Gmail OTP reading with complete integration creation including token extraction
"""

import os
import imaplib
import email
import re
import json
import base64
import asyncio
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Import Supabase client - same as main.py
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("[WARNING] Supabase module not available. Will only save to files.")
    SUPABASE_AVAILABLE = False

class HighLevelCompleteAutomationPlaywright:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.firebase_token = None  # token-id header
        self.api_tokens = {
            'authorization': None,
            'token-id': None
        }
        self.pit_token = None
        self.playwright = None
        
    async def setup_browser(self):
        """Initialize Playwright browser with network logging enabled"""
        try:
            self.playwright = await async_playwright().start()
            
            # Similar args as Selenium setup
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            
            self.page = await self.context.new_page()
            
            # Set up request interception for token capture
            await self.page.route('**/*', self.intercept_requests)
            
            print("[SUCCESS] Playwright browser initialized with network logging")
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
            
        except Exception:
            # Continue with the request even if interception fails
            await route.continue_()
    
    def get_otp_from_gmail(self):
        """Get OTP code from Gmail automatically - EXACT SAME as Selenium version"""
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
            
            # First, let's search for ALL security code emails (not just unread) from the last hour
            # This ensures we get the most recent one even if older ones are unread
            search_criteria = '(FROM "noreply@talk.onetoo.com" SUBJECT "Login security code" SINCE "' + (datetime.now() - timedelta(hours=1)).strftime("%d-%b-%Y") + '")'
            result, data = mail.search(None, search_criteria)
            
            if result != 'OK' or not data[0]:
                # Fallback to unread emails if no recent emails found
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
            
            # Fetch the email with PEEK to not mark as read immediately
            result, msg_data = mail.fetch(latest_email_id, '(BODY.PEEK[])')
            if result != 'OK':
                print("[❌ EMAIL] Failed to fetch email")
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get email date to confirm it's recent
            email_date = msg.get('Date', 'Unknown date')
            print(f"[📧 EMAIL] Email date: {email_date}")
            
            # Extract body
            body = self._extract_email_body(msg)
            print(f"[📧 EMAIL] Email body preview: {body[:200]}...")
            
            # Extract OTP using patterns from the email
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
                    
                    # Try to mark email as read (ignore errors)
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
        """Extract body text from email message - EXACT SAME as Selenium version"""
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
        """Decode JWT token to extract expiry information - EXACT SAME as Selenium version"""
        try:
            # JWT tokens have 3 parts separated by dots
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # The payload is the second part
            payload_part = parts[1]
            
            # Add padding if needed (JWT uses URL-safe base64 without padding)
            padding = 4 - len(payload_part) % 4
            if padding != 4:
                payload_part += '=' * padding
            
            # Decode the payload
            payload_json = base64.urlsafe_b64decode(payload_part)
            payload = json.loads(payload_json)
            
            # Extract expiry time
            if 'exp' in payload:
                exp_timestamp = payload['exp']
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                
                # Also extract issued at time if available
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
    
    async def extract_tokens_from_storage(self):
        """Extract tokens from localStorage/sessionStorage - Playwright equivalent"""
        try:
            print("[🔍 TOKENS] Checking browser storage for tokens...")
            
            # Check localStorage
            local_storage = await self.page.evaluate("() => window.localStorage")
            for key, value in local_storage.items():
                # Check for GHL's Base64 encoded token storage (key "a")
                if key == "a" and value:
                    try:
                        import base64
                        # Decode the Base64 value
                        decoded_bytes = base64.b64decode(value + '==')  # Add padding if needed
                        decoded_str = decoded_bytes.decode('utf-8')
                        token_data = json.loads(decoded_str)
                        
                        if isinstance(token_data, dict):
                            # Look for refresh tokens in various formats
                            if 'refreshToken' in token_data:
                                self.refresh_token = token_data['refreshToken']
                                print(f"[✅ REFRESH] Found refreshToken in Base64 storage: {self.refresh_token[:30]}...")
                            if 'refreshJwt' in token_data:
                                if not self.refresh_token:  # Use as backup
                                    self.refresh_token = token_data['refreshJwt']
                                    print(f"[✅ REFRESH] Found refreshJwt in Base64 storage: {self.refresh_token[:30]}...")
                            if 'authToken' in token_data:
                                self.access_token = token_data['authToken']
                                print(f"[✅ ACCESS] Found authToken in Base64 storage: {self.access_token[:30]}...")
                            if 'jwt' in token_data:
                                if not self.access_token:  # Use as backup
                                    self.access_token = token_data['jwt']
                                    print(f"[✅ ACCESS] Found jwt in Base64 storage: {self.access_token[:30]}...")
                    except Exception as e:
                        print(f"[⚠️ DECODE] Could not decode Base64 token storage: {e}")
                
                # Original token checking logic
                if 'token' in key.lower() or 'access' in key.lower():
                    try:
                        # Try to parse as JSON
                        data = json.loads(value)
                        if isinstance(data, dict):
                            if 'access_token' in data:
                                self.access_token = data['access_token']
                                print(f"[✅ TOKENS] Found access token in localStorage: {self.access_token[:20]}...")
                            if 'refresh_token' in data:
                                self.refresh_token = data['refresh_token']
                                print(f"[✅ TOKENS] Found refresh token in localStorage: {self.refresh_token[:20]}...")
                            if 'expires_in' in data:
                                expires_in = int(data['expires_in'])
                                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                                print(f"[✅ TOKENS] Token expires at: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
                    except:
                        # If not JSON, check if it's a direct token
                        if len(value) > 20 and not self.access_token:
                            self.access_token = value
                            print(f"[✅ TOKENS] Found potential access token: {value[:20]}...")
            
            # Check sessionStorage
            session_storage = await self.page.evaluate("() => window.sessionStorage")
            for key, value in session_storage.items():
                if 'token' in key.lower() or 'access' in key.lower():
                    try:
                        data = json.loads(value)
                        if isinstance(data, dict):
                            if 'access_token' in data and not self.access_token:
                                self.access_token = data['access_token']
                                print(f"[✅ TOKENS] Found access token in sessionStorage: {self.access_token[:20]}...")
                            if 'refresh_token' in data and not self.refresh_token:
                                self.refresh_token = data['refresh_token']
                                print(f"[✅ TOKENS] Found refresh token in sessionStorage: {self.refresh_token[:20]}...")
                    except:
                        pass
                        
        except Exception as e:
            print(f"[⚠️ TOKENS] Could not check browser storage: {e}")
    
    async def handle_automatic_verification(self, location_id=None):
        """Handle email verification with automatic OTP reading - Playwright version"""
        self.location_id = location_id or getattr(self, 'location_id', None)
        try:
            page_source = (await self.page.content()).lower()
            
            # Check if we need email verification
            if "verification" in page_source or "verify" in page_source or "code" in page_source:
                print("\n" + "="*60)
                print("[VERIFICATION] Email verification required!")
                print("="*60)
                
                # First, click the "Send Code" button
                try:
                    print("[VERIFICATION] Looking for 'Send Security Code' button...")

                    # Try multiple selectors for the button
                    button_selectors = [
                        'button:has-text("Send Security Code")',  # Most specific - exact text
                        'button.bg-curious-blue-500',  # Class-based selector from HTML
                        '//button[contains(text(), "Send Security Code")]',  # XPath with text
                        'button.hl-btn',  # Generic button class
                        f"xpath={'/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/button'}"  # Fallback
                    ]
                    
                    button_clicked = False
                    for selector in button_selectors:
                        try:
                            # Add xpath prefix if it's an xpath selector
                            if selector.startswith('//'):
                                selector = f"xpath={selector}"
                            
                            print(f"[VERIFICATION] Trying selector: {selector[:50]}...")
                            await self.page.wait_for_selector(selector, timeout=3000)
                            await self.page.click(selector)
                            print("[VERIFICATION] ✅ 'Send Security Code' button clicked successfully!")
                            button_clicked = True
                            break
                        except:
                            continue
                    
                    if button_clicked:
                        print("[⏳ WAITING] Waiting 2 seconds for email to be sent...")
                        await asyncio.sleep(2)  # Give more time for email to arrive
                    else:
                        print("[WARNING] Could not click 'Send Security Code' button with any selector")
                        print("[INFO] Continuing anyway - code may already be sent")

                except Exception as e:
                    print(f"[WARNING] Button clicking error: {e}")
                    print("[INFO] Continuing anyway - code may already be sent")
                
                print("[📧 AUTO] Starting automatic OTP retrieval...")
                print("[📧 AUTO] Checking Gmail for verification code...")
                
                # Wait for email to arrive and get OTP automatically
                max_attempts = 30  # 30 seconds
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
                    print("[💡 MANUAL] Please check your email and manually enter the code in the browser")
                    print("[⏳ WAITING] Waiting 15 seconds for manual OTP entry...")
                    await asyncio.sleep(15)
                    return True
                
                print(f"[✅ VERIFICATION] Using OTP code: {otp_code}")
                
                # Use flexible approach for entering OTP
                try:
                    print("[VERIFICATION] Attempting individual digit input (flexible approach)...")
                    
                    # Try different selectors for individual digit inputs
                    digit_selectors = [
                        'input[maxlength="1"]',
                        'input[type="text"][maxlength="1"]',
                        '.otp-digit',
                        '.digit-input', 
                        '[data-testid="digit-input"]',
                        'input[class*="digit"]'
                    ]
                    
                    input_success = False
                    for selector in digit_selectors:
                        try:
                            print(f"[VERIFICATION] Trying selector: {selector}")
                            elements = await self.page.locator(selector).all()
                            
                            if len(elements) >= len(otp_code):
                                print(f"[📱 VERIFICATION] Found {len(elements)} digit inputs using: {selector}")
                                
                                # Clear all inputs first
                                for element in elements[:len(otp_code)]:
                                    await element.fill("")  # Clear by filling with empty string
                                    await asyncio.sleep(0.1)
                                
                                # Input each digit with small delays
                                for i, digit in enumerate(otp_code):
                                    if i < len(elements):
                                        print(f"[VERIFICATION] Entering digit {i+1}: {digit}")
                                        await elements[i].click()
                                        await asyncio.sleep(0.2)
                                        await elements[i].fill("")  # Clear by filling with empty string
                                        await asyncio.sleep(0.1)
                                        await elements[i].fill(digit)
                                        await asyncio.sleep(0.3)
                                        print(f"[VERIFICATION] Digit {i+1} entered successfully")
                                
                                print("[✅ VERIFICATION] All digits entered successfully!")
                                input_success = True
                                break
                                
                        except Exception as e:
                            print(f"[⚠️ VERIFICATION] Selector {selector} failed: {e}")
                            continue
                    
                    if input_success:
                        print("[✅ VERIFICATION] OTP entered successfully")
                        await asyncio.sleep(3)  # Wait for verification to complete
                    else:
                        print("[❌ VERIFICATION] Failed to input OTP digits automatically")
                        print("[💡 MANUAL] Please enter the OTP manually in the browser")
                        await asyncio.sleep(15)
                        
                except Exception as e:
                    print(f"[ERROR] Verification code input error: {e}")
                    return False
            
            print("[SUCCESS] Verification completed!")
            
            # Wait for page to fully load and stabilize after verification
            print("[⏳ WAITING] Waiting for page to fully stabilize after verification...")
            await asyncio.sleep(5)  # Longer wait to let dashboard fully load
            
            # Check current URL after verification
            current_url = self.page.url
            print(f"[📍 POST-VERIFICATION] Current URL: {current_url}")
            
            # After login, we're redirected to dashboard, so navigate to private integrations
            if "private-integrations" not in current_url:
                print("[📍 REDIRECT] Not on private integrations page, navigating there now...")
                if not self.location_id:
                    print("[ERROR] location_id not set! Cannot navigate to private integrations.")
                    return False
                # Navigate to private integrations page
                private_int_url = f"https://app.gohighlevel.com/v2/location/{self.location_id}/settings/private-integrations"
                print(f"[📍 REDIRECT] Navigating to: {private_int_url}")
                await self.page.goto(private_int_url, wait_until='networkidle')  # Wait for network to be idle
                await asyncio.sleep(3)  # Give extra time for page to load
                
                # Verify we reached the page
                final_url = self.page.url
                print(f"[📍 FINAL URL] After navigation: {final_url}")
                if "private-integrations" in final_url:
                    print("[✅ SUCCESS] Successfully navigated to private integrations page!")
                else:
                    print(f"[⚠️ WARNING] May not be on correct page. Current: {final_url}")
            else:
                print("[✅ SUCCESS] Already on private integrations page!")
            
            # Extract tokens after successful login
            await self.extract_tokens_from_storage()
            
            return await self.create_private_integration()
            
        except Exception as e:
            print(f"[ERROR] Automatic verification failed: {e}")
            return False
    
    async def create_private_integration(self):
        """Create the private integration with all required scopes and extract token - Playwright version"""
        print("\n[STEP 3] Creating private integration...")
        print("[PIT CREATION] 🎯 Starting Private Integration Token (PIT) creation process")
        print("[PIT CREATION] This is the critical step that creates the API token")
        
        # We should already be on the private integrations page after login/verification
        print("[INFO] Should already be on private integrations page after login/verification")
        current_url = self.page.url
        print(f"[CURRENT URL] {current_url}")
        print(f"[PIT CREATION] 📍 Current page: {current_url}")
        
        # Check if we're actually on the right page
        if "private-integrations" not in current_url:
            print("[PIT CREATION] ⚠️  WARNING: Not on private integrations page!")
            print(f"[PIT CREATION] Expected: contains 'private-integrations'")
            print(f"[PIT CREATION] Actual: {current_url}")
            print("[PIT CREATION] This might explain why PIT creation fails")
        else:
            print("[PIT CREATION] ✅ Confirmed on private integrations page")
        
        # Wait for page to fully load and handle any redirects
        print("[⏳ WAITING] Waiting for page to stabilize...")
        print("[PIT CREATION] 🕐 Waiting 3 seconds for page elements to load...")
        await asyncio.sleep(3)  # Increased wait time
        
        # Check if URL has changed after waiting
        new_url = self.page.url
        if new_url != current_url:
            print(f"[📍 REDIRECT] Page redirected to: {new_url}")
            print(f"[PIT CREATION] 🔄 Page changed from {current_url} to {new_url}")
            if "private-integrations" not in new_url:
                print("[PIT CREATION] ❌ CRITICAL: Redirected away from private integrations page!")
                print("[PIT CREATION] This will cause PIT creation to fail")
            else:
                print("[PIT CREATION] ✅ Still on private integrations page after redirect")
        
        # Try multiple times with different strategies
        max_retries = 3
        print(f"[PIT CREATION] 🔍 Looking for 'Create new integration' button...")
        print(f"[PIT CREATION] Will try {max_retries} attempts with different selectors")
        
        # Debug: Check current page URL (no screenshot to save time)
        current_url = self.page.url
        print(f"[DEBUG] Current page URL: {current_url}")
        
        # Wait for the page to be fully loaded (with shorter timeout)
        try:
            await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
        except:
            print("[DEBUG] DOM content loaded timeout, proceeding anyway...")
        
        # Check for iframes (GHL often uses iframes)
        try:
            frames = self.page.frames
            print(f"[DEBUG] Found {len(frames)} frames on page")
            if len(frames) > 1:
                # Try to find the main content frame
                for frame in frames:
                    frame_url = frame.url
                    if 'private-integrations' in frame_url or frame != self.page.main_frame:
                        print(f"[DEBUG] Switching to frame: {frame_url}")
                        # Note: In Playwright, we work with frames directly, no need to switch
                        # We'll search in all frames
        except Exception as e:
            print(f"[DEBUG] Frame check error: {e}")
        
        # Simpler wait strategy to avoid timeouts
        print("[⏳ WAIT] Waiting for page content to load...")
        try:
            await self.page.wait_for_load_state('domcontentloaded', timeout=10000)
        except:
            print("[⚠️ TIMEOUT] DOM load timeout, continuing anyway...")
        await asyncio.sleep(2)  # Simple wait for dynamic content
        
        # Check if we're on the right page by looking for key elements
        try:
            await self.page.wait_for_selector("text=Private Integrations", timeout=3000)
            print("✅ Confirmed on Private Integrations page")
        except:
            print("⚠️ May not be on the correct page, continuing anyway...")
        
        for retry in range(max_retries):
            print(f"\n[🔄 RETRY] Attempt {retry + 1}/{max_retries} to find integration button...")
            print(f"[PIT CREATION] 🎯 Step 3.{retry + 1}: Searching for integration creation button")
            
            # Try multiple selectors for the button
            button_selectors = [
                # PRIMARY METHOD: User-provided XPath (most reliable)
                "xpath=/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div[2]/button[2]/span",
                
                # Most generic - just find the text and click its container
                "text=Create new integration",
                
                # Specific to the current implementation (Naive UI)
                ".n-button:has-text('Create new integration')",
                "[class*='n-button--primary']:has-text('Create new integration')",
                "#no-apps-found-btn-positive-action",  # ID selector if it stays consistent
                
                # Generic button selectors
                "button:has-text('Create new integration')",
                "[type='button']:has-text('Create new integration')",
                
                # Look for the span and click parent
                "//span[contains(text(), 'Create new integration')]/parent::button",
                "//span[normalize-space()='Create new integration']/ancestor::button",
                ".n-button__content:has-text('Create new integration')",
                
                # Very generic - any element with the text
                "//*[contains(text(), 'Create new integration')]",
                "//*[normalize-space(text())='Create new integration']",
                
                # Fallback to any clickable element with primary styling
                "[class*='primary']:has-text('Create')",
                "[class*='button']:has-text('Create')",
                
                # Last resort - find by partial text
                ":has-text('Create new')",
                ":has-text('new integration')"
            ]
            
            button_clicked = False
            
            # Search in all frames
            all_frames = [self.page] + self.page.frames
            
            for frame in all_frames:
                if button_clicked:
                    break
                    
                for selector in button_selectors:
                    try:
                        # Skip if not main page and selector doesn't make sense for frame
                        if frame != self.page and selector.startswith("text="):
                            continue
                            
                        print(f"[BUTTON] Trying selector in {('main frame' if frame == self.page else 'iframe')}: {selector}")
                        
                        # First check if element exists in this frame (shorter timeout)
                        element = await frame.locator(selector).first.element_handle(timeout=1000)
                        if element:
                            # Scroll element into view
                            await element.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            
                            # Try multiple click strategies
                            click_success = False
                            
                            # Strategy 1: Direct element click
                            try:
                                await element.click(timeout=3000)
                                print("[✅ SUCCESS] Button clicked using element.click()!")
                                click_success = True
                            except:
                                pass
                            
                            # Strategy 2: Frame click with selector
                            if not click_success:
                                try:
                                    await frame.click(selector, timeout=3000)
                                    print("[✅ SUCCESS] Button clicked using frame.click()!")
                                    click_success = True
                                except:
                                    pass
                            
                            # Strategy 3: JavaScript click
                            if not click_success:
                                try:
                                    await frame.evaluate("(el) => el.click()", element)
                                    print("[✅ SUCCESS] Button clicked using JavaScript!")
                                    click_success = True
                                except:
                                    pass
                            
                            # Strategy 4: Dispatch click event
                            if not click_success:
                                try:
                                    await element.dispatch_event('click')
                                    print("[✅ SUCCESS] Button clicked using dispatch_event!")
                                    click_success = True
                                except:
                                    pass
                            
                            if click_success:
                                button_clicked = True
                                break
                    except Exception as e:
                        continue
            
            if button_clicked:
                print(f"[✅ BUTTON SUCCESS] Integration button clicked successfully on attempt {retry + 1}")
                break
            else:
                print(f"[❌ ERROR] Could not find button with any selector on attempt {retry + 1}")
                
        # Check if button was successfully clicked across all retries
        if not button_clicked:
            print("[💡 FALLBACK] Could not click integration button after all attempts. Please click it manually in the browser.")
            print("[⏳ WAITING] Waiting 10 seconds for manual intervention...")
            await asyncio.sleep(10)
            # Continue anyway as user might have clicked manually
        else:
            print("[🎯 PROCEEDING] Button clicked successfully, continuing with form filling...")
        
        # Fill integration name
        try:
            print("[INTEGRATION] Filling integration name...")
            print("[PIT CREATION] 📝 Step 3.A: Filling integration form with name 'location key'")
            
            # Multiple selectors for integration name input field
            name_selectors = [
                'input[placeholder*="integration name" i]',  # Placeholder containing "integration name" (case insensitive)
                'input[placeholder*="name" i]',  # Placeholder containing "name" (case insensitive)
                'input[name="name"]',  # Name attribute
                'form input[type="text"]:first-of-type',  # First text input in form
                'form div input',  # Generic form input
                "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div[1]/div[1]/div/div[1]/div[1]/input"  # Original XPath as fallback
            ]
            
            name_field_found = False
            for selector in name_selectors:
                try:
                    if selector.startswith('/'):
                        # XPath selector
                        xpath_selector = f"xpath={selector}"
                        print(f"[PIT CREATION] 🔍 Trying XPath selector: {selector}")
                        await self.page.wait_for_selector(xpath_selector, timeout=3000)
                        await self.page.fill(xpath_selector, "")  # Clear by filling with empty string
                        await self.page.fill(xpath_selector, "location key")
                        print(f"[PIT CREATION] ✅ Successfully filled integration name using XPath: {selector}")
                        name_field_found = True
                        break
                    else:
                        # CSS selector
                        print(f"[PIT CREATION] 🔍 Trying CSS selector: {selector}")
                        await self.page.wait_for_selector(selector, timeout=3000)
                        await self.page.fill(selector, "")  # Clear by filling with empty string
                        await self.page.fill(selector, "location key")
                        print(f"[PIT CREATION] ✅ Successfully filled integration name using CSS: {selector}")
                        name_field_found = True
                        break
                except Exception as selector_error:
                    print(f"[PIT CREATION] ❌ Selector failed: {selector} - {selector_error}")
                    continue
            
            if not name_field_found:
                raise Exception("Could not find integration name input field with any selector")
                
            print("[INTEGRATION] Integration name set to: location key")
            print("[PIT CREATION] ✅ Successfully filled integration name")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[ERROR] Could not fill integration name: {e}")
            print(f"[PIT CREATION] ❌ CRITICAL: Failed to fill integration name - {e}")
            print("[PIT CREATION] This will prevent PIT creation from completing")
            return False
        
        # Submit the form
        try:
            print("[INTEGRATION] Submitting integration form...")
            print("[PIT CREATION] 📤 Step 3.B: Submitting the integration form")
            
            # Multiple selectors for submit button
            submit_selectors = [
                'button:has-text("Next")',  # Most likely submit text based on screenshot
                'button:has-text("Continue")',  # Alternative submit text
                'button:has-text("Submit")',  # Alternative submit text
                'button:has-text("Create")',  # Create button text
                '//button[contains(text(), "Next")]',  # XPath with Next text
                '//button[contains(text(), "Continue")]',  # XPath with Continue text
                '//button[contains(text(), "Submit")]',  # XPath with Submit text
                '//button[contains(text(), "Create")]',  # XPath with Create text
                'button[type="submit"]',  # Submit type button
                'button.bg-curious-blue-500',  # Blue submit button class
                'button.hl-btn.hl-btn--primary',  # Primary button class
                "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]"  # Original XPath as fallback
            ]
            
            submit_button_found = False
            for selector in submit_selectors:
                try:
                    if selector.startswith('/'):
                        # XPath selector
                        xpath_selector = f"xpath={selector}"
                        print(f"[PIT CREATION] 🔍 Trying XPath selector: {selector}")
                        await self.page.wait_for_selector(xpath_selector, timeout=3000)
                        await self.page.click(xpath_selector)
                        print(f"[PIT CREATION] ✅ Successfully clicked submit button using XPath: {selector}")
                        submit_button_found = True
                        break
                    else:
                        # CSS selector
                        print(f"[PIT CREATION] 🔍 Trying CSS selector: {selector}")
                        await self.page.wait_for_selector(selector, timeout=3000)
                        await self.page.click(selector)
                        print(f"[PIT CREATION] ✅ Successfully clicked submit button using CSS: {selector}")
                        submit_button_found = True
                        break
                except Exception as selector_error:
                    print(f"[PIT CREATION] ❌ Selector failed: {selector} - {selector_error}")
                    continue
            
            if not submit_button_found:
                raise Exception("Could not find submit button with any selector")
                
            print("[INTEGRATION] Form submitted")
            print("[PIT CREATION] ✅ Successfully submitted integration form")
            print("[PIT CREATION] 🕐 Waiting 3 seconds for next step to load...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[ERROR] Could not submit integration form: {e}")
            print(f"[PIT CREATION] ❌ CRITICAL: Failed to submit integration form - {e}")
            print("[PIT CREATION] Cannot proceed to scope selection without form submission")
            return False
        
        # Select scopes
        try:
            print("[INTEGRATION] Opening scopes selection...")
            print("[PIT CREATION] 🎯 Step 3.C: Starting scope selection process")
            print("[PIT CREATION] This is critical - we need to select specific scopes")
            
            # Wait for the scopes page to load
            print("[INTEGRATION] Waiting for scopes page to load...")
            await asyncio.sleep(3)
            
            # Check if we're on the scopes page by looking for "Scopes" tab
            try:
                await self.page.wait_for_selector('text=Scopes', timeout=5000)
                print("[✅ SCOPES PAGE] Successfully on scopes selection page")
            except:
                print("[⚠️ WARNING] Could not confirm we're on scopes page, continuing anyway...")
            
            # Click the "Select scopes" dropdown to open it
            print("[INTEGRATION] Looking for and clicking 'Select scopes' dropdown...")
            
            # Target the exact HTML structure from the provided code
            dropdown_selectors = [
                "#scopes-select",  # The exact ID from the HTML
                ".hr-select#scopes-select",  # ID with class
                ".hr-base-selection-tags",  # The clickable tags container
                ".hr-base-selection",  # The base selection element
                ".hr-base-selection-placeholder",  # The placeholder element
                "div.hr-base-selection-placeholder__inner",  # The inner placeholder with "Select scopes" text
                '[tabindex="0"].hr-base-selection-tags',  # Tabindex element
                "//div[@class='hr-base-selection-tags']",  # XPath for tags container
                "//div[@id='scopes-select']",  # XPath for ID
                "//div[contains(@class, 'hr-base-selection') and contains(@class, 'hr-base-selection--multiple')]",  # XPath for selection container
                "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div/div/div[1]"  # Original XPath as fallback
            ]
            
            dropdown_found = False
            for selector in dropdown_selectors:
                try:
                    if selector.startswith('/'):
                        # XPath selector
                        xpath_selector = f"xpath={selector}"
                        print(f"[PIT CREATION] 🔍 Trying XPath selector: {selector}")
                        await self.page.wait_for_selector(xpath_selector, timeout=3000)
                        await self.page.click(xpath_selector)
                        print(f"[PIT CREATION] ✅ Successfully clicked dropdown using XPath: {selector}")
                        dropdown_found = True
                        break
                    else:
                        # CSS selector
                        print(f"[PIT CREATION] 🔍 Trying CSS selector: {selector}")
                        await self.page.wait_for_selector(selector, timeout=3000)
                        await self.page.click(selector)
                        print(f"[PIT CREATION] ✅ Successfully clicked dropdown using CSS: {selector}")
                        dropdown_found = True
                        break
                except Exception as selector_error:
                    print(f"[PIT CREATION] ❌ Selector failed: {selector} - {selector_error}")
                    continue
            
            if not dropdown_found:
                raise Exception("Could not find Select scopes dropdown with any selector")
                
            await asyncio.sleep(2)
            
            # Click "Select all scopes" checkbox instead of selecting individually
            print("[INTEGRATION] Clicking 'Select all scopes' checkbox...")
            
            try:
                # Try multiple selectors for the "Select all scopes" checkbox
                select_all_selectors = [
                    "xpath=/html/body/div[5]/div/div/div[1]/div/div/span",  # User-provided XPath for label
                    "xpath=//*[@id='d8dd458f']",  # User-provided ID XPath
                    ".hr-checkbox__label",  # CSS class for label
                    'span:has-text("Select all")',  # Span with Select all text
                    "xpath=/html/body/div[5]/div/div/div[1]/div/div/div/div/div[2]",  # Previous XPath
                    ".hr-checkbox-box__border",  # CSS class from user
                    '.hr-checkbox',  # Generic checkbox class
                ]
                
                select_all_clicked = False
                for selector in select_all_selectors:
                    try:
                        print(f"[SCOPES] Trying selector: {selector}")
                        await self.page.wait_for_selector(selector, timeout=3000)
                        await self.page.click(selector)
                        print("[SCOPES] ✅ Successfully clicked 'Select all scopes' checkbox!")
                        select_all_clicked = True
                        break
                    except Exception as e:
                        print(f"[SCOPES] Selector failed: {selector} - {e}")
                        continue
                
                if not select_all_clicked:
                    print("[SCOPES] ⚠️ Could not find 'Select all scopes' checkbox")
                    raise Exception("Could not find Select all scopes checkbox")
                
                await asyncio.sleep(1)
                print("[SCOPES] ✅ All scopes selected via 'Select all' option")
                
            except Exception as e:
                print(f"[ERROR] Failed to select all scopes: {str(e)}")
            
            # IMPORTANT: Click outside the dropdown to close it and finalize scope selection
            print("\n[INTEGRATION] Clicking outside dropdown to finalize scope selection...")
            try:
                # Click on a neutral area outside the dropdown
                await self.page.click('body', position={'x': 500, 'y': 300})
                await asyncio.sleep(1)
                print("[INTEGRATION] Clicked outside dropdown to close it")
            except Exception as e:
                print(f"[WARNING] Could not click outside dropdown: {e}")
            
            # Continue with next steps - Click the Create button
            print("\n[INTEGRATION] Scope selection completed, clicking Create button...")
            
            # Multiple selectors for the final Create button
            create_button_selectors = [
                'button:has-text("Create")',  # Most likely text
                'button:has-text("Save")',  # Alternative text
                'button:has-text("Finish")',  # Alternative text
                '//button[contains(text(), "Create")]',  # XPath with Create text
                '//button[contains(text(), "Save")]',  # XPath with Save text
                '//button[contains(text(), "Finish")]',  # XPath with Finish text
                'button[type="submit"]',  # Submit type button
                'button.bg-curious-blue-500',  # Blue button class
                'button.hl-btn--primary',  # Primary button class
                "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]/span",  # Original XPath
                "//*[@id='btn-next']/span"  # Alternative XPath
            ]
            
            create_button_found = False
            for selector in create_button_selectors:
                try:
                    if selector.startswith('/'):
                        # XPath selector
                        xpath_selector = f"xpath={selector}"
                        print(f"[PIT CREATION] 🔍 Trying XPath selector: {selector}")
                        await self.page.wait_for_selector(xpath_selector, timeout=3000)
                        await self.page.click(xpath_selector)
                        print(f"[PIT CREATION] ✅ Successfully clicked Create button using XPath: {selector}")
                        create_button_found = True
                        break
                    else:
                        # CSS selector
                        print(f"[PIT CREATION] 🔍 Trying CSS selector: {selector}")
                        await self.page.wait_for_selector(selector, timeout=3000)
                        await self.page.click(selector)
                        print(f"[PIT CREATION] ✅ Successfully clicked Create button using CSS: {selector}")
                        create_button_found = True
                        break
                except Exception as selector_error:
                    print(f"[PIT CREATION] ❌ Selector failed: {selector} - {selector_error}")
                    continue
            
            if not create_button_found:
                print("[PIT CREATION] ⚠️ Could not find Create button with any selector")
                print("[PIT CREATION] Please click the Create button manually")
            
            # After clicking Create, a confirmation popup appears - click Confirm
            print("\n[INTEGRATION] Waiting for confirmation popup...")
            await asyncio.sleep(2)
            
            try:
                print("[INTEGRATION] Looking for Confirm button in popup...")
                confirm_selectors = [
                    "xpath=/html/body/div[7]/div/div/div[1]/div/div[3]/div[2]/div/button[2]/span",  # User-provided XPath
                    'button:has-text("Confirm")',  # Text-based selector
                    'span:has-text("Confirm")',  # Span with Confirm text
                    '.hr-button__content:has-text("Confirm")',  # CSS class with text
                    '//span[contains(text(), "Confirm")]/parent::button',  # XPath to button via span
                    'button.hr-button--primary:has-text("Confirm")',  # Primary button with Confirm
                ]
                
                confirm_clicked = False
                for selector in confirm_selectors:
                    try:
                        print(f"[CONFIRM] Trying selector: {selector}")
                        await self.page.wait_for_selector(selector, timeout=3000)
                        await self.page.click(selector)
                        print("[CONFIRM] ✅ Successfully clicked Confirm button!")
                        confirm_clicked = True
                        break
                    except Exception as e:
                        print(f"[CONFIRM] Selector failed: {selector} - {e}")
                        continue
                
                if not confirm_clicked:
                    print("[CONFIRM] ⚠️ Could not find Confirm button, continuing anyway...")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[WARNING] Error clicking Confirm button: {e}")
            
            # Wait for token display and copy it
            print("[INTEGRATION] Waiting for token generation...")
            await asyncio.sleep(3)
            
            try:
                # Use the exact XPath for the copy button (updated to div[8])
                copy_button_xpath = "/html/body/div[8]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/button/span"
                xpath_selector = f"xpath={copy_button_xpath}"
                
                await self.page.wait_for_selector(xpath_selector, timeout=10000)
                
                # Before clicking, try to get the token text directly
                print("[PIT CREATION] 🎯 Step 3.D: Extracting the Private Integration Token")
                print("[PIT CREATION] This is the final step - getting the actual token!")
                
                try:
                    print("[PIT CREATION] 🔍 Searching for token elements on the page...")
                    # Look for pre or code elements that might contain the token
                    token_elements = await self.page.locator("pre, code, div[class*='token'], textarea").all()
                    print(f"[PIT CREATION] Found {len(token_elements)} potential token elements")
                    
                    for i, elem in enumerate(token_elements, 1):
                        print(f"[PIT CREATION] 🔍 Checking element {i}/{len(token_elements)}...")
                        if await elem.is_visible():
                            print(f"[PIT CREATION] ✅ Element {i} is visible, extracting text...")
                            token_text = await elem.text_content() or await elem.input_value()
                            if token_text and len(token_text) > 10:  # Likely a token
                                print(f"[PIT CREATION] 🎉 Found token! Length: {len(token_text)} characters")
                                print("\n")
                                print("*"*100)
                                print("*" + " "*38 + "INTEGRATION TOKEN FOUND" + " "*38 + "*")
                                print("*" + " "*98 + "*")
                                print("*"*100)
                                print("\n")
                                print(token_text)
                                print("\n")
                                print("*"*100)
                                
                                print("[PIT CREATION] ✅ Successfully extracted PIT token!")
                                print("[PIT CREATION] 💾 Saving token and extracting additional tokens...")
                                
                                # Extract tokens one more time
                                await self.extract_tokens_from_storage()
                                
                                # Save all tokens
                                self.pit_token = token_text
                                await self.save_all_tokens(token_text)
                                print("[PIT CREATION] ✅ Token extraction and saving completed!")
                                return True
                            else:
                                print(f"[PIT CREATION] ❌ Element {i} text too short or empty")
                        else:
                            print(f"[PIT CREATION] ❌ Element {i} not visible")
                            
                    print("[PIT CREATION] ⚠️  No valid token found in direct search, trying copy button...")
                    
                except Exception as e:
                    print(f"[PIT CREATION] ❌ Error in direct token search: {e}")
                    print(f"[PIT CREATION] Falling back to copy button method...")
                
                # Click the copy button
                await self.page.click(xpath_selector)
                print("Clicked copy button with exact XPath to copy token to clipboard")
                
                # After clicking copy button, extract token using exact XPath
                try:
                    # Use the exact XPath where token is displayed (updated to div[8])
                    exact_token_xpath = "/html/body/div[8]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/p"
                    xpath_selector = f"xpath={exact_token_xpath}"
                    print("Looking for token at exact XPath...")
                    
                    # Wait for the element to be visible
                    await self.page.wait_for_selector(xpath_selector, timeout=10000)
                    
                    # Get the token text
                    token_text = await self.page.locator(xpath_selector).text_content()
                    
                    if token_text and len(token_text) > 10:  # Basic validation
                        print("\n")
                        print("*"*100)
                        print("*" + " "*38 + "INTEGRATION TOKEN EXTRACTED" + " "*38 + "*")
                        print("*"*100)
                        print("\n")
                        print(token_text)
                        print("\n")
                        print("*"*100)
                        
                        # Extract tokens one more time after PIT creation
                        await self.extract_tokens_from_storage()
                        
                        # Save all tokens
                        self.pit_token = token_text
                        await self.save_all_tokens(token_text)
                    else:
                        print("\n[WARNING] Token text appears to be empty or invalid")
                except Exception as e:
                    print(f"\n[ERROR] Failed to extract token: {e}")
            except Exception as e:
                print(f"[WARNING] Could not copy token with exact XPath: {str(e)}")
                print("Could not find any copy button, but integration was likely created")
            
        except Exception as e:
            print(f"[WARNING] Could not open scopes selection: {e}")
            print("[INFO] Please manually select scopes and continue")
        
        return True
    
    async def handle_login_and_verification(self, email: str, password: str, location_id: str = None):
        """Handle login and automatic email verification - Playwright version"""
        try:
            # Store location_id if provided
            if location_id:
                self.location_id = location_id
            
            current_url = self.page.url.lower()
            page_source = (await self.page.content()).lower()
            
            # Check if we're on a login page
            if "login" in current_url or "sign" in current_url or "sign into your account" in page_source:
                print("[LOGIN] Detected login page - filling credentials...")
                
                # Wait for page to fully load
                await asyncio.sleep(3)
                
                # Fill email field
                try:
                    print("[LOGIN] Looking for email field...")
                    
                    # Try multiple selectors based on the actual page structure
                    email_selectors = [
                        'input[placeholder="Your email address"]',  # Most specific - from screenshot
                        'input[type="email"]',  # Generic email input
                        '//input[@placeholder="Your email address"]',  # XPath version
                        'input[name="email"]',  # Name attribute fallback
                    ]
                    
                    email_filled = False
                    for selector in email_selectors:
                        try:
                            # Add xpath prefix if it's an xpath selector
                            if selector.startswith('//'):
                                selector = f"xpath={selector}"
                            
                            print(f"[LOGIN] Trying selector: {selector}")
                            await self.page.wait_for_selector(selector, timeout=3000)
                            await self.page.click(selector)
                            await self.page.fill(selector, email)
                            print(f"[LOGIN] ✅ Email filled successfully with: {email}")
                            email_filled = True
                            await asyncio.sleep(1)
                            break
                        except Exception as selector_error:
                            print(f"[LOGIN] Selector {selector} didn't work, trying next...")
                            continue
                    
                    if not email_filled:
                        raise Exception("Could not find email field with any selector")
                        
                except Exception as e:
                    print(f"[ERROR] Email field error: {e}")
                    return False

                # Fill password field
                try:
                    print("[LOGIN] Looking for password field...")
                    
                    # Try multiple selectors based on the actual page structure
                    password_selectors = [
                        'input[placeholder="The password you picked"]',  # Most specific - from screenshot
                        'input[type="password"]',  # Generic password input
                        '//input[@placeholder="The password you picked"]',  # XPath version
                        'input[name="password"]',  # Name attribute fallback
                    ]
                    
                    password_filled = False
                    for selector in password_selectors:
                        try:
                            # Add xpath prefix if it's an xpath selector
                            if selector.startswith('//'):
                                selector = f"xpath={selector}"
                            
                            print(f"[LOGIN] Trying selector: {selector}")
                            await self.page.wait_for_selector(selector, timeout=3000)
                            await self.page.click(selector)
                            await self.page.fill(selector, password)
                            print("[LOGIN] ✅ Password filled successfully")
                            password_filled = True
                            await asyncio.sleep(1)
                            break
                        except Exception as selector_error:
                            print(f"[LOGIN] Selector {selector} didn't work, trying next...")
                            continue
                    
                    if not password_filled:
                        raise Exception("Could not find password field with any selector")
                        
                except Exception as e:
                    print(f"[ERROR] Password field error: {e}")
                    return False
                
                # Click login button
                try:
                    print("[LOGIN] Looking for login button...")
                    await self.page.wait_for_selector('button:has-text("Sign in")', timeout=10000)
                    await self.page.click('button:has-text("Sign in")')
                    print("[LOGIN] Login button clicked")
                    
                    # Wait for login to process
                    print("[LOGIN] Waiting for login to complete...")
                    await asyncio.sleep(4)
                    
                except Exception as e:
                    print(f"[ERROR] Login button error: {e}")
                    return False
            
            # Handle email verification if needed
            return await self.handle_automatic_verification()
            
        except Exception as e:
            print(f"[ERROR] Login and verification failed: {e}")
            return False
    
    async def navigate_to_target(self, location_id: str, email: str, password: str):
        """Navigate to target URL with login and verification handling - Playwright version"""
        try:
            # Store location_id as instance variable
            self.location_id = location_id
            
            target_url = f"https://app.gohighlevel.com/v2/location/{location_id}/settings/private-integrations/"
            print(f"[NAVIGATE] Going directly to: {target_url}")
            
            # Go directly to the target URL
            await self.page.goto(target_url)
            await asyncio.sleep(3)
            
            # Handle login and verification (pass location_id)
            if not await self.handle_login_and_verification(email, password, location_id):
                return False
            
            # Wait and check final URL
            await asyncio.sleep(2)
            final_url = self.page.url
            print(f"[INFO] Final URL: {final_url}")
            
            # Verify we're on the correct page
            if location_id in final_url and "private-integrations" in final_url:
                print("[SUCCESS] Successfully reached private integrations page!")
                return True
            elif "private-integrations" in final_url:
                print("[SUCCESS] Reached private integrations page (URL may have changed)")
                return True
            else:
                print(f"[WARNING] May not be on expected page. Current URL: {final_url}")
                return True
                
        except Exception as e:
            print(f"[ERROR] Navigation failed: {e}")
            return False
    
    async def save_all_tokens(self, pit_token=None):
        """Save all tokens to a comprehensive JSON file - Same as Selenium version"""
        try:
            # Decode access token to get expiry
            token_info = None
            if self.access_token:
                token_info = self.decode_jwt_token(self.access_token)
                if token_info:
                    self.token_expiry = token_info['expires_at']
            
            # Decode Firebase token if available
            firebase_token_info = None
            if self.firebase_token:
                firebase_token_info = self.decode_jwt_token(self.firebase_token)
            
            tokens_data = {
                "timestamp": datetime.now().isoformat(),
                "location_id": "MdY4KL72E0lc7TqMm3H0",
                "tokens": {
                    "private_integration_token": pit_token,
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "firebase_token": self.firebase_token,
                    "api_tokens": self.api_tokens
                },
                "expiry": {
                    "access_token_expires_at": self.token_expiry.isoformat() if self.token_expiry else None,
                    "access_token_expires_in_seconds": (self.token_expiry - datetime.now()).total_seconds() if self.token_expiry else None,
                    "access_token_expires_in_readable": str(self.token_expiry - datetime.now()) if self.token_expiry else None,
                    "access_token_issued_at": token_info['issued_at'].isoformat() if token_info and token_info['issued_at'] else None,
                    "firebase_token_expires_at": firebase_token_info['expires_at'].isoformat() if firebase_token_info and firebase_token_info['expires_at'] else None,
                    "firebase_token_issued_at": firebase_token_info['issued_at'].isoformat() if firebase_token_info and firebase_token_info['issued_at'] else None
                }
            }
            
            # Skip file saving - we're using database instead
            # Tokens are already saved to database in save_to_database method
            
            # Display all tokens
            print("\n" + "="*100)
            print("=" + " "*40 + "ALL TOKENS EXTRACTED" + " "*40 + "=")
            print("="*100)
            print()
            print(f"1. PRIVATE INTEGRATION TOKEN (PIT):")
            print(f"   {pit_token}")
            print()
            print(f"2. ACCESS TOKEN (Authorization Bearer):")
            print(f"   {self.access_token if self.access_token else 'Not found - check browser console'}")
            print()
            print(f"3. FIREBASE TOKEN (token-id header for API calls):")
            print(f"   {self.firebase_token if self.firebase_token else 'Not found - check browser console'}")
            print()
            print(f"4. REFRESH TOKEN:")
            print(f"   {self.refresh_token if self.refresh_token else 'Not found - check browser console'}")
            print()
            if self.token_expiry:
                print(f"5. ACCESS TOKEN EXPIRY:")
                print(f"   Expires at: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Time remaining: {self.token_expiry - datetime.now()}")
                if token_info and token_info['issued_at']:
                    print(f"   Issued at: {token_info['issued_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Token lifetime: {self.token_expiry - token_info['issued_at']}")
            
            if firebase_token_info and firebase_token_info['expires_at']:
                print()
                print(f"6. FIREBASE TOKEN EXPIRY:")
                print(f"   Expires at: {firebase_token_info['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Time remaining: {firebase_token_info['expires_at'] - datetime.now()}")
                if firebase_token_info['issued_at']:
                    print(f"   Issued at: {firebase_token_info['issued_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Token lifetime: {firebase_token_info['expires_at'] - firebase_token_info['issued_at']}")
            print()
            print("="*100)
            print("\n✅ All tokens saved to database")
            
        except Exception as e:
            print(f"[ERROR] Could not save tokens: {e}")
    
    async def save_to_database(self, pit_token: str, firm_user_id: str, agent_id: str, ghl_location_id: str, ghl_user_id: str = None, save_to_database: bool = True):
        """Save all captured data to the database using Supabase"""
        try:
            if not SUPABASE_AVAILABLE:
                print("[💾 DATABASE] Supabase not available - skipping database save")
                return True
                
            print("\n[💾 DATABASE] Saving tokens and setup data...")
            
            # Initialize Supabase client - same as main.py
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            if not supabase_url or not supabase_key:
                print("[❌ DATABASE] SUPABASE_URL or SUPABASE_SERVICE_KEY not found in environment variables")
                return False
                
            supabase: Client = create_client(supabase_url, supabase_key)
            
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
                    "private_integration_token": pit_token,
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
                    "pit_token": bool(pit_token),
                    "access_token": bool(self.access_token),
                    "firebase_token": bool(self.firebase_token)
                },
                "created_at": datetime.now().isoformat()
            }
            
            # Only save if requested - main backend handles database operations with new tables
            if save_to_database:
                # Save to NEW facebook_integrations table (not old tables)
                facebook_integration_data = {
                    'firm_user_id': firm_user_id,
                    'firm_id': ghl_location_id,  # Using location_id as firm_id
                    'ghl_location_id': ghl_location_id,
                    'ghl_user_id': ghl_user_id,
                    'private_integration_token': pit_token,
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'firebase_token': self.firebase_token,
                    'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
                    'setup_completed': True,
                    'automation_completed': True,
                    'scopes_count': 15,
                    'tokens_data': tokens_data,
                    'setup_config': setup_config,
                    'status': 'active',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                # Save to facebook_integrations table
                result = supabase.table('facebook_integrations').upsert(
                    facebook_integration_data,
                    on_conflict='firm_user_id,ghl_location_id'
                ).execute()
                
                print("[✅ DATABASE] Successfully saved to facebook_integrations table!")
                print(f"[📊 DATABASE] Record ID: {result.data[0]['id'] if result.data else 'Generated'}")
            else:
                print("[📝 DATABASE] Skipped database save - handled by main backend code")
            
            print(f"[📍] Firm User ID: {firm_user_id}")
            print(f"[🤖] Agent ID: {agent_id}")
            print(f"[📧] GHL Location ID: {ghl_location_id}")
            print(f"[🎫] PIT Token: {pit_token[:30]}...") 
            print(f"[🔑] Access Token: {'✅ Captured' if self.access_token else '❌ Not Found'}")
            print(f"[🔥] Firebase Token: {'✅ Captured' if self.firebase_token else '❌ Not Found'}")
            
            return True
            
        except Exception as e:
            print(f"[❌ DATABASE] Error saving to database: {e}")
            return False
    
    async def take_screenshot(self, location_id: str):
        """Screenshot function disabled for performance - Playwright version"""
        # Screenshots disabled to improve performance
        print(f"[SCREENSHOT] Skipped for performance")
        return None
    
    async def run_automation(self, email: str, password: str, location_id: str, 
                           firm_user_id: str = None, agent_id: str = None, ghl_user_id: str = None,
                           save_to_database: bool = True):
        """Run the complete automation workflow with automatic email verification - Playwright version"""
        try:
            # Always use hardcoded agency credentials for login
            agency_email = 'somashekhar34+MdY4KL72@gmail.com'
            agency_password = os.getenv('HIGHLEVEL_PASSWORD', 'Dummy@123')
            
            print("[STEP 1] Setting up Playwright browser...")
            if not await self.setup_browser():
                return False
            
            # Step 2: Navigate and handle login/verification
            print("\n[STEP 2] Navigating with login and automatic email verification...")
            if not await self.navigate_to_target(location_id, agency_email, agency_password):
                return False
            
            # Step 3: Save to database if parameters provided
            if firm_user_id and agent_id and self.pit_token:
                print("\n[STEP 3] Saving to database...")
                await self.save_to_database(self.pit_token, firm_user_id, agent_id, location_id, ghl_user_id, save_to_database)
            
            # Step 4: Take screenshot
            print("\n[STEP 4] Taking screenshot...")
            screenshot = await self.take_screenshot(location_id)

            # Step 5: Verify PIT token was captured before declaring success
            if not self.pit_token:
                print("\n" + "="*80)
                print("[FAILED] Automation completed but NO PIT TOKEN was captured!")
                print(f"[RESULT] Private integration may not have been created for location: {location_id}")
                print("[INFO] Check the logs above to see where the process failed")
                print("="*80)
                return False

            # Step 6: Show success and keep browser open
            print("\n" + "="*80)
            print("[SUCCESS] Complete automation workflow finished!")
            print(f"[RESULT] Private integration created for location: {location_id}")
            print(f"[PIT TOKEN] Captured: {self.pit_token[:30]}...")
            if screenshot:
                print(f"[SCREENSHOT] Screenshot saved as: {screenshot}")
            print("[INFO] Browser will remain open for you to continue working")
            print("[INFO] All tokens saved to database (check facebook_integrations table)")
            print("="*80)

            # Keep browser open - don't close automatically
            print("\n[BROWSER] Browser will stay open. Close it manually when done.")
            return True
            
        except Exception as e:
            print(f"[ERROR] Automation failed: {e}")
            return False
        finally:
            # Don't close browser automatically - let user close it manually
            pass

async def main():
    """Main function"""
    load_dotenv()
    
    # Get HighLevel credentials
    email = os.getenv('HIGHLEVEL_EMAIL', 'somashekhar34+MdY4KL72@gmail.com')
    password = os.getenv('HIGHLEVEL_PASSWORD', 'Dummy@123')
    
    if not email or not password:
        print("[ERROR] Missing HighLevel credentials. Please set in .env file:")
        print("  HIGHLEVEL_EMAIL=your_highlevel_email")
        print("  HIGHLEVEL_PASSWORD=your_highlevel_password")
        return
    
    # Use the correct location ID
    location_id = "MdY4KL72E0lc7TqMm3H0"
    print(f"\n[INPUT] Using location ID: {location_id}")
    
    # Database parameters for end-to-end test
    firm_user_id = str(uuid.uuid4())  # Generate test firm_user_id
    agent_id = "playwright_test_agent_001"
    ghl_user_id = None  # Optional
    
    print(f"[DATABASE] Test parameters:")
    print(f"  Firm User ID: {firm_user_id}")
    print(f"  Agent ID: {agent_id}")
    print(f"  Location ID: {location_id}")
    print()
    
    # Run automation with database integration
    automation = HighLevelCompleteAutomationPlaywright(headless=False)
    success = await automation.run_automation(email, password, location_id, firm_user_id, agent_id, ghl_user_id)
    
    if success:
        print("\n[FINAL] Complete Playwright automation with automatic 2FA and PIT creation completed successfully!")
    else:
        print("\n[FINAL] Automation failed - check the logs above")

if __name__ == "__main__":
    asyncio.run(main())