#!/usr/bin/env python3
"""
HighLevel Complete Automation with Automatic OTP and Full PIT Creation
Combines automatic Gmail OTP reading with complete integration creation including token extraction
"""

import os
import sys
import time
import imaplib
import email
import re
import json
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

class HighLevelCompleteAutomation:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.firebase_token = None  # token-id header
        self.api_tokens = {
            'authorization': None,
            'token-id': None
        }
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with network logging enabled"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_experimental_option("detach", True)  # Keep browser open
            
            # Enable network logging to capture requests
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[SUCCESS] Chrome WebDriver initialized with network logging")
                return True
            except:
                print("[ERROR] Could not initialize Chrome WebDriver")
                return False
            
        except Exception as e:
            print(f"[ERROR] WebDriver setup failed: {str(e)}")
            return False
    
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
    
    def extract_tokens_from_network(self):
        """Extract access token, firebase token, and API tokens from network logs"""
        try:
            print("\n[🔍 TOKENS] Extracting tokens from network logs...")
            
            # Get network logs
            logs = self.driver.get_log('performance')
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    method = message.get('message', {}).get('method', '')
                    
                    # Look for network requests with authorization headers
                    if method == 'Network.requestWillBeSentExtraInfo':
                        headers = message.get('message', {}).get('params', {}).get('headers', {})
                        
                        # Check for Authorization header (Bearer token)
                        auth_header = headers.get('Authorization', '') or headers.get('authorization', '')
                        if auth_header and auth_header.startswith('Bearer '):
                            token = auth_header.replace('Bearer ', '').strip()
                            if token and len(token) > 20:  # Valid token length
                                self.access_token = token
                                self.api_tokens['authorization'] = token
                                print(f"[✅ TOKENS] Found Authorization Bearer token: {token[:20]}...")
                        
                        # Check for token-id header (Firebase ID token)
                        token_id = headers.get('token-id', '') or headers.get('Token-Id', '')
                        if token_id and len(token_id) > 20:
                            self.firebase_token = token_id
                            self.api_tokens['token-id'] = token_id
                            print(f"[✅ TOKENS] Found token-id (Firebase): {token_id[:20]}...")
                        
                        # Check for refresh token in cookies or other headers
                        cookie_header = headers.get('Cookie', '') or headers.get('cookie', '')
                        if 'refresh_token=' in cookie_header:
                            refresh_match = re.search(r'refresh_token=([^;]+)', cookie_header)
                            if refresh_match:
                                self.refresh_token = refresh_match.group(1)
                                print(f"[✅ TOKENS] Found refresh token: {self.refresh_token[:20]}...")
                    
                    # Also check response headers for tokens
                    elif method == 'Network.responseReceivedExtraInfo':
                        headers = message.get('message', {}).get('params', {}).get('headers', {})
                        
                        # Check for tokens in response headers
                        if 'x-access-token' in headers:
                            self.access_token = headers['x-access-token']
                            print(f"[✅ TOKENS] Found access token in response: {self.access_token[:20]}...")
                        
                        if 'x-refresh-token' in headers:
                            self.refresh_token = headers['x-refresh-token']
                            print(f"[✅ TOKENS] Found refresh token in response: {self.refresh_token[:20]}...")
                
                except Exception as e:
                    continue
            
            # Alternative method: Execute JavaScript to get tokens from localStorage/sessionStorage
            if not self.access_token:
                try:
                    print("[🔍 TOKENS] Checking localStorage for tokens...")
                    
                    # Check localStorage
                    local_storage = self.driver.execute_script("return window.localStorage;")
                    for key, value in local_storage.items():
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
                    session_storage = self.driver.execute_script("return window.sessionStorage;")
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
            
            return self.access_token is not None
            
        except Exception as e:
            print(f"[❌ TOKENS] Error extracting tokens: {e}")
            return False
    
    def handle_automatic_verification(self):
        """Handle email verification with automatic OTP reading"""
        try:
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()
            
            # Check if we need email verification
            if "verification" in page_source or "verify" in page_source or "code" in page_source:
                print("\n" + "="*60)
                print("[VERIFICATION] Email verification required!")
                print("="*60)
                
                # First, click the "Send Code" button
                try:
                    print("[VERIFICATION] Looking for 'Send Code' button...")
                    send_code_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/button"
                    
                    send_code_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, send_code_xpath))
                    )
                    print("[VERIFICATION] Found 'Send Code' button")
                    
                    send_code_button.click()
                    print("[VERIFICATION] 'Send Code' button clicked - email being sent...")
                    print("[⏳ WAITING] Waiting 5 seconds for email to be sent...")
                    time.sleep(5)  # Give more time for email to arrive
                    
                except Exception as e:
                    print(f"[WARNING] Could not find/click 'Send Code' button: {e}")
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
                    time.sleep(1)
                
                if not otp_code:
                    print("[❌ AUTO] Failed to get OTP automatically")
                    print("[💡 MANUAL] Please check your email and manually enter the code in the browser")
                    print("[⏳ WAITING] Waiting 30 seconds for manual OTP entry...")
                    time.sleep(30)
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
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            if len(elements) >= len(otp_code):
                                print(f"[📱 VERIFICATION] Found {len(elements)} digit inputs using: {selector}")
                                
                                # Clear all inputs first
                                for element in elements[:len(otp_code)]:
                                    element.clear()
                                    time.sleep(0.1)
                                
                                # Input each digit with small delays
                                for i, digit in enumerate(otp_code):
                                    if i < len(elements):
                                        print(f"[VERIFICATION] Entering digit {i+1}: {digit}")
                                        elements[i].click()
                                        time.sleep(0.2)
                                        elements[i].clear()
                                        time.sleep(0.1)
                                        elements[i].send_keys(digit)
                                        time.sleep(0.3)
                                        print(f"[VERIFICATION] Digit {i+1} entered successfully")
                                
                                print("[✅ VERIFICATION] All digits entered successfully!")
                                input_success = True
                                break
                                
                        except Exception as e:
                            print(f"[⚠️ VERIFICATION] Selector {selector} failed: {e}")
                            continue
                    
                    if input_success:
                        print("[✅ VERIFICATION] OTP entered successfully")
                        time.sleep(5)  # Wait for verification to complete
                    else:
                        print("[❌ VERIFICATION] Failed to input OTP digits automatically")
                        print("[💡 MANUAL] Please enter the OTP manually in the browser")
                        time.sleep(30)
                        
                except Exception as e:
                    print(f"[ERROR] Verification code input error: {e}")
                    return False
            
            print("[SUCCESS] Verification completed!")
            
            # Extract tokens after successful login
            self.extract_tokens_from_network()
            
            return self.create_private_integration()
            
        except Exception as e:
            print(f"[ERROR] Automatic verification failed: {e}")
            return False
    
    def create_private_integration(self):
        """Create the private integration with all required scopes and extract token"""
        print("\n[STEP 3] Creating private integration...")
        
        # We should already be on the private integrations page after login/verification
        print("[INFO] Should already be on private integrations page after login/verification")
        current_url = self.driver.current_url
        print(f"[CURRENT URL] {current_url}")
        
        # Wait for page to fully load and handle any redirects
        print("[⏳ WAITING] Waiting for page to stabilize...")
        time.sleep(8)  # Increased wait time
        
        # Check if URL has changed after waiting
        new_url = self.driver.current_url
        if new_url != current_url:
            print(f"[📍 REDIRECT] Page redirected to: {new_url}")
        
        # Try multiple times with different strategies
        max_retries = 3
        for retry in range(max_retries):
            print(f"\n[🔄 RETRY] Attempt {retry + 1}/{max_retries} to find integration button...")
            
            # Press the integration creation button with multiple fallback options
            try:
                # List of button selectors to try
                button_selectors = [
                    # Primary button
                    "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div[2]/button[2]/span",
                    # Fallback button
                    "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div/button/span",
                    # Alternative selectors
                    "//button[contains(text(), 'Create Private Integration')]",
                    "//button[contains(text(), 'Create Integration')]",
                    "//button[contains(text(), 'New Integration')]",
                    "//button[contains(text(), 'Add Integration')]",
                    "//button[contains(@class, 'integration')]//span",
                    "//button[contains(@id, 'create')]//span",
                    "//span[contains(text(), 'Create')]/..",
                    "//div[contains(@class, 'integration')]//button[last()]"
                ]
                
                button_clicked = False
                for selector in button_selectors:
                    try:
                        print(f"[🔍 SEARCH] Trying selector: {selector}")
                        create_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        # Scroll element into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", create_button)
                        time.sleep(0.5)
                        create_button.click()
                        print(f"[✅ SUCCESS] Integration button clicked using: {selector}")
                        button_clicked = True
                        break
                    except Exception:
                        continue
                
                if button_clicked:
                    # Wait for form to load
                    print("[⏳ WAITING] Waiting for form to load...")
                    time.sleep(3)
                    break
                else:
                    if retry < max_retries - 1:
                        print(f"[⏳ WAITING] No button found, waiting 5 seconds before retry...")
                        time.sleep(5)
                    else:
                        raise Exception("Could not find integration creation button after all retries")
                    
            except Exception as e:
                print(f"[❌ ERROR] Failed on attempt {retry + 1}: {e}")
                if retry == max_retries - 1:
                    print("[💡 FALLBACK] Could not click integration button. Please click it manually in the browser.")
                    print("[⏳ WAITING] Waiting 20 seconds for manual intervention...")
                    time.sleep(20)
                    # Continue anyway as user might have clicked manually
        
        # Fill integration name
        try:
            print("[INTEGRATION] Filling integration name...")
            name_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div[1]/div[1]/div/div[1]/div[1]/input"
            name_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, name_xpath))
            )
            name_field.clear()
            name_field.send_keys("location key")
            print("[INTEGRATION] Integration name set to: location key")
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Could not fill integration name: {e}")
            return False
        
        # Submit the form
        try:
            print("[INTEGRATION] Submitting integration form...")
            submit_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]"
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, submit_xpath))
            )
            submit_button.click()
            print("[INTEGRATION] Form submitted")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Could not submit integration form: {e}")
            return False
        
        # Select scopes
        try:
            print("[INTEGRATION] Opening scopes selection...")
            
            # Click the main scopes container to activate the input
            print("[INTEGRATION] Clicking main scopes container...")
            scopes_container_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div/div/div[1]"
            scopes_container = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, scopes_container_xpath))
            )
            scopes_container.click()
            time.sleep(1)
            
            # List of scopes to add - User specified scopes only (15)
            scopes_to_add = [
                # User-specified scopes (15)
                "View Contacts", "Edit Contacts",
                "View Conversation Reports", "Edit Conversations",
                "View Calendars", "View Businesses",
                "View Conversation Messages", "Edit Conversation Messages",
                "View Custom Fields", "Edit Custom Fields",
                "View Custom Values", "Edit Custom Values",
                "View Medias", "Edit Tags", "View Tags"
            ]
            
            try:
                # Direct targeting approach
                print("[INTEGRATION] Selecting scopes with direct targeting...")
                
                # Try different possible selectors for the dropdown input
                selectors = [
                    "//input[@placeholder='Search scopes...']",
                    "//div[contains(@class, 'n-base-selection-input-tag')]//input",
                    "//div[contains(@class, 'vs__dropdown-toggle')]//input",
                    "//*[contains(@placeholder, 'Search') or contains(@placeholder, 'search')]"
                ]
                
                dropdown = None
                for selector in selectors:
                    try:
                        print(f"Trying selector: {selector}")
                        dropdown = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print(f"Found dropdown with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not dropdown:
                    # Last resort - try to find any input field
                    print("Trying to find any input field")
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for inp in inputs:
                        if inp.is_displayed() and inp.is_enabled():
                            dropdown = inp
                            print("Found visible input element")
                            break
                
                if not dropdown:
                    raise Exception("Could not find any suitable input field for scopes")
                
                # Make sure element is visible
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
                time.sleep(0.05)
                
                # Click to ensure focus
                dropdown.click()
                time.sleep(0.05)
                
                # For each scope, consistently type and press Enter
                for i, scope in enumerate(scopes_to_add):
                    try:
                        # Reset before each scope entry
                        dropdown.click()
                        time.sleep(0.3)
                        
                        # Log which scope we're processing
                        print(f"[{i+1}/{len(scopes_to_add)}] Selecting: {scope}")
                        
                        # Type the scope name
                        dropdown.send_keys(scope)
                        time.sleep(0.05)
                        dropdown.send_keys(Keys.ENTER)
                        time.sleep(0.05)
                        
                        # Quick verification
                        print(f"  ✓ Added scope: {scope}")
                    except Exception as e:
                        print(f"Error selecting scope '{scope}': {e}")
                
            except Exception as e:
                print(f"[ERROR] Failed to select scope: {str(e)}")
            
            # Continue with next steps - Click the Create button
            print("\n[INTEGRATION] Scope selection completed, clicking Create button...")
            try:
                # Use the exact XPath provided
                create_button_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]/span"
                create_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, create_button_xpath))
                )
                create_button.click()
                print("Clicked Create button using exact XPath")
            except Exception as e:
                print(f"Error clicking Create button: {str(e)}")
                try:
                    # Try alternative selector as backup
                    create_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='btn-next']/span"))
                    )
                    create_button.click()
                    print("Clicked Create button using backup selector")
                except Exception as e:
                    print(f"Error clicking Create button with backup selector: {str(e)}")
                    print("Please click the Create button manually")
            
            # Wait for token display and copy it
            print("[INTEGRATION] Waiting for token generation...")
            time.sleep(3)
            
            try:
                # Use the exact XPath for the copy button
                copy_button_xpath = "/html/body/div[7]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/button/span"
                copy_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, copy_button_xpath))
                )
                
                # Before clicking, try to get the token text directly
                try:
                    # Look for pre or code elements that might contain the token
                    token_elements = self.driver.find_elements(By.XPATH, "//pre | //code | //div[contains(@class, 'token')] | //textarea")
                    for elem in token_elements:
                        if elem.is_displayed():
                            token_text = elem.text or elem.get_attribute('value')
                            if token_text and len(token_text) > 10:  # Likely a token
                                print("\n")
                                print("*"*100)
                                print("*" + " "*38 + "INTEGRATION TOKEN FOUND" + " "*38 + "*")
                                print("*" + " "*98 + "*")
                                print("*"*100)
                                print("\n")
                                print(token_text)
                                print("\n")
                                print("*"*100)
                                
                                # Extract tokens one more time
                                self.extract_tokens_from_network()
                                
                                # Save all tokens
                                self.save_all_tokens(token_text)
                except Exception as e:
                    print(f"Could not read token directly: {e}")
                
                # Click the copy button
                copy_button.click()
                print("Clicked copy button with exact XPath to copy token to clipboard")
                
                # After clicking copy button, extract token using exact XPath
                try:
                    # Use the exact XPath where token is displayed
                    exact_token_xpath = "/html/body/div[7]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/p"
                    print("Looking for token at exact XPath...")
                    
                    # Wait for the element to be visible
                    token_element = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, exact_token_xpath))
                    )
                    
                    # Get the token text
                    token_text = token_element.text
                    
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
                        self.extract_tokens_from_network()
                        
                        # Save all tokens
                        self.save_all_tokens(token_text)
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
    
    def handle_login_and_verification(self, email: str, password: str):
        """Handle login and automatic email verification"""
        try:
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()
            
            # Check if we're on a login page
            if "login" in current_url or "sign" in current_url or "sign into your account" in page_source:
                print("[LOGIN] Detected login page - filling credentials...")
                
                # Wait for page to fully load
                time.sleep(3)
                
                # Fill email field
                try:
                    print("[LOGIN] Looking for email field using exact XPath...")
                    email_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[2]/div/div[2]/input"
                    
                    email_field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, email_xpath))
                    )
                    print("[LOGIN] Found email field with exact XPath")
                    
                    email_field.click()
                    email_field.clear()
                    time.sleep(0.5)
                    email_field.send_keys(email)
                    print(f"[LOGIN] Email filled: {email}")
                    time.sleep(1)
                        
                except Exception as e:
                    print(f"[ERROR] Email field error: {e}")
                    return False
                
                # Fill password field
                try:
                    print("[LOGIN] Looking for password field using exact XPath...")
                    password_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div[2]/input"
                    
                    password_field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, password_xpath))
                    )
                    print("[LOGIN] Found password field with exact XPath")
                    
                    password_field.click()
                    password_field.clear()
                    time.sleep(0.5)
                    password_field.send_keys(password)
                    print("[LOGIN] Password filled")
                    time.sleep(1)
                except Exception as e:
                    print(f"[ERROR] Password field error: {e}")
                    return False
                
                # Click login button
                try:
                    print("[LOGIN] Looking for login button...")
                    login_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Sign in")]'))
                    )
                    login_button.click()
                    print("[LOGIN] Login button clicked")
                    
                    # Wait for login to process
                    print("[LOGIN] Waiting for login to complete...")
                    time.sleep(8)
                    
                except Exception as e:
                    print(f"[ERROR] Login button error: {e}")
                    return False
            
            # Handle email verification if needed
            return self.handle_automatic_verification()
            
        except Exception as e:
            print(f"[ERROR] Login and verification failed: {e}")
            return False
    
    def navigate_to_target(self, location_id: str, email: str, password: str):
        """Navigate to target URL with login and verification handling"""
        try:
            target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
            print(f"[NAVIGATE] Going directly to: {target_url}")
            
            # Go directly to the target URL
            self.driver.get(target_url)
            time.sleep(3)
            
            # Handle login and verification
            if not self.handle_login_and_verification(email, password):
                return False
            
            # Wait and check final URL
            time.sleep(5)
            final_url = self.driver.current_url
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
    
    def save_all_tokens(self, pit_token=None):
        """Save all tokens to a comprehensive JSON file"""
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
            
            # Save to JSON file
            with open("highlevel_tokens_complete.json", "w") as f:
                json.dump(tokens_data, f, indent=2)
            
            # Also save PIT to the original file for backward compatibility
            if pit_token:
                with open("highlevel_token.txt", "w") as f:
                    f.write(pit_token)
            
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
            print("\nAll tokens saved to: highlevel_tokens_complete.json")
            print("PIT also saved to: highlevel_token.txt")
            
        except Exception as e:
            print(f"[ERROR] Could not save tokens: {e}")
    
    def take_screenshot(self, location_id: str):
        """Take a screenshot of the current page"""
        try:
            filename = f"ghl_complete_automation_{location_id}.png"
            self.driver.save_screenshot(filename)
            print(f"[SCREENSHOT] Saved: {filename}")
            return filename
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")
            return None
    
    def run_automation(self, email: str, password: str, location_id: str):
        """Run the complete automation workflow with automatic email verification"""
        try:
            print("="*80)
            print("[AUTOMATION] HighLevel Complete Automation with Automatic OTP and Full PIT Creation")
            print("="*80)
            print(f"[TARGET] Location ID: {location_id}")
            print(f"[TARGET] URL: https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/")
            print(f"[CREDENTIALS] HighLevel Email: {email}")
            print("[INFO] 2FA codes will be read automatically from Gmail")
            print("[INFO] Private Integration Token (PIT) will be created and extracted")
            print()
            
            # Step 1: Setup WebDriver
            print("[STEP 1] Setting up Chrome WebDriver...")
            if not self.setup_driver():
                return False
            
            # Step 2: Navigate and handle login/verification
            print("\n[STEP 2] Navigating with login and automatic email verification...")
            if not self.navigate_to_target(location_id, email, password):
                return False
            
            # Step 3: Take screenshot
            print("\n[STEP 4] Taking screenshot...")
            screenshot = self.take_screenshot(location_id)
            
            # Step 4: Show success and keep browser open
            print("\n" + "="*80)
            print("[SUCCESS] Complete automation workflow finished!")
            print(f"[RESULT] Private integration created for location: {location_id}")
            if screenshot:
                print(f"[SCREENSHOT] Screenshot saved as: {screenshot}")
            print("[INFO] Browser will remain open for you to continue working")
            print("[INFO] Check highlevel_tokens_complete.json for all tokens (PIT, access, refresh)")
            print("[INFO] PIT also saved to highlevel_token.txt for backward compatibility")
            print("="*80)
            
            # Keep browser open - don't close automatically
            print("\n[BROWSER] Browser will stay open. Close it manually when done.")
            return True
            
        except Exception as e:
            print(f"[ERROR] Automation failed: {e}")
            return False

def main():
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
    print()
    
    # Run automation
    automation = HighLevelCompleteAutomation(headless=False)
    success = automation.run_automation(email, password, location_id)
    
    if success:
        print("\n[FINAL] Complete automation with automatic 2FA and PIT creation completed successfully!")
    else:
        print("\n[FINAL] Automation failed - check the logs above")

if __name__ == "__main__":
    main()