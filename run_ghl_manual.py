#!/usr/bin/env python3
"""
Simple GHL automation script that works interactively
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
        
        # Get OTP from user
        print("\n📧 Check your email for the verification code from noreply@talk.onetoo.com")
        otp = input("Enter the 6-digit code: ").strip()
        
        # Enter OTP
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[maxlength="1"]')
        if len(inputs) >= 6:
            for i, digit in enumerate(otp):
                inputs[i].clear()
                inputs[i].send_keys(digit)
                time.sleep(0.3)
                print(f"✅ Digit {i+1}: {digit}")
        
        print("⏳ Waiting for verification...")
        time.sleep(10)
        
        print(f"📍 Current URL: {driver.current_url}")
        print("🎉 Login completed! Browser will stay open for you to continue manually.")
        
        # Keep browser open
        input("Press Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()