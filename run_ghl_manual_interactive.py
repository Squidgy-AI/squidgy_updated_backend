#!/usr/bin/env python3
"""
GHL automation script that keeps browser open for manual OTP entry
"""

import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def main():
    load_dotenv()
    
    # Get credentials
    email = os.getenv('HIGHLEVEL_EMAIL', 'somashekhar34+MdY4KL72@gmail.com')
    password = os.getenv('HIGHLEVEL_PASSWORD', 'Dummy@123')
    location_id = "MdY4KL72E0lc7TqMm3H0"
    
    print(f"🎯 Starting GHL automation")
    print(f"📧 Email: {email}")
    print(f"📍 Location: {location_id}")
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # Keep browser visible for manual interaction
    chrome_options.add_experimental_option("detach", True)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to target URL
        target_url = f"https://app.onetoo.com/v2/location/{location_id}/settings/private-integrations/"
        print(f"🔗 Navigating to: {target_url}")
        driver.get(target_url)
        time.sleep(3)
        
        # Fill login
        email_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[2]/div/div[2]/input"
        email_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, email_xpath))
        )
        email_field.clear()
        email_field.send_keys(email)
        print("✅ Email filled")
        
        password_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/div[2]/input"
        password_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, password_xpath))
        )
        password_field.clear()
        password_field.send_keys(password)
        print("✅ Password filled")
        
        # Login
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Sign in")]'))
        )
        login_button.click()
        print("✅ Login clicked")
        time.sleep(8)
        
        # Handle 2FA
        try:
            send_code_xpath = "/html/body/div[1]/div[1]/div[4]/section/div[2]/div/div/div/div[3]/div/button"
            send_code_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, send_code_xpath))
            )
            send_code_button.click()
            print("✅ Send code clicked")
            time.sleep(3)
        except:
            print("⚠️ Send code button not found")
        
        print("\n" + "="*50)
        print("📧 Check your email for the verification code")
        print("👆 MANUALLY ENTER THE 6-DIGIT CODE IN THE BROWSER")
        print("="*50)
        
        # Wait for manual OTP entry and successful navigation
        print("\n⏳ Waiting for you to enter OTP and complete login...")
        print("🔍 Checking every 2 seconds for successful login...")
        
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            current_url = driver.current_url
            # Check if we've navigated away from login page
            if "settings/private-integrations" in current_url and "login" not in current_url.lower():
                print(f"\n✅ Login successful!")
                print(f"📍 Current URL: {current_url}")
                print("\n🎉 You can now continue using the browser manually")
                print("🔓 The browser will remain open for your use")
                break
            time.sleep(2)
        else:
            print("\n⏱️ Timeout waiting for login completion")
        
        print("\n" + "="*50)
        print("ℹ️  The browser will stay open. Close it manually when done.")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔓 Browser will remain open for debugging")

if __name__ == "__main__":
    main()