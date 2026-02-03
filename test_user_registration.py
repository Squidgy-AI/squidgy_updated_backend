#!/usr/bin/env python3
"""
Test script to simulate actual user registration flow
This calls the REAL backend endpoint that triggers during signup
"""
import requests
import json
import time

# Backend URL (local server running on port 8000)
BACKEND_URL = "http://localhost:8000"

# Test user data
test_user = {
    "user_id": "TEST-" + str(int(time.time())),  # Unique test user ID
    "agent_id": "SOL",
    "subaccount_name": "Test User Registration",
    "business_phone": "+17166044029",
    "business_address": "456 Solar Demo Avenue",
    "business_city": "Buffalo",
    "business_state": "NY",
    "business_country": "US",
    "business_postal_code": "14201",
    "business_timezone": "America/New_York",
    "business_website": "https://test-client.com",
    "prospect_first_name": "Test",
    "prospect_last_name": "User",
    "prospect_email": f"test+{int(time.time())}@example.com"
}

print("="*80)
print("TESTING USER REGISTRATION FLOW")
print("="*80)
print()
print("This will call the ACTUAL backend endpoint that runs during signup:")
print(f"  POST {BACKEND_URL}/api/ghl/register-subaccount")
print()
print("Test User Data:")
print(json.dumps(test_user, indent=2))
print()
print("="*80)
print()

input("Press ENTER to start the test (make sure backend is running on port 8000)...")

print("\n🚀 Calling registration endpoint...")
print()

try:
    response = requests.post(
        f"{BACKEND_URL}/api/ghl/register-subaccount",
        json=test_user,
        timeout=180  # 3 minutes timeout
    )

    print("="*80)
    print("RESPONSE:")
    print("="*80)
    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS!")
        print()
        print(json.dumps(data, indent=2))

        if 'ghl_location_id' in data:
            print()
            print("="*80)
            print("NEXT STEPS:")
            print("="*80)
            print(f"1. Check if automation ran successfully")
            print(f"2. Location ID: {data.get('ghl_location_id')}")
            print(f"3. Check database for firebase_token:")
            print()
            print(f"   SELECT firebase_token, automation_status, automation_error")
            print(f"   FROM ghl_subaccounts")
            print(f"   WHERE firm_user_id = '{test_user['user_id']}'")
            print("="*80)
    else:
        print("❌ FAILED!")
        print()
        print(response.text)

except requests.exceptions.Timeout:
    print("❌ Request timed out (3 minutes)")
    print("The automation might still be running in the background")
except Exception as e:
    print(f"❌ Error: {e}")

print()
