#!/usr/bin/env python3
"""
Simple test for Playwright automation without database
Just tests login and form filling
"""

import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

async def test_login_form_detection():
    """Test login form detection and filling"""
    load_dotenv()
    
    email = os.getenv('HIGHLEVEL_EMAIL', 'somashekhar34+MdY4KL72@gmail.com')
    password = os.getenv('HIGHLEVEL_PASSWORD', 'Dummy@123')
    location_id = "MdY4KL72E0lc7TqMm3H0"
    
    print("="*80)
    print("🧪 TESTING PLAYWRIGHT LOGIN FORM DETECTION")
    print("="*80)
    print(f"📧 Email: {email}")
    print(f"📍 Location: {location_id}")
    
    playwright = await async_playwright().start()
    
    try:
        # Launch browser (not headless so we can see what's happening)
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # First, clear cookies to ensure we get login page
        await context.clear_cookies()
        
        # Navigate to login page
        target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
        print(f"\n🔗 Navigating to: {target_url}")
        await page.goto(target_url)
        
        # Wait for page to load
        await page.wait_for_timeout(5000)
        
        # Check current URL
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        # Check if we're on login page or need to login
        needs_login = ("login" in current_url.lower() or 
                      "sign" in current_url.lower() or
                      await page.locator('input[type="email"], input[type="password"]').count() > 0)
        
        if needs_login:
            print("✅ Detected login page")
            
            # Take a screenshot
            await page.screenshot(path="login_page.png")
            print("📸 Screenshot saved as login_page.png")
            
            # Try to find and list all input fields
            print("\n🔍 Finding all input fields...")
            inputs = await page.locator('input').all()
            
            for i, input_elem in enumerate(inputs):
                try:
                    input_type = await input_elem.get_attribute('type')
                    input_name = await input_elem.get_attribute('name')
                    input_id = await input_elem.get_attribute('id')
                    input_placeholder = await input_elem.get_attribute('placeholder')
                    
                    print(f"  Input {i+1}:")
                    print(f"    Type: {input_type}")
                    print(f"    Name: {input_name}")
                    print(f"    ID: {input_id}")
                    print(f"    Placeholder: {input_placeholder}")
                except Exception as e:
                    print(f"    Error getting attributes: {e}")
            
            # Try to fill email field using exact XPath
            print("\n📧 Trying to fill email field...")
            try:
                # Use the exact XPath from Selenium version
                email_xpath = '/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[2]/div/div[2]/input'
                await page.locator(f'xpath={email_xpath}').fill(email)
                print(f"✅ Email filled using exact XPath")
                
                # Take screenshot after email
                await page.screenshot(path="after_email.png")
                print("📸 Screenshot after email: after_email.png")
                
            except Exception as e:
                print(f"❌ XPath failed: {e}")
                
                # Try alternative selectors
                email_selectors = [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[placeholder*="email" i]',
                    'input:first-of-type'
                ]
                
                for selector in email_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            await page.locator(selector).fill(email)
                            print(f"✅ Email filled using: {selector}")
                            break
                    except Exception as e:
                        print(f"❌ Selector failed: {selector} - {e}")
            
            # Try to fill password field
            print("\n🔒 Trying to fill password field...")
            try:
                # Use exact XPath from Selenium version
                password_xpath = '/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div[2]/input'
                await page.locator(f'xpath={password_xpath}').fill(password)
                print(f"✅ Password filled using exact XPath")
                
                # Take screenshot after password
                await page.screenshot(path="after_password.png")
                print("📸 Screenshot after password: after_password.png")
                
            except Exception as e:
                print(f"❌ XPath failed: {e}")
                
                # Try alternative selectors
                password_selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[placeholder*="password" i]'
                ]
                
                for selector in password_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            await page.locator(selector).fill(password)
                            print(f"✅ Password filled using: {selector}")
                            break
                    except Exception as e:
                        print(f"❌ Selector failed: {selector} - {e}")
            
            # Look for login button
            print("\n🔘 Looking for login button...")
            buttons = await page.locator('button').all()
            
            for i, button in enumerate(buttons):
                try:
                    button_text = await button.text_content()
                    button_type = await button.get_attribute('type')
                    print(f"  Button {i+1}: '{button_text}' (type: {button_type})")
                except:
                    pass
            
            # Wait a bit more to see results
            print("\n⏳ Waiting 10 seconds to observe results...")
            await page.wait_for_timeout(10000)
            
        else:
            print("❌ Not on login page")
            await page.screenshot(path="not_login_page.png")
            print("📸 Screenshot saved as not_login_page.png")
        
        await browser.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_login_form_detection())