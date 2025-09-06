#!/usr/bin/env python3
"""
🔐 ENHANCED 2FA SERVICE FOR GMAIL
=================================
Handles GHL 2FA with Gmail email monitoring (simplified setup)
"""

import asyncio
import imaplib
import email
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from playwright.async_api import async_playwright, Page

def get_base_2fa_email():
    """Get the base email for 2FA access (without +extension)"""
    import os
    base_email = os.environ.get("GHL_AUTOMATION_2FA_EMAIL", "info@squidgy.net")
    return base_email

class GmailEmailConfig:
    """Configuration for Gmail email monitoring"""
    
    def __init__(self, location_id: str = None):
        # Gmail IMAP settings
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        
        # Dynamic Gmail configuration - use base email for 2FA access
        import os
        self.email_address = get_base_2fa_email()  # Use base email for 2FA access
        self.email_password = os.environ.get("GMAIL_2FA_APP_PASSWORD", "qfwfjrfedcjbzdam")
        self.account_id = "gmail"
        
        # COMMENTED OUT: Complex database account management for future use
        # try:
        #     from email_account_db_manager import get_email_account_for_integration
        #     account = get_email_account_for_integration(location_id)
        #     
        #     if account:
        #         self.email_address = account.email
        #         self.email_password = account.password
        #         self.account_id = str(account.account_number)
        #         self.account_db_id = account.id
        #     else:
        #         # Fallback to environment variables for development
        #         import os
        #         self.email_address = os.environ.get("OUTLOOK_2FA_EMAIL", "sa+01@squidgy.ai")
        #         self.email_password = os.environ.get("OUTLOOK_2FA_PASSWORD", "your-outlook-password")
        #         self.account_id = "01"
        #         self.account_db_id = None
        #         
        # except Exception as e:
        #     # Fallback in case of database issues
        #     import os
        #     print(f"⚠️ Using fallback email config due to: {e}")
        #     self.email_address = os.environ.get("OUTLOOK_2FA_EMAIL", "sa+01@squidgy.ai")
        #     self.email_password = os.environ.get("OUTLOOK_2FA_PASSWORD", "your-outlook-password")
        #     self.account_id = "01"
        #     self.account_db_id = None
        
        # Email patterns to search for (based on actual email received)
        self.sender_patterns = [
            "noreply@gohighlevel.com",
            "no-reply@gohighlevel.com", 
            "support@gohighlevel.com",
            "noreply@talk.onetoo.com",  # Specific GHL security code sender
        ]

class Enhanced2FAService:
    """Enhanced 2FA service with Gmail support (simplified)"""
    
    def __init__(self, email_config: GmailEmailConfig):
        self.email_config = email_config
        self._log_function = None
    
    def set_log_function(self, log_function):
        """Set external logging function"""
        self._log_function = log_function
    
    def _log(self, step: str, details: str = ""):
        """Internal logging method"""
        if self._log_function:
            self._log_function(f"[2FA] {step}", details)
        else:
            print(f"🔐 [2FA] {step}: {details}")
        
    async def handle_ghl_2fa_flow(self, page: Page) -> dict:
        """
        Complete GHL 2FA flow:
        1. Detect 2FA page
        2. Select email option
        3. Click send code
        4. Monitor email for OTP
        5. Input OTP in browser
        6. Complete login
        """
        
        try:
            self._log("🚀 2FA Start", "Beginning enhanced 2FA flow...")
            
            # Step 1: Wait for 2FA page to load
            self._log("⏱️ Page Analysis", "Analyzing current page for 2FA requirements...")
            await page.wait_for_timeout(3000)
            current_url = page.url
            page_content = await page.content()
            
            # Check for 2FA indicators in URL or page content
            is_2fa_page = (
                "2fa" in current_url.lower() or 
                "verify" in current_url.lower() or
                "Verify Security Code" in page_content or
                "Send code to email" in page_content or
                "security code" in page_content.lower()
            )
            
            if not is_2fa_page:
                self._log("ℹ️ No 2FA Needed", f"Current URL does not require 2FA: {current_url}")
                return {"success": True, "2fa_required": False}
            
            self._log("📱 2FA Detected", f"2FA page detected at: {current_url}")
            
            # Step 2: Select email option if multiple options available
            self._log("📧 Email Option", "Selecting email option for 2FA...")
            await self._select_email_2fa_option(page)
            
            # Step 3: Click send code button
            self._log("📤 Send Code", "Clicking send code button...")
            await self._click_send_code_button(page)
            
            # Step 4: Monitor email and input code
            self._log("👀 Email Monitor", "Starting email monitoring and code input process...")
            success = await self._monitor_and_input_code(page)
            
            if success:
                self._log("✅ 2FA Complete", "2FA process completed successfully!")
                return {"success": True, "2fa_required": True, "2fa_completed": True}
            else:
                self._log("❌ 2FA Failed", "2FA code input or verification failed")
                self._log("💡 Manual Input", "Please manually enter the 2FA code in browser")
                # Give user 3 minutes to manually input the code
                await asyncio.sleep(180)
                return {"success": True, "2fa_required": True, "manual_input": True}
                
        except Exception as e:
            print(f"💥 2FA flow error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _select_email_2fa_option(self, page: Page):
        """Select email option for 2FA"""
        
        print("📧 Looking for email 2FA option...")
        
        # Common selectors for email option
        email_selectors = [
            'text="Email"',
            'text="Send to Email"',
            'text="Email Address"',
            '[data-testid="email-option"]',
            '.email-option',
            'input[value="email"]',
            'button:has-text("Email")',
            'label:has-text("Email")'
        ]
        
        for selector in email_selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.click(selector)
                print(f"✅ Selected email option using: {selector}")
                await page.wait_for_timeout(1000)
                return
            except:
                continue
        
        print("ℹ️ Email option not found or already selected")
    
    async def _click_send_code_button(self, page: Page):
        """Click the send code button"""
        
        print("📤 Looking for send code button...")
        
        # Common selectors for send code button
        send_selectors = [
            'text="Send Security Code"',  # Exact text from GHL 2FA screen
            'text="Send Code"',
            'text="Send"',
            'text="Send Verification Code"',
            'text="Send OTP"',
            'button:has-text("Send Security Code")',
            'button:has-text("Send")',
            '[data-testid="send-code"]',
            '.send-code-btn',
            'button[type="submit"]',
            '.btn-primary:has-text("Send")'
        ]
        
        for selector in send_selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.click(selector)
                print(f"✅ Clicked send code button: {selector}")
                await page.wait_for_timeout(2000)
                return
            except:
                continue
        
        print("ℹ️ Send code button not found or already clicked")
    
    async def _monitor_and_input_code(self, page: Page) -> bool:
        """Monitor email for OTP and input it in browser - FAST & RELIABLE"""
        
        print("⚡ Starting FAST email monitoring for OTP...")
        
        # Extended timeout for production reliability
        max_attempts = 120  # 2 minutes total
        
        for attempt in range(max_attempts):
            self._log("📧 Quick Check", f"Fast OTP check ({attempt + 1}/{max_attempts})...")
            
            # Get OTP from email
            otp_code = await self._get_otp_from_gmail()
            
            if otp_code:
                self._log("🎯 OTP FOUND!", f"GOT IT: {otp_code} - Inputting immediately!")
                
                # Input the code in browser IMMEDIATELY with multiple attempts
                for input_attempt in range(3):  # Try 3 times quickly
                    self._log("⚡ Rapid Input", f"Attempt {input_attempt + 1}: Inputting {otp_code}")
                    success = await self._input_otp_in_browser(page, otp_code)
                    
                    if success:
                        self._log("✅ OTP SUCCESS!", "Code entered successfully!")
                        return True
                    else:
                        self._log("🔄 Retry", f"Input attempt {input_attempt + 1} failed, trying again...")
                        await asyncio.sleep(0.5)  # Very short delay between attempts
                
                self._log("❌ Input Failed", f"Could not input {otp_code} after 3 attempts")
                return False
            else:
                self._log("🔍 Scanning...", f"Checking... ({attempt + 1})")
            
            await asyncio.sleep(1)  # Check every 1 second (faster)
        
        self._log("⏰ Fast Timeout", f"No OTP found in {max_attempts} seconds")
        return False
    
    async def _get_otp_from_gmail(self) -> Optional[str]:
        """Get OTP code from Gmail email - FOCUS ON FRESH UNSEEN EMAILS ONLY"""
        
        try:
            # Connect to Gmail (using same config as working test script)
            import os
            from datetime import datetime, timedelta
            
            email_address = get_base_2fa_email()  # Use base email for 2FA access
            email_password = os.environ.get("GMAIL_2FA_APP_PASSWORD", "ytmfxlelgyojxjmf")
            
            # Check if we have valid Gmail credentials  
            if email_password == "your-app-password-here":
                print("⚠️ No valid Gmail App Password configured")
                print("💡 Please set GMAIL_2FA_APP_PASSWORD environment variable with a valid Gmail App Password")
                print("📝 Generate one at: https://myaccount.google.com/apppasswords")
                return None
            
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(email_address, email_password)
            mail.select('inbox')
            
            print("🔍 SMART SEARCH: Getting the ABSOLUTE LATEST unread security code...")
            
            # Step 1: Search for ALL unread emails from GHL security sender
            search_criteria = '(FROM "noreply@talk.onetoo.com" UNSEEN SUBJECT "Login security code")'
            result, data = mail.search(None, search_criteria)
            
            if result != 'OK' or not data[0]:
                print("📧 No unread security code emails found")
                return None
            
            email_ids = data[0].split()
            print(f"📨 Found {len(email_ids)} unread security code email(s)")
            
            if not email_ids:
                return None
            
            # Step 2: Get the HIGHEST email ID (newest in Gmail)
            # In Gmail, higher email IDs = newer emails
            latest_email_id = max(email_ids, key=lambda x: int(x))
            print(f"🎯 Selected LATEST email ID: {latest_email_id}")
            
            # Step 3: Fetch and process the latest email
            try:
                result, msg_data = mail.fetch(latest_email_id, '(RFC822)')
                if result != 'OK':
                    print("❌ Failed to fetch latest email")
                    return None
                
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Get email details
                email_date_str = msg.get('Date', '')
                email_subject = msg.get('Subject', '')
                print(f"📧 Latest email: {email_subject}")
                print(f"📅 Date: {email_date_str}")
                
                # Extract email body
                body = self._extract_email_body(msg)
                print(f"📄 Email body preview: {body[:200]}...")
                
                # Extract OTP using the exact pattern from your emails
                otp = self._extract_otp_from_body(body)
                
                if otp:
                    print(f"🎯 EXTRACTED OTP: {otp}")
                    
                    # Mark as read to avoid reusing
                    mail.store(latest_email_id, '+FLAGS', '\\Seen')
                    mail.close()
                    mail.logout()
                    
                    return otp
                else:
                    print("❌ No OTP found in latest email body")
                    print(f"❌ Full body: {body}")
                    
            except Exception as e:
                print(f"❌ Error processing latest email: {e}")
                return None
            
            print("📧 No FRESH OTP found in any security code emails")
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"📧 Email check error: {e}")
            import traceback
            print(f"📧 Full error: {traceback.format_exc()}")
        
        return None
    
    def _extract_email_body(self, msg) -> str:
        """Extract body text from email message"""
        
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
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
    
    def _extract_otp_from_body(self, body: str) -> Optional[str]:
        """Extract OTP code from email body - matches your exact email format"""
        
        # Patterns based on your actual emails:
        # "Your login security code: 274526"
        otp_patterns = [
            r'Your login security code:\s*(\d{6})',     # Exact match from your emails
            r'login security code:\s*(\d{6})',          # Variation
            r'security code:\s*(\d{6})',                # General security code
            r'code:\s*(\d{6})',                         # Simple code pattern
            r'\b(\d{6})\b',                             # Any 6-digit number as fallback
        ]
        
        # Don't convert to lowercase to preserve exact matching
        print(f"🔍 Searching for OTP in body: {repr(body[:200])}")
        
        for i, pattern in enumerate(otp_patterns, 1):
            print(f"🔍 Trying pattern {i}: {pattern}")
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                for match in matches:
                    if len(match) == 6 and match.isdigit():  # Must be exactly 6 digits
                        print(f"✅ FOUND OTP with pattern {i}: {match}")
                        return match
            print(f"   ❌ Pattern {i} - no match")
        
        print("❌ No 6-digit OTP found with any pattern")
        return None
    
    async def _input_otp_in_browser(self, page: Page, otp_code: str) -> bool:
        """Input OTP code in browser form"""
        
        try:
            print(f"⌨️ Inputting OTP code: {otp_code}")
            
            # GHL typically uses individual digit boxes, so try that first
            print("🔢 Attempting individual digit input (GHL format)...")
            success = await self._try_individual_digit_inputs(page, otp_code)
            if success:
                await self._submit_otp_form(page)
                return True
            
            print("🔄 Trying single input field approach...")
            # Fallback to single input field approach
            otp_selectors = [
                'input[type="text"]',
                'input[type="number"]',
                'input[name*="code"]',
                'input[name*="otp"]',
                'input[name*="verification"]',
                'input[placeholder*="code"]',
                'input[placeholder*="Code"]',
                '.otp-input',
                '.verification-input',
                '[data-testid="otp-input"]'
            ]
            
            # Try to find and fill single OTP input
            for selector in otp_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=2000)
                    
                    # Clear any existing content
                    await page.fill(selector, '')
                    await page.wait_for_timeout(500)
                    
                    # Input the OTP code
                    await page.fill(selector, otp_code)
                    await page.wait_for_timeout(1000)
                    
                    print(f"✅ OTP entered using single input selector: {selector}")
                    
                    # Submit the form
                    await self._submit_otp_form(page)
                    
                    return True
                    
                except:
                    continue
            
            print("❌ Could not find suitable OTP input fields")
            return False
            
        except Exception as e:
            print(f"⌨️ OTP input error: {e}")
            return False
    
    async def _try_individual_digit_inputs(self, page: Page, otp_code: str):
        """Try inputting OTP in individual digit boxes"""
        
        try:
            print("🔢 Trying individual digit inputs...")
            
            # GHL uses 6 individual input boxes - try multiple approaches
            digit_selectors = [
                'input[maxlength="1"]',  # Most common for digit inputs
                'input[type="text"][maxlength="1"]',  # Specific text inputs with single char
                '.otp-digit',
                '.digit-input', 
                '[data-testid="digit-input"]',
                'input[class*="digit"]',  # Any input with "digit" in class name
                'input[id*="digit"]',     # Any input with "digit" in ID
            ]
            
            for selector in digit_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    
                    if len(elements) >= len(otp_code):
                        print(f"📱 Found {len(elements)} digit inputs using selector: {selector}")
                        
                        # Clear all inputs first
                        for element in elements[:len(otp_code)]:
                            await element.fill('')
                            await page.wait_for_timeout(100)
                        
                        # Input each digit with small delays
                        for i, digit in enumerate(otp_code):
                            if i < len(elements):
                                await elements[i].click()  # Focus the input
                                await page.wait_for_timeout(200)
                                await elements[i].fill(digit)
                                await page.wait_for_timeout(300)
                                
                                # Try typing as backup
                                await elements[i].type(digit)
                                await page.wait_for_timeout(200)
                        
                        print("✅ OTP entered in individual digit boxes")
                        
                        # Wait a moment for auto-submit or find submit button
                        await page.wait_for_timeout(2000)
                        
                        return True
                        
                except Exception as e:
                    print(f"🔢 Selector {selector} failed: {e}")
                    continue
            
            # If individual inputs not found, try a different approach
            print("🔄 Trying alternative input methods...")
            
            # Look for any input field that might accept the full code
            fallback_selectors = [
                'input[type="text"]',
                'input[type="number"]', 
                'input[name*="code"]',
                'input[placeholder*="code"]'
            ]
            
            for selector in fallback_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=1000)
                    await page.fill(selector, otp_code)
                    print(f"✅ OTP entered using fallback selector: {selector}")
                    return True
                except:
                    continue
                    
            return False
                    
        except Exception as e:
            print(f"🔢 Individual digit input error: {e}")
            return False
    
    async def _submit_otp_form(self, page: Page):
        """Submit the OTP form"""
        
        submit_selectors = [
            'button[type="submit"]',
            'text="Verify"',
            'text="Submit"',
            'text="Continue"',
            'text="Confirm"',
            '.submit-btn',
            '.verify-btn',
            '[data-testid="submit"]'
        ]
        
        for selector in submit_selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.click(selector)
                print(f"✅ Submitted OTP form using: {selector}")
                await page.wait_for_timeout(3000)
                return
            except:
                continue
        
        # If no submit button found, try pressing Enter
        try:
            await page.keyboard.press('Enter')
            print("✅ Submitted OTP form with Enter key")
            await page.wait_for_timeout(3000)
        except:
            print("⚠️ Could not submit OTP form")

# Test function
async def test_gmail_2fa():
    """Test the Gmail 2FA service"""
    
    print("🧪 Testing Gmail 2FA Service")
    print("=" * 40)
    
    email_config = GmailEmailConfig()
    service = Enhanced2FAService(email_config)
    
    # Test email connection
    try:
        otp = await service._get_otp_from_gmail()
        if otp:
            print(f"✅ Found OTP: {otp}")
        else:
            print("ℹ️ No OTP found in recent emails")
    except Exception as e:
        print(f"❌ Email test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gmail_2fa())