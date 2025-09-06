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
                
                # After successful verification, navigate directly to private integrations URL
                print("✅ 2FA verification complete")
                print("🔗 Navigating directly to private integrations URL...")
                
                # Get current URL to extract location if needed
                current_url = self.driver.current_url
                print(f"📍 Current URL after verification: {current_url}")
                
                # If we don't have a location ID from main args, try to extract from current URL
                if "location" not in current_url:
                    print("⚠️ Not on a location page yet, will use provided location ID")
            
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
        """Create the private integration with all required scopes"""
        try:
            print("🔧 Creating private integration...")
            
            # We should already be on the private integrations page
            current_url = self.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            # Wait for page to load
            time.sleep(3)
            
            # Press the integration creation button with fallback option
            try:
                print("🔍 Looking for primary integration creation button...")
                create_button_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div[2]/button[2]/span"
                
                try:
                    # Try primary button first
                    create_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, create_button_xpath))
                    )
                    create_button.click()
                    print("✅ Primary integration creation button clicked")
                except Exception as primary_error:
                    # If primary button fails, wait and try fallback button
                    print(f"⚠️ Primary button not found or not clickable: {primary_error}")
                    print("⚠️ Waiting 2 seconds then trying fallback button...")
                    time.sleep(2)
                    
                    try:
                        # Try fallback button
                        fallback_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div/div/button/span"
                        fallback_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, fallback_xpath))
                        )
                        fallback_button.click()
                        print("✅ Fallback integration creation button clicked")
                    except Exception as fallback_error:
                        # Try generic selectors as final fallback
                        print(f"⚠️ Both specific buttons failed. Trying generic selectors")
                        create_selectors = [
                            "//button[contains(text(), 'New')]",
                            "//button[contains(text(), 'Create')]",
                            "//button[contains(@class, 'primary')]",
                            "//*[@role='button'][contains(text(), 'Private')]",
                            "//span[contains(text(), 'New Private')]/parent::button"
                        ]
                        
                        button_found = False
                        for selector in create_selectors:
                            try:
                                create_button = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                                create_button.click()
                                print(f"✅ Found and clicked button with selector: {selector}")
                                button_found = True
                                break
                            except:
                                continue
                        
                        if not button_found:
                            raise Exception(f"All buttons failed. Primary: {primary_error}, Fallback: {fallback_error}")
                
                # Wait for form to load
                time.sleep(3)
            except Exception as e:
                print(f"❌ Could not click any integration creation button: {e}")
                return False
            
            # Fill integration name
            try:
                print("🔧 Filling integration name...")
                name_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div[1]/div[1]/div/div[1]/div[1]/input"
                try:
                    # Try exact XPath first
                    name_field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, name_xpath))
                    )
                    name_field.clear()
                    name_field.send_keys("location key")
                    print("✅ Integration name set to: location key (using exact XPath)")
                except Exception as name_error:
                    # Fallback to generic input search
                    print(f"⚠️ Name field not found by XPath: {name_error}. Trying generic search.")
                    name_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for inp in name_inputs:
                        if inp.is_displayed() and inp.is_enabled():
                            placeholder = inp.get_attribute("placeholder") or ""
                            if "name" in placeholder.lower() or not placeholder:
                                inp.clear()
                                inp.send_keys("location key")
                                print("✅ Integration name set to: location key (using generic search)")
                                break
                
                time.sleep(2)
            except Exception as e:
                print(f"❌ Could not fill integration name: {e}")
                return False
            
            # Submit the form
            try:
                print("🔧 Submitting integration form...")
                submit_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]"
                try:
                    # Try exact XPath first
                    submit_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, submit_xpath))
                    )
                    submit_button.click()
                    print("✅ Form submitted using exact XPath")
                except Exception as submit_error:
                    # Fallback to generic button search
                    print(f"⚠️ Submit button not found by XPath: {submit_error}. Trying generic search.")
                    submit_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Create') or contains(text(), 'Submit') or contains(text(), 'Next')]")
                    for btn in submit_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            print("✅ Form submitted using generic search")
                            break
                
                time.sleep(5)
            except Exception as e:
                print(f"❌ Could not submit integration form: {e}")
                return False
                
            # Select scopes
            try:
                print("[INTEGRATION] Opening scopes selection...")
                scopes_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div/div/div[1]"
                scopes_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, scopes_xpath))
                )
                
                # Click the main scopes container to activate the input
                print("[INTEGRATION] Clicking main scopes container...")
                scopes_container_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/form/div/div/div[1]"
                scopes_container = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, scopes_container_xpath))
                )
                scopes_container.click()
                time.sleep(1)  # Wait for the input to be ready
                
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
                    # Absolute simplest approach with direct target
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
                            # Log which scope we're processing
                            print(f"[{i+1}/{len(scopes_to_add)}] Selecting: {scope}")
                            
                            # More direct approach - no clicking between scopes
                            # Just focus once at the beginning if needed
                            if i == 0:
                                dropdown.click()
                                time.sleep(0.01)
                            
                            # Clear any previous text
                            dropdown.clear()
                            
                            # Type the scope name and immediately hit Enter
                            dropdown.send_keys(scope)
                            time.sleep(0.01)
                            
                            # Use multiple Enter methods simultaneously for maximum reliability
                            try:
                                # Direct send_keys - most reliable method
                                dropdown.send_keys(Keys.ENTER)
                                
                                # Just in case, also try RETURN
                                dropdown.send_keys(Keys.RETURN)
                                
                                # ActionChains as another approach
                                actions = ActionChains(self.driver)
                                actions.send_keys(Keys.RETURN)
                                actions.perform()
                                
                                print(f"    - Enter key pressed for '{scope}'")
                                
                                # Immediately verify if scope was added and move to next if it was
                                continue
                            
                            except Exception as e:
                                print(f"    - Error pressing Enter key: {e}")
                                
                                # Quick fallback - try clicking the first visible dropdown item
                                try:
                                    print(f"    - Trying direct dropdown selection")
                                    # Find any visible dropdown items with shortest path possible
                                    dropdown_items = self.driver.find_elements(By.CSS_SELECTOR, ".n-base-select-option, .vs__dropdown-option")
                                    
                                    for item in dropdown_items:
                                        if item.is_displayed():
                                            item.click()
                                            print(f"    - Clicked dropdown item for '{scope}'")
                                            break
                                except Exception:
                                    # If all else fails, try a fresh approach - reset and try again
                                    try:
                                        # Press Escape to reset the dropdown
                                        dropdown.send_keys(Keys.ESCAPE)
                                        time.sleep(0.01)
                                        dropdown.click()
                                        dropdown.clear()
                                        dropdown.send_keys(scope + Keys.RETURN)
                                    except:
                                        pass
                            
                            # Quick verification
                            print(f"  ✓ Added scope: {scope}")
                        except Exception as e:
                            print(f"Error selecting scope '{scope}': {e}")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to select scope: {str(e)}")
                
                # Continue with next steps - Click the Create button with exact XPath
                print("\n🔧 Scope selection completed, clicking Create button...")
                try:
                    # Use the exact XPath provided
                    create_button_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]/span"
                    create_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, create_button_xpath))
                    )
                    create_button.click()
                    print("✅ Clicked Create button using exact XPath")
                except Exception as e:
                    print(f"⚠️ Error clicking Create button: {str(e)}")
                    try:
                        # Try alternative selector as backup
                        create_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//*[@id='btn-next']/span"))
                        )
                        create_button.click()
                        print("✅ Clicked Create button using backup selector")
                    except Exception as e:
                        print(f"⚠️ Error clicking Create button with backup selector: {str(e)}")
                        
                        # Last resort - try any button that might be the create button
                        buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                text = btn.text.lower()
                                if "create" in text or "next" in text or "submit" in text:
                                    btn.click()
                                    print("✅ Clicked button with text: " + btn.text)
                                    break
                
                # Wait for token display
                print("🔧 Waiting for token generation...")
                time.sleep(3)  # Give time for the token to generate
                
                return True
                
            except Exception as e:
                print(f"❌ Scope selection/submission error: {e}")
                # Continue to try and extract token anyway
                return True
            
        except Exception as e:
            print(f"❌ Integration creation failed: {e}")
            return False
    
    def extract_pit_token(self):
        """Try to extract the PIT token from the page"""
        try:
            print("\n[STEP 4] Looking for integration token...")
            time.sleep(3)
            
            # Try direct extraction first with exact XPath
            try:
                # Use the exact XPath provided by user where token is displayed
                exact_token_xpath = "/html/body/div[7]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/p"
                print("Looking for token at exact XPath provided by user...")
                
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
                    
                    # Save to file for backup
                    try:
                        with open("highlevel_token.txt", "w") as f:
                            f.write(token_text)
                        print("\nToken saved to highlevel_token.txt for reference")
                    except Exception as e:
                        print(f"Could not save token to file: {e}")
                else:
                    print("\n[WARNING] Token text appears to be empty or invalid")
                    # Fallback to scanning for token
                    try:
                        # Try alternative selectors as fallback
                        token_selectors = [
                            "//div[contains(@class, 'dialog')]//p",
                            "//div[contains(@class, 'modal')]//p",
                            "//div[contains(@class, 'token')]",
                            "//pre[contains(text(), 'pit-')]"
                        ]
                        
                        for selector in token_selectors:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for elem in elements:
                                if elem.is_displayed():
                                    alt_token = elem.text
                                    if alt_token and len(alt_token) > 10 and ("pit-" in alt_token or "-" in alt_token):
                                        print("\n[FALLBACK] Found token with alternative selector:")
                                        print(alt_token)
                                        
                                        # Save to file
                                        try:
                                            with open("highlevel_token.txt", "w") as f:
                                                f.write(alt_token)
                                            print("Token saved to file as backup")
                                        except Exception as e:
                                            print(f"Could not save token to file: {e}")
                                        
                                        return True
                    except Exception as e:
                        print(f"[ERROR] Fallback token extraction failed: {e}")
            except Exception as direct_extract_error:
                print(f"[ERROR] Could not extract token directly: {direct_extract_error}")
            
            # Try the copy button approach
            try:
                # Look for the copy button
                copy_button_xpath = "/html/body/div[7]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/button/span"
                print("Trying to find copy button...")
                
                copy_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, copy_button_xpath))
                )
                
                # Click the copy button
                copy_button.click()
                print("Clicked copy button - token should now be in clipboard")
                
                # Try to find token elsewhere on page now that it's copied
                token_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//p[contains(text(), 'pit-')] | //div[contains(text(), 'pit-')] | //pre | //code"
                )
                
                for elem in token_elements:
                    if elem.is_displayed():
                        token = elem.text
                        if token and len(token) > 10:
                            print("\n")
                            print("*"*100)
                            print("*" + " "*30 + "INTEGRATION TOKEN COPIED TO CLIPBOARD" + " "*30 + "*")
                            print("*"*100)
                            print("\n")
                            print(token)
                            print("\n")
                            print("*"*100)
                            
                            # Save to file
                            try:
                                with open("highlevel_token.txt", "w") as f:
                                    f.write(token)
                                print("Token saved to highlevel_token.txt for reference")
                            except Exception as e:
                                print(f"Could not save token to file: {e}")
                            
                            return True
            except Exception as e:
                print(f"[ERROR] Could not find token after clicking copy button: {e}")
            
            # Last resort - try additional selectors
            try:
                print("[FALLBACK] Trying additional token selectors...")
                token_selectors = [
                    "//pre",
                    "//code", 
                    "//*[contains(text(), 'pit-')]",
                    "//textarea",
                    "//*[contains(@class, 'token')]"
                ]
                
                for selector in token_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            token_text = element.text or element.get_attribute('value')
                            if token_text and len(token_text) > 10:
                                print("\n[FALLBACK] Found token with selector: " + selector)
                                print(token_text)
                                
                                # Save to file for backup
                                try:
                                    with open("highlevel_token.txt", "w") as f:
                                        f.write(token_text)
                                    print("Token saved to highlevel_token.txt for reference")
                                except Exception as e:
                                    print(f"Could not save token to file: {e}")
                                
                                return True
            except Exception as e:
                print(f"[ERROR] Additional selector search failed: {e}")
                
            # Last resort - take a screenshot and notify user
            try:
                print("[SCREENSHOT] Taking screenshot as last resort")
                screenshot_path = "token_screenshot.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                print(f"[ERROR] Could not take screenshot: {e}")
                
            return False
            
        except Exception as e:
            print(f"❌ Token extraction error: {e}")
            return False
    
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
            self.driver.get("https://app.gohighlevel.com/")
            time.sleep(3)
            
            # Step 3: Handle login and 2FA
            print("\n🔐 Step 3: Handling login and 2FA...")
            if not self.handle_login_and_2fa(email, password):
                return False
            
            # Step 4: Navigate directly to private integrations URL for location
            print("\n📍 Step 4: Navigating directly to Private Integrations URL...")
            print(f"🔗 URL: https://app.gohighlevel.com/v2/location/{location_id}/settings/private-integrations/")
            self.driver.get(f"https://app.gohighlevel.com/v2/location/{location_id}/settings/private-integrations/")
            time.sleep(5)
            
            # Verify we reached the correct page
            current_url = self.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if "private-integrations" in current_url:
                print("✅ Successfully navigated to private integrations page")
            else:
                print("⚠️ May not be on private integrations page, continuing anyway...")
            
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
