#!/usr/bin/env python3
"""
Simple PIT token test with step-by-step logging
"""

import httpx
import asyncio
import json

# Test data
PIT_TOKEN = "pit-242184f6-b9df-45dc-9e21-08c680f40bb3"
LOCATION_ID = "gDf0mj9zKyFBDzhaJfj2"

async def simple_pit_test():
    """Simple test with PIT token authentication"""
    
    print("🔑 STEP 1: Setting up PIT token authentication")
    print(f"   PIT Token: {PIT_TOKEN}")
    print(f"   Location ID: {LOCATION_ID}")
    
    print("\n📋 STEP 2: Preparing headers for Bearer authentication")
    headers = {
        "Authorization": f"Bearer {PIT_TOKEN}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    print(f"   Headers: {json.dumps(headers, indent=6)}")
    
    print("\n🌐 STEP 3: Making request to GHL Facebook API")
    url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/facebook/accounts/test123"
    print(f"   URL: {url}")
    
    print("\n⏳ STEP 4: Sending request...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            
            print(f"\n📥 STEP 5: Response received")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            
            print(f"\n📄 STEP 6: Response body")
            try:
                response_data = response.json()
                print(f"   JSON Response: {json.dumps(response_data, indent=6)}")
            except:
                print(f"   Raw Response: {response.text}")
                
            print(f"\n🎯 STEP 7: Analysis")
            if response.status_code == 200:
                print("   ✅ SUCCESS: Authentication worked!")
            elif response.status_code == 401:
                print("   ❌ AUTHENTICATION FAILED: Token is invalid/expired")
            elif response.status_code == 403:
                print("   ❌ FORBIDDEN: Token doesn't have required permissions")
            elif response.status_code == 404:
                print("   ❌ NOT FOUND: Endpoint doesn't exist")
            else:
                print(f"   ❌ OTHER ERROR: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"\n💥 STEP 5: Request failed with exception")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("SIMPLE PIT TOKEN AUTHENTICATION TEST")
    print("=" * 60)
    asyncio.run(simple_pit_test())
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)