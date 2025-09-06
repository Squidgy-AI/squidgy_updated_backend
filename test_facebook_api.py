#!/usr/bin/env python3
"""
Test Facebook API calls using captured tokens
"""

import json
import requests
from datetime import datetime

def load_tokens():
    """Load tokens from the saved file"""
    try:
        with open("highlevel_tokens_complete.json", "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading tokens: {e}")
        return None

def test_facebook_pages_api(tokens_data):
    """Test the Facebook pages API call"""
    try:
        location_id = tokens_data['location_id']
        firebase_token = tokens_data['tokens']['firebase_token']
        
        if not firebase_token:
            print("❌ No Firebase token found - cannot make API calls")
            return False
        
        # API endpoint
        url = f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/pages?getAll=true"
        
        # Headers (based on your network request)
        headers = {
            'accept': 'application/json, text/plain, */*',
            'channel': 'APP',
            'source': 'WEB_USER',
            'token-id': firebase_token,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'version': '2021-07-28'
        }
        
        print(f"🔍 Testing Facebook Pages API...")
        print(f"📍 Location ID: {location_id}")
        print(f"🔗 URL: {url}")
        print(f"🎫 Using Firebase token: {firebase_token[:20]}...")
        
        # Make the API call
        response = requests.get(url, headers=headers)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ API call successful!")
                print(f"📋 Response data: {json.dumps(data, indent=2)}")
                return True
            except:
                print(f"✅ API call successful but response is not JSON")
                print(f"📋 Response text: {response.text}")
                return True
        else:
            print(f"❌ API call failed")
            print(f"📋 Response text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error making API call: {e}")
        return False

def main():
    """Main function"""
    print("="*80)
    print("🧪 FACEBOOK API TESTER")
    print("="*80)
    
    # Load tokens
    tokens_data = load_tokens()
    if not tokens_data:
        print("❌ Could not load tokens")
        return
    
    print(f"📅 Tokens loaded from: {tokens_data['timestamp']}")
    print(f"📍 Location ID: {tokens_data['location_id']}")
    
    # Check if we have the Firebase token
    firebase_token = tokens_data['tokens']['firebase_token']
    if firebase_token:
        print(f"✅ Firebase token available: {firebase_token[:20]}...")
    else:
        print("❌ No Firebase token found - run the automation script first")
        return
    
    # Test GET API
    print("\n" + "="*50)
    test_facebook_pages_api(tokens_data)
    
    print("\n" + "="*80)
    print("🧪 Facebook API testing completed!")
    print("="*80)

if __name__ == "__main__":
    main()