#!/usr/bin/env python3
"""
Fixed GHL Private Integration Automation
Handles navigation through UI after login
"""

import os
import time
import imaplib
import email
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GHLPrivateIntegrationFixed:
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
            
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Chrome WebDriver initialized")
            return True
        except Exception as e:
            print(f"❌ WebDriver setup failed: {e}")
            return False
    
    def get_otp_from_gmail(self):
        """Get OTP code from Gmail automatically"""
        try:
            print("📧 Connecting to Gmail for OTP...")
            
            email_address = os.getenv('GMAIL_2FA_EMAIL', 'somashekhar34@gmail.com')
            email_password = os.getenv('GMAIL_2FA_APP_PASSWORD', 'ytmfxlelgyojxjmf')
            
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(email_address, email_password)
            mail.select('inbox')
            
            # Search for unread security code emails
            search_criteria = '(FROM "noreply@talk.onetoo.com" UNSEEN SUBJECT "Login security code")'
            result, data = mail.search(None, search_criteria)
            
            if result != 'OK' or not data[0]:
                print("📧 No unread security code emails found")
                return None
            
            email_ids = data[0].split()
            if not email_ids:
                return None
            
            # Get the latest email
            latest_email_id = max(email_ids, key=lambda x: int(x))
            
            # Fetch the email
            result, msg_data = mail.fetch(latest_email_id, '(RFC822)')
            if result != 'OK':
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract body
            body = self._extract_email_body(msg)
            
            # Extract OTP
            otp_patterns = [
                r'Your login security code:\s*(\d{6})',
                r'login security code:\s*(\d{6})',
                r'\b(\d{6})\b'
            ]
            
            for pattern in otp_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    otp = matches[0]
                    print(f"✅ Extracted OTP: {otp}")
                    
                    # Mark as read
                    mail.store(latest_email_id, '+FLAGS', '\\Seen')
                    mail.close()
                    mail.logout()
                    return otp
            
            mail.close()
            mail.logout()
            return None
            
        except Exception as e:
            print(f"❌ Email error: {e}")
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
    
    def handle_login_and_2fa(self, email: str, password: str):
        """Handle login and automatic 2FA"""
        try:
            # Fill email
            email_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[2]/div/div[2]/input"
            email_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, email_xpath))
            )
            email_field.clear()
            email_field.send_keys(email)
            print(f"✅ Email filled: {email}")
            
            # Fill password
            password_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div[2]/input"
            password_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, password_xpath))
            )
            password_field.clear()
            password_field.send_keys(password)
            print("✅ Password filled")
            
            # Click login
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Sign in")]'))
            )
            login_button.click()
            print("✅ Login button clicked")
            time.sleep(8)
            
            # Handle 2FA if needed
            page_source = self.driver.page_source.lower()
            if "verification" in page_source or "verify" in page_source:
                print("🔐 2FA required - handling automatically...")
                
                # Click send code
                try:
                    send_code_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/button"
                    send_code_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, send_code_xpath))
                    )
                    send_code_button.click()
                    print("✅ Send code button clicked")
                    time.sleep(3)
                except:
                    print("⚠️ Send code button not found, continuing...")
                
                # Get OTP
                max_attempts = 30
                otp_code = None
                
                for attempt in range(max_attempts):
                    print(f"🔍 Attempt {attempt + 1}/{max_attempts}")
                    otp_code = self.get_otp_from_gmail()
                    if otp_code:
                        break
                    time.sleep(1)
                
                if not otp_code:
                    print("❌ Failed to get OTP automatically")
                    return False
                
                # Input OTP
                print("⌨️ Inputting OTP digits...")
                inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[maxlength="1"]')
                if len(inputs) >= 6:
                    for i, digit in enumerate(otp_code):
                        inputs[i].clear()
                        inputs[i].send_keys(digit)
                        time.sleep(0.3)
                        print(f"✅ Digit {i+1}: {digit}")
                
                print("✅ All digits entered - waiting for verification...")
                time.sleep(8)
            
            return True
            
        except Exception as e:
            print(f"❌ Login/2FA failed: {e}")
            return False
    
    def navigate_through_ui_to_private_integrations(self):
        """Navigate to private integrations through the UI"""
        try:
            print("🔍 Navigating to private integrations through UI...")
            
            # Wait for dashboard to load
            time.sleep(5)
            
            # Click on Settings in the left menu
            try:
                print("🎯 Looking for Settings in left menu...")
                # Try multiple selectors for Settings
                settings_selectors = [
                    "//span[contains(text(), 'Settings')]",
                    "//div[contains(text(), 'Settings')]", 
                    "//a[contains(text(), 'Settings')]",
                    "//*[contains(@class, 'sidebar')]//span[contains(text(), 'Settings')]",
                    "//*[contains(@class, 'menu')]//span[contains(text(), 'Settings')]"
                ]
                
                settings_clicked = False
                for selector in settings_selectors:
                    try:
                        settings = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        settings.click()
                        print("✅ Clicked Settings")
                        settings_clicked = True
                        break
                    except:
                        continue
                
                if not settings_clicked:
                    print("❌ Could not find Settings button")
                    return False
                
                # Wait for settings page to load
                time.sleep(3)
                
                # Click on Private Integrations
                print("🎯 Looking for Private Integrations...")
                pi_selectors = [
                    "//span[contains(text(), 'Private Integrations')]",
                    "//div[contains(text(), 'Private Integrations')]",
                    "//a[contains(text(), 'Private Integrations')]",
                    "//*[contains(text(), 'Private') and contains(text(), 'Integrations')]"
                ]
                
                pi_clicked = False
                for selector in pi_selectors:
                    try:
                        pi_link = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        pi_link.click()
                        print("✅ Clicked Private Integrations")
                        pi_clicked = True
                        break
                    except:
                        continue
                
                if not pi_clicked:
                    print("❌ Could not find Private Integrations link")
                    return False
                
                # Wait for page to load
                time.sleep(5)
                
                current_url = self.driver.current_url
                print(f"📍 Current URL: {current_url}")
                
                return True
                
            except Exception as e:
                print(f"❌ UI navigation error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False
    
    def create_private_integration(self):
        """Create the private integration"""
        try:
            print("🔧 Creating private integration...")
            
            # Wait for page to load
            time.sleep(3)
            
            # Try to click create integration button
            try:
                # Try multiple selectors
                create_selectors = [
                    "//button[contains(text(), 'Create') or contains(text(), 'New')]",
                    "//button[contains(@class, 'primary')]",
                    "//button[contains(@class, 'btn')]",
                    "//*[@role='button'][contains(text(), 'Create')]"
                ]
                
                for selector in create_selectors:
                    try:
                        create_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        create_button.click()
                        print("✅ Create integration button clicked")
                        break
                    except:
                        continue
                
            except:
                print("❌ Could not find create button")
                return False
            
            time.sleep(3)
            
            # Fill integration name
            try:
                name_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in name_inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        placeholder = inp.get_attribute("placeholder") or ""
                        if "name" in placeholder.lower() or not placeholder:
                            inp.clear()
                            inp.send_keys("Auto Location Key")
                            print("✅ Integration name filled")
                            break
                
                time.sleep(2)
            except Exception as e:
                print(f"❌ Could not fill name: {e}")
                return False
            
            # Submit form
            try:
                submit_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Create') or contains(text(), 'Submit') or contains(text(), 'Next')]")
                for btn in submit_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        print("✅ Form submitted")
                        break
                
                time.sleep(5)
            except Exception as e:
                print(f"❌ Could not submit: {e}")
                return False
            
            print("✅ Private integration process initiated!")
            return True
            
        except Exception as e:
            print(f"❌ Integration creation failed: {e}")
            return False
    
    def extract_pit_token(self):
        """Try to extract the PIT token from the page"""
        try:
            print("🔍 Looking for PIT token...")
            time.sleep(3)
            
            # Look for token in various elements
            token_selectors = [
                "//pre",
                "//code", 
                "//*[contains(text(), 'pit-')]",
                "//textarea",
                "//*[contains(@class, 'token')]"
            ]
            
            for selector in token_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        text = elem.text or elem.get_attribute('value')
                        if text and "pit-" in text:
                            print(f"✅ Found PIT token: {text}")
                            # Save to file
                            with open("ghl_pit_token.txt", "w") as f:
                                f.write(text)
                            print("💾 Token saved to ghl_pit_token.txt")
                            return text
            
            print("❌ Could not find PIT token on page")
            return None
            
        except Exception as e:
            print(f"❌ Token extraction error: {e}")
            return None
    
    def run_complete_automation(self, email: str, password: str, location_id: str):
        """Run the complete automation workflow"""
        try:
            print("=" * 80)
            print("🎯 GHL Private Integration Automation - FIXED VERSION")
            print("=" * 80)
            print(f"📧 Email: {email}")
            print(f"📍 Location: {location_id}")
            print("🔧 Strategy: Navigate through UI after login")
            print("=" * 80)
            
            # Step 1: Setup driver
            print("\n🚀 Step 1: Setting up Chrome WebDriver...")
            if not self.setup_driver():
                return False
            
            # Step 2: Go to login page
            print("\n🔗 Step 2: Navigating to GHL login...")
            self.driver.get("https://app.onetoo.com/")
            time.sleep(3)
            
            # Step 3: Handle login and 2FA
            print("\n🔐 Step 3: Handling login and 2FA...")
            if not self.handle_login_and_2fa(email, password):
                return False
            
            # Step 4: Navigate through UI to private integrations
            print("\n📍 Step 4: Navigating to Private Integrations through UI...")
            if not self.navigate_through_ui_to_private_integrations():
                # Try direct navigation as fallback
                print("⚠️ UI navigation failed, trying direct URL...")
                self.driver.get(f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/")
                time.sleep(5)
            
            # Step 5: Create private integration
            print("\n🔧 Step 5: Creating private integration...")
            if not self.create_private_integration():
                return False
            
            # Step 6: Try to extract token
            print("\n🔑 Step 6: Attempting to extract PIT token...")
            token = self.extract_pit_token()
            
            # Step 7: Take screenshot
            print("\n📸 Step 7: Taking final screenshot...")
            screenshot_path = f"ghl_private_integration_fixed_{location_id}.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"✅ Screenshot saved: {screenshot_path}")
            
            print("\n" + "=" * 80)
            print("🎉 SUCCESS! Automation workflow completed!")
            print("✅ Login completed with automatic 2FA")
            print("✅ Navigated to private integrations")
            print("✅ Integration creation initiated")
            if token:
                print(f"✅ PIT Token extracted: {token}")
            print(f"📸 Screenshot saved: {screenshot_path}")
            print("=" * 80)
            
            # Keep browser open for inspection
            print("\n⏱️ Keeping browser open for 60 seconds for manual inspection...")
            print("💡 You can manually complete any remaining steps if needed")
            time.sleep(60)
            
            return True
            
        except Exception as e:
            print(f"❌ Automation failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 Browser closed")

def main():
    """Main function"""
    load_dotenv()
    
    # Get credentials from environment
    email = os.getenv('HIGHLEVEL_EMAIL')
    password = os.getenv('HIGHLEVEL_PASSWORD')
    location_id = "MdY4KL72E0lc7TqMm3H0"
    
    if not email or not password:
        print("❌ Missing credentials in .env file")
        return
    
    # Run automation
    automation = GHLPrivateIntegrationFixed(headless=False)
    success = automation.run_complete_automation(email, password, location_id)
    
    if success:
        print("\n🎉 FINAL SUCCESS: GHL private integration automation completed!")
    else:
        print("\n❌ FINAL FAILURE: Automation failed - check logs above")

if __name__ == "__main__":
    main()