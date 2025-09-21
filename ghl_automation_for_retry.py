#!/usr/bin/env python3
"""
HighLevel Automation for Retry - Token Capture Only
Handles login, verification, and token extraction WITHOUT creating new PIT
Updates facebook_integrations table with access_token, firebase_token, expires_at, and date fields
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

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("[WARNING] Supabase module not available. Will only capture tokens.")
    SUPABASE_AVAILABLE = False

class HighLevelRetryAutomation:
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
        self.playwright = None
        
    async def setup_browser(self):
        """Initialize Playwright browser with network logging enabled"""
        try:
            self.playwright = await async_playwright().start()
            
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
            
            # Search for security code emails from the last hour
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
            
            # Get the latest email
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
                    
                    # Mark email as read
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
            # JWT tokens have 3 parts separated by dots
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # The payload is the second part
            payload_part = parts[1]
            
            # Add padding if needed
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
        """Extract tokens from localStorage/sessionStorage"""
        try:
            print("[🔍 TOKENS] Checking browser storage for tokens...")
            
            # Check localStorage
            local_storage = await self.page.evaluate("() => window.localStorage")
            for key, value in local_storage.items():
                # Check for GHL's Base64 encoded token storage (key "a")
                if key == "a" and value:
                    try:
                        # Decode the Base64 value
                        decoded_bytes = base64.b64decode(value + '==')  # Add padding if needed
                        decoded_str = decoded_bytes.decode('utf-8')
                        token_data = json.loads(decoded_str)
                        
                        if isinstance(token_data, dict):
                            # Look for refresh tokens
                            if 'refreshToken' in token_data:
                                self.refresh_token = token_data['refreshToken']
                                print(f"[✅ REFRESH] Found refreshToken in Base64 storage: {self.refresh_token[:30]}...")
                            if 'refreshJwt' in token_data:
                                if not self.refresh_token:
                                    self.refresh_token = token_data['refreshJwt']
                                    print(f"[✅ REFRESH] Found refreshJwt in Base64 storage: {self.refresh_token[:30]}...")
                            if 'authToken' in token_data:
                                self.access_token = token_data['authToken']
                                print(f"[✅ ACCESS] Found authToken in Base64 storage: {self.access_token[:30]}...")
                            if 'jwt' in token_data:
                                if not self.access_token:
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
        """Handle email verification with automatic OTP reading"""
        self.location_id = location_id or getattr(self, 'location_id', None)
        try:
            page_source = (await self.page.content()).lower()
            
            # Check if we need email verification
            if "verification" in page_source or "verify" in page_source or "code" in page_source:
                print("\n" + "="*60)
                print("[VERIFICATION] Email verification required!")
                print("="*60)
                
                # Click the "Send Security Code" button
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
                        print("[⏳ WAITING] Waiting 5 seconds for email to be sent...")
                        await asyncio.sleep(5)  # Give more time for email to arrive
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
                    print("[⏳ WAITING] Waiting 30 seconds for manual OTP entry...")
                    await asyncio.sleep(30)
                    return True
                
                print(f"[✅ VERIFICATION] Using OTP code: {otp_code}")
                
                # Enter OTP using flexible approach
                try:
                    print("[VERIFICATION] Attempting individual digit input...")
                    
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
                                    await element.fill("")
                                    await asyncio.sleep(0.1)
                                
                                # Input each digit
                                for i, digit in enumerate(otp_code):
                                    if i < len(elements):
                                        print(f"[VERIFICATION] Entering digit {i+1}: {digit}")
                                        await elements[i].click()
                                        await asyncio.sleep(0.2)
                                        await elements[i].fill("")
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
                        await asyncio.sleep(5)  # Wait for verification to complete
                    else:
                        print("[❌ VERIFICATION] Failed to input OTP digits automatically")
                        print("[💡 MANUAL] Please enter the OTP manually in the browser")
                        await asyncio.sleep(30)
                        
                except Exception as e:
                    print(f"[ERROR] Verification code input error: {e}")
                    return False
            
            print("[SUCCESS] Verification completed!")
            
            # Wait for page to fully load after verification
            print("[⏳ WAITING] Waiting for page to stabilize after verification...")
            await asyncio.sleep(5)
            
            # Check current URL
            current_url = self.page.url
            print(f"[📍 POST-VERIFICATION] Current URL: {current_url}")
            
            # Extract tokens after successful login
            await self.extract_tokens_from_storage()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Automatic verification failed: {e}")
            return False
    
    async def handle_login_and_verification(self, email: str, password: str):
        """Handle login and automatic email verification"""
        try:
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
                    await asyncio.sleep(8)
                    
                except Exception as e:
                    print(f"[ERROR] Login button error: {e}")
                    return False
            
            # Handle email verification if needed
            return await self.handle_automatic_verification()
            
        except Exception as e:
            print(f"[ERROR] Login and verification failed: {e}")
            return False
    
    async def navigate_to_target(self, location_id: str, email: str, password: str):
        """Navigate to target URL with login and verification handling"""
        try:
            target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
            print(f"[NAVIGATE] Going directly to: {target_url}")
            
            # Go directly to the target URL
            await self.page.goto(target_url)
            await asyncio.sleep(3)
            
            # Handle login and verification
            if not await self.handle_login_and_verification(email, password):
                return False
            
            # Wait and check final URL
            await asyncio.sleep(5)
            final_url = self.page.url
            print(f"[INFO] Final URL: {final_url}")
            
            # Extract tokens after reaching the target page
            await self.extract_tokens_from_storage()
            
            return True
                
        except Exception as e:
            print(f"[ERROR] Navigation failed: {e}")
            return False
    
    async def update_facebook_integrations_table(self, firm_user_id: str):
        """Update facebook_integrations table with captured tokens and dates ONLY"""
        try:
            if not SUPABASE_AVAILABLE:
                print("[💾 DATABASE] Supabase not available - skipping database update")
                return True
                
            print("\n[💾 DATABASE] Updating facebook_integrations table with tokens...")
            
            # Initialize Supabase client
            supabase_url = "https://aoteeitreschwzkbpqyd.supabase.co"
            supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Decode access token to get expiry
            access_token_info = None
            if self.access_token:
                access_token_info = self.decode_jwt_token(self.access_token)
                if access_token_info:
                    self.token_expiry = access_token_info['expires_at']
            
            # Prepare update data - ONLY tokens and dates
            current_time = datetime.now().isoformat()
            update_data = {
                'updated_at': current_time
            }
            
            # Add tokens if captured
            if self.access_token:
                update_data['access_token'] = self.access_token
                print(f"[💾] Adding access_token: {self.access_token[:30]}...")
            
            if self.firebase_token:
                update_data['firebase_token'] = self.firebase_token
                print(f"[💾] Adding firebase_token: {self.firebase_token[:30]}...")
            
            if self.token_expiry:
                update_data['access_token_expires_at'] = self.token_expiry.isoformat()
                print(f"[💾] Adding expires_at: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Update the record
            result = supabase.table('facebook_integrations').update(update_data).eq('firm_user_id', firm_user_id).execute()
            
            if result.data:
                print("[✅ DATABASE] Successfully updated facebook_integrations table!")
                print(f"[📊 DATABASE] Updated record for firm_user_id: {firm_user_id}")
                print(f"[🔑] Access Token: {'✅ Updated' if self.access_token else '❌ Not Found'}")
                print(f"[🔥] Firebase Token: {'✅ Updated' if self.firebase_token else '❌ Not Found'}")
                print(f"[⏰] Token Expiry: {'✅ Updated' if self.token_expiry else '❌ Not Found'}")
                return True
            else:
                print(f"[❌ DATABASE] No record found for firm_user_id: {firm_user_id}")
                return False
            
        except Exception as e:
            print(f"[❌ DATABASE] Error updating database: {e}")
            return False
    
    async def run_retry_automation(self, email: str, password: str, location_id: str, firm_user_id: str):
        """Run the retry automation workflow - token capture only, no PIT creation"""
        try:
            # Use agency credentials from environment variables
            agency_email = os.getenv('HIGHLEVEL_EMAIL')
            agency_password = os.getenv('HIGHLEVEL_PASSWORD')
            
            if not agency_email or not agency_password:
                print("[ERROR] Agency credentials not found in environment variables!")
                print("Required: HIGHLEVEL_EMAIL and HIGHLEVEL_PASSWORD")
                return False
            
            print("="*80)
            print("[RETRY AUTOMATION] HighLevel Token Capture - NO PIT Creation")
            print("="*80)
            print(f"[TARGET] Location ID: {location_id}")
            print(f"[TARGET] Firm User ID: {firm_user_id}")
            print(f"[TARGET] URL: https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/")
            print(f"[CREDENTIALS] HighLevel Email: {agency_email}")
            print("[INFO] Will capture access_token, firebase_token, and expires_at ONLY")
            print("[INFO] NO Private Integration Token creation")
            print()
            
            # Step 1: Setup Browser
            print("[STEP 1] Setting up Playwright browser...")
            if not await self.setup_browser():
                return False
            
            # Step 2: Navigate and handle login/verification
            print("\n[STEP 2] Navigating with login and automatic email verification...")
            if not await self.navigate_to_target(location_id, agency_email, agency_password):
                return False
            
            # Step 3: Update database with captured tokens
            print("\n[STEP 3] Updating facebook_integrations table...")
            success = await self.update_facebook_integrations_table(firm_user_id)
            
            # Step 4: Show results
            print("\n" + "="*80)
            print("[SUCCESS] Retry automation workflow finished!")
            print(f"[RESULT] Tokens captured for location: {location_id}")
            print(f"[DATABASE] Updated firm_user_id: {firm_user_id}")
            print("[INFO] Browser will remain open for manual work if needed")
            print("="*80)
            
            return success
            
        except Exception as e:
            print(f"[ERROR] Retry automation failed: {e}")
            return False
        finally:
            # Keep browser open for manual work
            print("\n[BROWSER] Browser staying open for manual work...")

async def main():
    """Main function for testing"""
    load_dotenv()
    
    # Test parameters
    location_id = "MdY4KL72E0lc7TqMm3H0"
    firm_user_id = "test-firm-user-id-123"  # Replace with actual firm_user_id
    
    print(f"\n[INPUT] Using location ID: {location_id}")
    print(f"[INPUT] Using firm_user_id: {firm_user_id}")
    print()
    
    # Run retry automation
    automation = HighLevelRetryAutomation(headless=False)
    success = await automation.run_retry_automation("", "", location_id, firm_user_id)
    
    if success:
        print("\n[FINAL] Retry automation completed successfully!")
    else:
        print("\n[FINAL] Retry automation failed - check the logs above")

if __name__ == "__main__":
    asyncio.run(main())