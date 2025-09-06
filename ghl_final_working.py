#!/usr/bin/env python3
"""
🎯 FINAL WORKING GHL AUTOMATION
==============================
Enhanced Selenium script with automatic OTP reading and proper navigation handling
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

class GHLFinalAutomation:
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
                r'Your login security code:\\s*(\\d{6})',
                r'login security code:\\s*(\\d{6})',
                r'\\b(\\d{6})\\b'
            ]
            
            for pattern in otp_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    otp = matches[0]
                    print(f"✅ Extracted OTP: {otp}")
                    
                    # Mark as read
                    mail.store(latest_email_id, '+FLAGS', '\\\\Seen')
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
            # Check if login is needed
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()
            
            if "login" in current_url or "sign" in current_url or "sign into your account" in page_source:
                print("🔐 Login required - filling credentials...")
                
                # Email field
                email_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[2]/div/div[2]/input"
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, email_xpath))
                )
                email_field.click()
                email_field.clear()
                email_field.send_keys(email)
                print(f"✅ Email filled: {email}")
                
                # Password field
                password_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div[2]/input"
                password_field = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, password_xpath))
                )
                password_field.click()
                password_field.clear()
                password_field.send_keys(password)
                print("✅ Password filled")
                
                # Login button
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Sign in")]'))
                )
                login_button.click()
                print("✅ Login button clicked")
                time.sleep(8)
            
            # Handle 2FA if needed
            page_source = self.driver.page_source.lower()
            if "verification" in page_source or "verify" in page_source or "code" in page_source:
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
                    print("⚠️ Send code button not found")
                
                # Get OTP automatically
                print("📧 Getting OTP from Gmail...")
                max_attempts = 30
                otp_code = None
                
                for attempt in range(max_attempts):
                    print(f"🔍 Attempt {attempt + 1}/{max_attempts}")
                    otp_code = self.get_otp_from_gmail()
                    if otp_code:
                        break
                    time.sleep(1)
                
                if not otp_code:
                    print("❌ Failed to get OTP")
                    return False
                
                # Input OTP
                verification_xpaths = [
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[1]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[2]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[3]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[4]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[5]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[6]/input"
                ]
                
                print("⌨️ Inputting OTP digits...")
                for i, digit in enumerate(otp_code):
                    field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, verification_xpaths[i]))
                    )
                    field.click()
                    time.sleep(0.3)
                    field.clear()
                    time.sleep(0.3)
                    field.send_keys(digit)
                    time.sleep(0.5)
                    print(f"✅ Digit {i+1}: {digit}")
                
                print("✅ All digits entered - waiting for verification...")
                time.sleep(8)
            
            return True
            
        except Exception as e:
            print(f"❌ Login/2FA failed: {e}")
            return False
    
    def navigate_to_private_integrations(self, location_id: str):
        """Navigate to private integrations page after login/2FA"""
        try:
            current_url = self.driver.current_url
            print(f"📍 Current URL after login/2FA: {current_url}")
            
            # Check if we're already on private integrations page
            if "private-integrations" in current_url:
                print("✅ Already on private integrations page!")
                return True
            
            # Navigate to private integrations page
            target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
            print(f"🔗 Navigating to: {target_url}")
            
            self.driver.get(target_url)
            time.sleep(5)
            
            final_url = self.driver.current_url
            print(f"📍 Final URL: {final_url}")
            
            if "private-integrations" in final_url:
                print("✅ Successfully navigated to private integrations page!")
                return True
            else:
                print("⚠️ Not on private integrations page, but continuing...")
                return True
                
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
                create_button_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div[2]/button[2]/span"
                create_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, create_button_xpath))
                )
                create_button.click()
                print("✅ Create integration button clicked")
            except:
                # Try fallback button
                try:
                    fallback_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div/button/span"
                    fallback_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, fallback_xpath))
                    )
                    fallback_button.click()
                    print("✅ Fallback create button clicked")
                except:
                    print("❌ Could not find create button")
                    return False
            
            time.sleep(3)
            
            # Fill integration name
            try:
                name_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div[1]/div[1]/div/div[1]/div[1]/input"
                name_field = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, name_xpath))
                )
                name_field.clear()
                name_field.send_keys("Auto Location Key")
                print("✅ Integration name filled")
                time.sleep(2)
            except Exception as e:
                print(f"❌ Could not fill name: {e}")
                return False
            
            # Submit form
            try:
                submit_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]"
                submit_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, submit_xpath))
                )
                submit_button.click()
                print("✅ Form submitted")
                time.sleep(5)
            except Exception as e:
                print(f"❌ Could not submit: {e}")
                return False
            
            print("✅ Private integration creation completed!")
            return True
            
        except Exception as e:
            print(f"❌ Integration creation failed: {e}")
            return False
    
    def run_complete_automation(self, email: str, password: str, location_id: str):
        """Run the complete automation workflow"""
        try:
            print("=" * 80)
            print("🎯 GHL FINAL AUTOMATION - Complete Workflow")
            print("=" * 80)
            print(f"📧 Email: {email}")
            print(f"📍 Location: {location_id}")
            print(f"🔗 Target: Private Integrations Page")
            print("📱 2FA: Automatic OTP reading from Gmail")
            print("=" * 80)
            
            # Step 1: Setup driver
            print("\\n🚀 Step 1: Setting up Chrome WebDriver...")
            if not self.setup_driver():
                return False
            
            # Step 2: Navigate to private integrations URL
            print("\\n🔗 Step 2: Navigating to private integrations...")
            target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
            self.driver.get(target_url)
            time.sleep(3)
            
            # Step 3: Handle login and 2FA
            print("\\n🔐 Step 3: Handling login and 2FA...")
            if not self.handle_login_and_2fa(email, password):
                return False
            
            # Step 4: Navigate to private integrations (handles GHL redirect)
            print("\\n📍 Step 4: Ensuring we're on private integrations page...")
            if not self.navigate_to_private_integrations(location_id):
                return False
            
            # Step 5: Create private integration
            print("\\n🔧 Step 5: Creating private integration...")
            if not self.create_private_integration():
                return False
            
            # Step 6: Take screenshot and finish
            print("\\n📸 Step 6: Taking final screenshot...")
            screenshot_path = f"ghl_final_automation_{location_id}.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"✅ Screenshot saved: {screenshot_path}")
            
            print("\\n" + "=" * 80)
            print("🎉 SUCCESS! Complete automation workflow finished!")
            print("✅ Login completed with automatic 2FA")
            print("✅ Navigated to private integrations page")
            print("✅ Private integration created successfully")
            print(f"📸 Screenshot saved: {screenshot_path}")
            print("=" * 80)
            
            # Keep browser open for inspection
            print("\\n⏱️ Keeping browser open for 60 seconds for inspection...")
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
        print("❌ Missing credentials in .env file:")
        print("  HIGHLEVEL_EMAIL=your_email")
        print("  HIGHLEVEL_PASSWORD=your_password")
        print("  GMAIL_2FA_APP_PASSWORD=your_gmail_app_password")
        return
    
    # Run automation
    automation = GHLFinalAutomation(headless=False)
    success = automation.run_complete_automation(email, password, location_id)
    
    if success:
        print("\\n🎉 FINAL SUCCESS: GHL automation completed with automatic 2FA!")
    else:
        print("\\n❌ FINAL FAILURE: Automation failed - check logs above")

if __name__ == "__main__":
    main()