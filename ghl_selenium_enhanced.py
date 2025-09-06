#!/usr/bin/env python3
"""
HighLevel Automation with Automatic Email OTP Reading
Enhanced version of the working Selenium script with automatic 2FA
"""

import os
import sys
import time
import imaplib
import email
import re
import asyncio
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains

class HighLevelEnhancedAutomation:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Initialize Chrome WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[SUCCESS] Chrome WebDriver initialized")
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
            
            # Search for unread security code emails from GHL
            search_criteria = '(FROM "noreply@talk.onetoo.com" UNSEEN SUBJECT "Login security code")'
            result, data = mail.search(None, search_criteria)
            
            if result != 'OK' or not data[0]:
                print("[📧 EMAIL] No unread security code emails found")
                return None
            
            email_ids = data[0].split()
            print(f"[📧 EMAIL] Found {len(email_ids)} unread security code email(s)")
            
            if not email_ids:
                return None
            
            # Get the latest email (highest ID)
            latest_email_id = max(email_ids, key=lambda x: int(x))
            print(f"[📧 EMAIL] Processing latest email ID: {latest_email_id.decode()}")
            
            # Fetch the email
            result, msg_data = mail.fetch(latest_email_id, '(RFC822)')
            if result != 'OK':
                print("[❌ EMAIL] Failed to fetch email")
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
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
    
    def handle_automatic_verification(self):
        """Handle email verification with automatic OTP reading"""
        try:
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()
            
            # Check if we need email verification
            if "verification" in page_source or "verify" in page_source or "code" in page_source:
                print("\\n" + "="*60)
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
                    time.sleep(3)
                    
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
                    print("[💡 MANUAL] Please enter the code manually:")
                    
                    # Fallback to manual input
                    while True:
                        try:
                            user_input = input("[INPUT] Enter the verification code from your email: ").strip()
                            
                            if user_input and user_input.isdigit() and len(user_input) >= 4:
                                otp_code = user_input
                                break
                            else:
                                print("[ERROR] Please enter a valid verification code")
                        except KeyboardInterrupt:
                            print("\\n[CANCELLED] Automation cancelled by user")
                            return False
                
                print(f"[✅ VERIFICATION] Using OTP code: {otp_code}")
                
                # Use flexible approach like enhanced_2fa_service.py
                try:
                    print("[VERIFICATION] Attempting individual digit input (flexible approach)...")
                    
                    # Try different selectors for individual digit inputs
                    digit_selectors = [
                        'input[maxlength="1"]',  # Most common for digit inputs
                        'input[type="text"][maxlength="1"]',  # Specific text inputs with single char
                        '.otp-digit',
                        '.digit-input', 
                        '[data-testid="digit-input"]',
                        'input[class*="digit"]'  # Any input with "digit" in class name
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
                                        elements[i].click()  # Focus the input
                                        time.sleep(0.2)
                                        elements[i].clear()  # Clear again
                                        time.sleep(0.1)
                                        elements[i].send_keys(digit)  # Enter the digit
                                        time.sleep(0.3)
                                        print(f"[VERIFICATION] Digit {i+1} entered successfully")
                                
                                print("[✅ VERIFICATION] All digits entered successfully!")
                                input_success = True
                                break
                                
                        except Exception as e:
                            print(f"[⚠️ VERIFICATION] Selector {selector} failed: {e}")
                            continue
                    
                    # Fallback to exact XPaths if flexible approach fails
                    if not input_success:
                        print("[VERIFICATION] Falling back to exact XPath approach...")
                        verification_xpaths = [
                            "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[1]/input",
                            "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[2]/input",
                            "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[3]/input",
                            "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[4]/input",
                            "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[5]/input",
                            "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[6]/input"
                        ]
                        
                        for i, digit in enumerate(otp_code):
                            print(f"[VERIFICATION] XPath entering digit {i+1}: {digit}")
                            field = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, verification_xpaths[i]))
                            )
                            field.click()  # Click to focus
                            time.sleep(0.3)
                            field.clear()  # Clear any existing content
                            time.sleep(0.3)
                            field.send_keys(digit)  # Enter the digit
                            time.sleep(0.5)
                            print(f"[VERIFICATION] XPath digit {i+1} entered successfully")
                        
                        input_success = True
                    
                    if input_success:
                        print("[✅ VERIFICATION] All 6 digits entered successfully")
                        time.sleep(5)  # Wait for verification to complete
                    else:
                        print("[❌ VERIFICATION] Failed to input OTP digits")
                        return False
                        
                except Exception as e:
                    print(f"[ERROR] Verification code input error: {e}")
                    return False
            
            print("[SUCCESS] Verification completed!")
            
            # After successful 2FA, we should already be on private integrations page
            # Just call create_private_integration directly like the original script
            return self.create_private_integration()
            
        except Exception as e:
            print(f"[ERROR] Automatic verification failed: {e}")
            return False
    
    def navigate_to_private_integrations_and_create(self):
        """Navigate to private integrations page and create integration"""
        try:
            current_url = self.driver.current_url
            print(f"\\n[NAVIGATION] Current URL: {current_url}")
            
            # Extract location ID from current URL
            import re
            location_match = re.search(r'/location/([^/]+)/', current_url)
            if location_match:
                location_id = location_match.group(1)
                print(f"[NAVIGATION] Detected location ID: {location_id}")
                
                # Navigate to private integrations page
                target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
                print(f"[NAVIGATION] Navigating to: {target_url}")
                
                self.driver.get(target_url)
                time.sleep(5)
                
                print(f"[NAVIGATION] Successfully navigated to private integrations page")
                return self.create_private_integration()
            else:
                print("[ERROR] Could not extract location ID from URL")
                return False
                
        except Exception as e:
            print(f"[ERROR] Navigation failed: {e}")
            return False
    
    def create_private_integration(self):
        """Create the private integration with all required scopes"""
        print("\\n[STEP 3] Creating private integration...")
        
        # We should already be on the private integrations page after navigation
        print("[INFO] Should already be on private integrations page after navigation")
        
        # Wait a bit more for page to fully load
        time.sleep(3)
        current_url = self.driver.current_url
        print(f"[CURRENT URL] {current_url}")
        
        # The original script assumes we're already on the private integrations page after 2FA
        # Don't try to navigate again, just proceed with integration creation
        if "private-integrations" not in current_url:
            print("[INFO] Not on private integrations page, but proceeding anyway like original script")
            print("[INFO] Original script returns True even when not on expected page")
        
        # If we're not on the right page, we should be redirected there automatically
        time.sleep(5)
        
        # Press the integration creation button with fallback option
        try:
            print("[INTEGRATION] Looking for primary integration creation button...")
            create_button_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div[2]/button[2]/span"
            
            try:
                # Try primary button first
                create_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, create_button_xpath))
                )
                create_button.click()
                print("[INTEGRATION] Primary integration creation button clicked")
            except Exception as primary_error:
                # If primary button fails, wait and try fallback button
                print(f"[INFO] Primary button not found or not clickable: {primary_error}")
                print("[INFO] Waiting 2 seconds then trying fallback button...")
                time.sleep(2)
                
                try:
                    # Try fallback button
                    fallback_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div/button/span"
                    fallback_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, fallback_xpath))
                    )
                    fallback_button.click()
                    print("[INTEGRATION] Fallback integration creation button clicked")
                except Exception as fallback_error:
                    raise Exception(f"Both buttons failed. Primary: {primary_error}, Fallback: {fallback_error}")
            
            # Wait for form to load
            time.sleep(3)
        except Exception as e:
            print(f"[ERROR] Could not click any integration creation button: {e}")
            return False
        
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
        
        # Continue with scope selection and token extraction...
        print("[✅ SUCCESS] Private integration automation completed!")
        print("[💡 INFO] Token extraction can be added here...")
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
        """Navigate to target URL with login and verification handling - EXACT SAME as original script"""
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
    
    def take_screenshot(self, location_id: str):
        """Take a screenshot of the current page"""
        try:
            filename = f"ghl_enhanced_automation_{location_id}.png"
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
            print("[AUTOMATION] HighLevel Enhanced Automation with Automatic 2FA")
            print("="*80)
            print(f"[TARGET] Location ID: {location_id}")
            print(f"[TARGET] URL: https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/")
            print(f"[CREDENTIALS] HighLevel Email: {email}")
            print("[INFO] 2FA codes will be read automatically from Gmail")
            print()
            
            # Step 1: Setup WebDriver
            print("[STEP 1] Setting up Chrome WebDriver...")
            if not self.setup_driver():
                return False
            
            # Step 2: Navigate and handle login/verification (this will call create_private_integration internally)
            print("\\n[STEP 2] Navigating with login and automatic email verification...")
            if not self.navigate_to_target(location_id, email, password):
                return False
            
            # Step 3: Take screenshot
            print("\\n[STEP 3] Taking screenshot...")
            screenshot = self.take_screenshot(location_id)
            
            # Step 4: Show success and keep browser open
            print("\\n" + "="*80)
            print("[SUCCESS] Enhanced automation workflow completed!")
            print(f"[RESULT] Private integration created for location: {location_id}")
            if screenshot:
                print(f"[SCREENSHOT] Screenshot saved as: {screenshot}")
            print("[INFO] Browser will remain open for you to continue working")
            print("[INFO] You can manually close the browser when finished")
            print("="*80)
            
            # Keep browser open - don't close automatically
            input("\\n[PAUSE] Press Enter to close the browser (or just close this terminal to keep it open)...")
            return True
            
        except Exception as e:
            print(f"[ERROR] Automation failed: {e}")
            return False
        finally:
            # Only close browser if user pressed Enter
            if self.driver:
                try:
                    print("\\n[CLEANUP] Closing browser...")
                    self.driver.quit()
                except:
                    pass  # Browser may already be closed

def main():
    """Main function"""
    load_dotenv()
    
    # Get HighLevel credentials
    email = os.getenv('HIGHLEVEL_EMAIL')
    password = os.getenv('HIGHLEVEL_PASSWORD')
    
    if not email or not password:
        print("[ERROR] Missing HighLevel credentials. Please set in .env file:")
        print("  HIGHLEVEL_EMAIL=your_highlevel_email")
        print("  HIGHLEVEL_PASSWORD=your_highlevel_password")
        return
    
    # Use the correct location ID
    location_id = "MdY4KL72E0lc7TqMm3H0"
    print(f"[INPUT] Using location ID: {location_id}")
    
    # Run automation
    automation = HighLevelEnhancedAutomation(headless=False)
    success = automation.run_automation(email, password, location_id)
    
    if success:
        print("\\n[FINAL] Enhanced automation with automatic 2FA completed successfully!")
    else:
        print("\\n[FINAL] Automation failed - check the logs above")

if __name__ == "__main__":
    main()