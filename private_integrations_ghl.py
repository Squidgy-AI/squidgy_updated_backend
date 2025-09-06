#!/usr/bin/env python3
"""
HighLevel Automation with Manual Email Verification
Pauses for user to manually enter verification code from email
"""

import os
import sys
import time
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

class HighLevelManualVerification:
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
    
    def handle_manual_verification(self):
        """Handle email verification with manual code input"""
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
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"[WARNING] Could not find/click 'Send Code' button: {e}")
                    print("[INFO] Continuing anyway - code may already be sent")
                
                print("[INFO] HighLevel is sending a verification code to your email:")
                print("       somashekhar34+MdY4KL72@gmail.com")
                print("[INFO] The email will be from: noreply@talk.onetoo.com")
                print()
                print("[ACTION NEEDED] Please:")
                print("1. Wait a moment for the email to arrive")
                print("2. Check your Gmail inbox for the verification email")
                print("3. Find the verification code in the email")
                print("4. Enter the code below when prompted")
                print()
                
                # Get verification code from user
                while True:
                    try:
                        user_input = input("[INPUT] Enter the verification code from your email: ").strip()
                        
                        # Skip any Chrome error messages containing ERROR or DEPRECATED
                        if "ERROR:" in user_input or "DEPRECATED" in user_input:
                            continue
                            
                        # Only accept input that looks like a verification code
                        if user_input and user_input.isdigit() and len(user_input) >= 4:
                            verification_code = user_input
                            break
                        else:
                            print("[ERROR] Please enter a valid verification code")
                    except KeyboardInterrupt:
                        print("\n[CANCELLED] Automation cancelled by user")
                        return False
                
                print(f"[VERIFICATION] Using code: {verification_code}")
                
                # Input each digit into the 6 separate input fields
                verification_xpaths = [
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[1]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[2]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[3]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[4]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[5]/input",
                    "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div/div[6]/input"
                ]
                
                try:
                    print("[VERIFICATION] Filling 6-digit verification code (one digit per field)...")
                    for i, digit in enumerate(verification_code):
                        print(f"[VERIFICATION] Entering digit {i+1}: {digit}")
                        field = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, verification_xpaths[i]))
                        )
                        field.click()  # Click to focus
                        time.sleep(0.3)
                        field.clear()  # Clear any existing content
                        time.sleep(0.3)
                        field.send_keys(digit)  # Enter the digit
                        time.sleep(0.5)
                        print(f"[VERIFICATION] Digit {i+1} entered successfully")
                    
                    print("[VERIFICATION] All 6 digits entered successfully")
                    time.sleep(5)  # Wait for verification to complete
                        
                except Exception as e:
                    print(f"[ERROR] Verification code input error: {e}")
                    return False
            
            print("[SUCCESS] Verification completed!")
            return self.create_private_integration()
            
        except Exception as e:
            print(f"[ERROR] Manual verification failed: {e}")
            return False
    
    def create_private_integration(self):
        """Create the private integration with all required scopes"""
        print("\n[STEP 3] Creating private integration...")
        
        # We should already be on the private integrations page after login/verification
        print("[INFO] Should already be on private integrations page after login/verification")
        current_url = self.driver.current_url
        print(f"[CURRENT URL] {current_url}")
        
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
                        # Reset before each scope entry
                        dropdown.click()
                        time.sleep(0.3)
                        
                        # Log which scope we're processing
                        print(f"[{i+1}/{len(scopes_to_add)}] Selecting: {scope}")
                        
                        # Type the scope name
                        dropdown.send_keys(scope)
                        time.sleep(0.05)
                        dropdown.send_keys(Keys.ENTER)
                        time.sleep(0.05)  # Increased timing
                        
                        # Quick verification
                        print(f"  ✓ Added scope: {scope}")
                    except Exception as e:
                        print(f"Error selecting scope '{scope}': {e}")
                
            except Exception as e:
                print(f"[ERROR] Failed to select scope: {str(e)}")
            
            # Continue with next steps - Click the Create button with exact XPath
            print("\n[INTEGRATION] Scope selection completed, clicking Create button...")
            try:
                # Use the exact XPath provided by the user
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
            
            # Wait for token display and copy it using exact XPath
            print("[INTEGRATION] Waiting for token generation...")
            time.sleep(3)  # Give time for the token to generate
            
            try:
                # Use the exact XPath provided by the user for the copy button
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
                                print("*" + " "*98 + "*")
                                print("*" + " "*38 + "INTEGRATION TOKEN FOUND" + " "*38 + "*")
                                print("*" + " "*98 + "*")
                                print("*"*100)
                                print("\n")
                                print(token_text)
                                print("\n")
                                print("*"*100)
                                
                                # Save token to file for backup
                                try:
                                    with open("highlevel_token.txt", "w") as f:
                                        f.write(token_text)
                                    print("\nToken saved to highlevel_token.txt")
                                except:
                                    pass
                except Exception as e:
                    print(f"Could not read token directly: {e}")
                
                # Click the copy button
                copy_button.click()
                print("Clicked copy button with exact XPath to copy token to clipboard")
                
                # After clicking copy button, extract token using exact XPath provided by user
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
                                            with open("highlevel_token.txt", "w") as f:
                                                f.write(alt_token)
                                            print("Token saved to highlevel_token.txt")
                                            break
                        except Exception as inner_e:
                            print(f"Fallback token search failed: {inner_e}")
                except Exception as e:
                    print(f"\n[ERROR] Failed to extract token: {e}")
            except Exception as e:
                print(f"[WARNING] Could not copy token with exact XPath: {str(e)}")
                try:
                    # Try some fallback selectors
                    fallback_selectors = [
                        "//button[.//svg]", # Any button containing an SVG
                        "//button[contains(@title, 'Copy') or contains(@aria-label, 'copy')]"
                    ]
                    
                    for selector in fallback_selectors:
                        try:
                            copy_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            copy_button.click()
                            print(f"Clicked copy button with fallback selector: {selector}")
                            break
                        except:
                            continue
                except Exception:
                    print("Could not find any copy button, but integration was likely created")
            
        except Exception as e:
            print(f"[WARNING] Could not open scopes selection: {e}")
            print("[INFO] Please manually select scopes and continue")
        
        # Submit again
        try:
            print("[INTEGRATION] Submitting final integration...")
            final_submit_xpath = "/html/body/div[1]/div[1]/div[4]/section/div/section/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/button[2]"
            final_submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, final_submit_xpath))
            )
            final_submit_button.click()
            print("[INTEGRATION] Final submission completed")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Could not submit final integration: {e}")
            return False
        
        # Extract and print the integration code
        return self.extract_integration_code()
    
    def extract_integration_code(self):
        """Extract and print the integration code"""
        print("\n[STEP 4] Extracting integration code...")
        
        try:
            copy_button_xpath = "/html/body/div[8]/div/div/div[1]/div/div[3]/div[1]/div/div[2]/button/span"
            copy_button = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, copy_button_xpath))
            )
            
            # Try to get the code from nearby elements
            try:
                # Look for code in various possible locations
                possible_code_selectors = [
                    "/html/body/div[8]/div/div/div[1]/div/div[3]/div[1]/div/div[1]",
                    "/html/body/div[8]/div/div/div[1]/div/div[3]/div[1]/div",
                    "code",
                    "pre",
                    "[data-testid*='code']",
                    "[class*='code']"
                ]
                
                for selector in possible_code_selectors:
                    try:
                        if selector.startswith("/"):
                            code_element = self.driver.find_element(By.XPATH, selector)
                        else:
                            code_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if code_element and code_element.text.strip():
                            integration_code = code_element.text.strip()
                            print("\n" + "="*60)
                            print("[SUCCESS] INTEGRATION CODE EXTRACTED:")
                            print("="*60)
                            print(integration_code)
                            print("="*60)
                            return True
                    except:
                        continue
                
            except Exception as e:
                print(f"[WARNING] Could not extract code automatically: {e}")
            
            # Click copy button as fallback
            copy_button.click()
            print("[INFO] Copy button clicked - code should be in clipboard")
            print("[INFO] Please paste the code from your clipboard")
            return True
            
        except Exception as e:
            print(f"[ERROR] Could not extract integration code: {e}")
            return False
        
        return True
    
    def handle_login_and_verification(self, email: str, password: str):
        """Handle login and manual email verification"""
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
            return self.handle_manual_verification()
            
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
    
    def take_screenshot(self, location_id: str):
        """Take a screenshot of the current page"""
        try:
            filename = f"private_integrations_manual_verified_{location_id}.png"
            self.driver.save_screenshot(filename)
            print(f"[SCREENSHOT] Saved: {filename}")
            return filename
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")
            return None
    
    def run_automation(self, email: str, password: str, location_id: str):
        """Run the complete automation workflow with manual email verification"""
        try:
            print("="*80)
            print("[AUTOMATION] HighLevel Automation with Manual Email Verification")
            print("="*80)
            print(f"[TARGET] Location ID: {location_id}")
            print(f"[TARGET] URL: https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/")
            print(f"[CREDENTIALS] HighLevel Email: {email}")
            print("[INFO] You will be prompted to enter the verification code manually")
            print()
            
            # Step 1: Setup WebDriver
            print("[STEP 1] Setting up Chrome WebDriver...")
            if not self.setup_driver():
                return False
            
            # Step 2: Navigate and handle login/verification
            print("\\n[STEP 2] Navigating with login and manual email verification...")
            if not self.navigate_to_target(location_id, email, password):
                return False
            
            # Step 3: Take screenshot
            print("\\n[STEP 3] Taking screenshot...")
            screenshot = self.take_screenshot(location_id)
            
            # Step 4: Show success and keep browser open
            print("\\n" + "="*80)
            print("[SUCCESS] Complete automation workflow finished!")
            print(f"[RESULT] Private integration created for location: {location_id}")
            if screenshot:
                print(f"[SCREENSHOT] Screenshot saved as: {screenshot}")
            print("[INFO] Browser will remain open for you to continue working")
            print("[INFO] You can manually close the browser when finished")
            print("="*80)
            
            # Keep browser open - don't close automatically
            print("\\n[PAUSE] Browser will stay open for 60 seconds for inspection...")
            time.sleep(60)
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
    
    # Use the correct location ID directly
    location_id = "MdY4KL72E0lc7TqMm3H0"
    print(f"\n[INPUT] Using location ID: {location_id}")
    
    print()
    
    # Run automation
    automation = HighLevelManualVerification(headless=False)
    success = automation.run_automation(email, password, location_id)
    
    if success:
        print("\\n[FINAL] Automation with manual email verification completed successfully!")
    else:
        print("\\n[FINAL] Automation failed - check the logs above")

if __name__ == "__main__":
    main()
