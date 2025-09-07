#!/usr/bin/env python3
"""
Verification script for GHL Registration Endpoint
Run this to test the complete flow
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "full_name": "Test User Verification",
    "email": "verify@test.com"  # Make sure this exists in profiles table
}

def test_registration_endpoint():
    """Test the registration endpoint"""
    print("🧪 Testing GHL Registration Endpoint")
    print(f"📧 Using test email: {TEST_USER['email']}")
    
    try:
        # Make registration request
        response = requests.post(
            f"{BASE_URL}/api/ghl/create-subaccount-and-user-registration",
            json=TEST_USER,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Registration endpoint successful!")
            print(f"🆔 GHL Record ID: {data.get('ghl_record_id')}")
            print(f"👤 User ID: {data.get('user_id')}")
            print(f"🏢 Company ID: {data.get('company_id')}")
            print(f"📝 Subaccount Name: {data.get('subaccount_name')}")
            
            return data.get('ghl_record_id')
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_status_endpoint(ghl_record_id, max_checks=10):
    """Test the status endpoint and monitor progress"""
    print(f"\n📊 Monitoring Status for Record: {ghl_record_id}")
    
    for i in range(max_checks):
        try:
            response = requests.get(
                f"{BASE_URL}/api/ghl/status/{ghl_record_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                ghl_status = data['ghl_status']['creation_status']
                automation_status = data['ghl_status']['automation_status']
                overall_status = data['overall_status']
                
                print(f"📈 Check {i+1}/{max_checks}: GHL={ghl_status}, Auto={automation_status}, Overall={overall_status}")
                
                if data.get('facebook_status'):
                    fb_status = data['facebook_status']['automation_status']
                    fb_step = data['facebook_status'].get('automation_step', 'unknown')
                    print(f"📱 Facebook: {fb_status} (Step: {fb_step})")
                
                # Check if completed
                if overall_status == 'fully_completed':
                    print("🎉 Process fully completed!")
                    return True
                elif overall_status == 'failed':
                    print("❌ Process failed!")
                    print(f"Error: {data['ghl_status'].get('creation_error') or data['ghl_status'].get('automation_error')}")
                    return False
                    
            else:
                print(f"❌ Status check failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Status check error: {e}")
        
        # Wait before next check
        if i < max_checks - 1:
            print(f"⏳ Waiting 30 seconds before next check...")
            time.sleep(30)
    
    print("⏰ Monitoring timeout reached")
    return False

def main():
    """Main verification function"""
    print("🚀 GHL Registration Endpoint Verification")
    print(f"🕒 Started at: {datetime.now()}")
    print("="*50)
    
    # Step 1: Test registration
    ghl_record_id = test_registration_endpoint()
    
    if not ghl_record_id:
        print("❌ Verification failed at registration step")
        return
    
    # Step 2: Monitor status
    print("\n" + "="*50)
    success = test_status_endpoint(ghl_record_id)
    
    # Final summary
    print("\n" + "="*50)
    print("📋 VERIFICATION SUMMARY")
    print(f"🆔 GHL Record ID: {ghl_record_id}")
    print(f"✅ Success: {'Yes' if success else 'No'}")
    print(f"🕒 Completed at: {datetime.now()}")
    
    if success:
        print("🎉 All tests passed! The endpoint is working correctly.")
    else:
        print("⚠️ Some tests failed. Check logs and database for details.")

if __name__ == "__main__":
    main()