#!/usr/bin/env python3
"""
Test the REAL Facebook page connection to GHL
"""

import requests
import json
from datetime import datetime

# Test the real page connection endpoint
def test_real_page_connection():
    """Test connecting a Facebook page to GHL using the real API"""
    
    print("🔗 TESTING REAL FACEBOOK PAGE CONNECTION")
    print("=" * 80)
    
    # Get the latest JWT token from diagnostic test
    print("⚠️  You need to run the diagnostic test first to get a fresh JWT token")
    print("   Run: python diagnostic_facebook_api.py")
    print()
    
    # Use the JWT token from the diagnostic test
    jwt_token = input("📋 Enter the JWT token from the diagnostic test: ").strip()
    
    if not jwt_token:
        print("❌ JWT token is required")
        return
    
    # API endpoint
    url = "http://localhost:8000/api/facebook/connect-page"
    
    # Test payload (using the page we know exists from diagnostic test)
    payload = {
        "location_id": "GJSb0aPcrBRne73LK3A3",
        "page_id": "736138742906375",  # Testing Test Business page
        "jwt_token": jwt_token
    }
    
    print(f"📍 URL: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print("=" * 80)
    
    try:
        print("\n⏳ Sending request to REAL page connection endpoint...")
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success: {result.get('success', False)}")
            print(f"📄 Message: {result.get('message', 'No message')}")
            
            if result.get('success'):
                print(f"📱 Page Name: {result.get('page_name', 'N/A')}")
                print(f"🆔 Page ID: {result.get('page_id', 'N/A')}")
                
                if result.get('ghl_response'):
                    print(f"\n🎯 GHL Response: {json.dumps(result['ghl_response'], indent=2)}")
                
                print("\n✅ PAGE SHOULD NOW BE CONNECTED IN GHL!")
                print("🔍 Check your GHL dashboard to verify the connection")
            else:
                print(f"\n❌ Connection failed: {result.get('message', 'Unknown error')}")
                if result.get('error'):
                    print(f"💥 Error details: {result['error']}")
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response: {response.text}")
                
    except requests.exceptions.Timeout:
        print("\n⏰ Request timed out")
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Make sure the backend server is running")
    except Exception as e:
        print(f"\n💥 Unexpected Error: {type(e).__name__}: {str(e)}")
    
    print("\n📋 What this test does:")
    print("1. 📥 Gets page details from database")
    print("2. 🔗 Calls REAL GHL API to connect the page")
    print("3. 📊 Updates database with connection status")
    print("4. ✅ Should show page as connected in GHL dashboard")

if __name__ == "__main__":
    test_real_page_connection()