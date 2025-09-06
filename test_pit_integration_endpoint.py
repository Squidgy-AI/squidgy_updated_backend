#!/usr/bin/env python3
"""
Test PIT token with the integration endpoint (backend.leadconnectorhq.com)
This is the endpoint the browser actually uses successfully
"""

import httpx
import asyncio
import json
from datetime import datetime

# Real test data from database
PIT_TOKEN = "pit-242184f6-b9df-45dc-9e21-08c680f40bb3"
LOCATION_ID = "gDf0mj9zKyFBDzhaJfj2"

async def test_pit_with_integration_endpoint():
    """Test PIT token with the backend.leadconnectorhq.com integration endpoint"""
    print("=" * 80)
    print("PIT TOKEN WITH INTEGRATION ENDPOINT TEST")
    print("=" * 80)
    print(f"PIT Token: {PIT_TOKEN}")
    print(f"Location ID: {LOCATION_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Try PIT token with integration endpoint (like Firebase token)
        print("\n📱 TEST 1: PIT Token with Integration Headers (Firebase-style)")
        print("-" * 60)
        
        headers_firebase_style = {
            "token-id": PIT_TOKEN,  # Use PIT as token-id like Firebase
            "channel": "APP",
            "source": "WEB_USER",
            "version": "2021-07-28",
            "accept": "application/json, text/plain, */*"
        }
        
        url = f"https://backend.leadconnectorhq.com/integrations/facebook/{LOCATION_ID}/pages?getAll=true"
        
        try:
            print(f"URL: {url}")
            print(f"Headers: {json.dumps({k: v[:20] + '...' if k == 'token-id' else v for k, v in headers_firebase_style.items()}, indent=2)}")
            
            response = await client.get(url, headers=headers_firebase_style)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get('pages', [])
                print(f"✅ SUCCESS! Found {len(pages)} pages")
                
                if pages:
                    print("\nPages found:")
                    for i, page in enumerate(pages[:3], 1):
                        print(f"  {i}. {page.get('facebookPageName', 'Unknown')} (ID: {page.get('facebookPageId', 'unknown')})")
                
                return pages
            else:
                print(f"❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Try PIT token with Bearer Authorization
        print("\n📱 TEST 2: PIT Token with Bearer Authorization")
        print("-" * 60)
        
        headers_bearer = {
            "Authorization": f"Bearer {PIT_TOKEN}",
            "Version": "2021-07-28",
            "Accept": "application/json"
        }
        
        try:
            print(f"URL: {url}")
            print(f"Headers: {json.dumps({k: v[:30] + '...' if k == 'Authorization' else v for k, v in headers_bearer.items()}, indent=2)}")
            
            response = await client.get(url, headers=headers_bearer)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get('pages', [])
                print(f"✅ SUCCESS with Bearer! Found {len(pages)} pages")
                return pages
            else:
                print(f"❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Try different integration endpoints
        print("\n📱 TEST 3: Try Other Integration Endpoints")
        print("-" * 60)
        
        other_endpoints = [
            f"https://backend.leadconnectorhq.com/integrations/facebook/{LOCATION_ID}/pages",
            f"https://backend.leadconnectorhq.com/integrations/facebook/{LOCATION_ID}/allPages",
            f"https://backend.leadconnectorhq.com/integrations/facebook/{LOCATION_ID}/allPages?limit=20",
        ]
        
        for endpoint in other_endpoints:
            try:
                print(f"\n🔍 Trying: {endpoint}")
                
                # Try with Firebase-style headers
                response = await client.get(endpoint, headers=headers_firebase_style)
                print(f"Firebase-style Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ SUCCESS: {json.dumps(data, indent=2)}")
                    return data.get('pages', [])
                elif response.status_code != 401:
                    print(f"Response: {response.text}")
                
                # Try with Bearer headers
                response = await client.get(endpoint, headers=headers_bearer)
                print(f"Bearer Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ SUCCESS with Bearer: {json.dumps(data, indent=2)}")
                    return data.get('pages', [])
                elif response.status_code != 401:
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Test 4: Try to connect pages if we got any
        print("\n📱 TEST 4: Test Page Connection")
        print("-" * 60)
        
        # Use test data for connection
        connect_url = f"https://backend.leadconnectorhq.com/integrations/facebook/{LOCATION_ID}/pages"
        
        test_body = {
            "facebookPageIds": ["test_page_123"],
            "reconnect": False
        }
        
        # Try with Firebase-style headers
        headers_post = {
            "token-id": PIT_TOKEN,
            "channel": "APP",
            "source": "WEB_USER",
            "version": "2021-07-28",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json"
        }
        
        try:
            print(f"URL: {connect_url}")
            print(f"Body: {json.dumps(test_body, indent=2)}")
            
            response = await client.post(connect_url, headers=headers_post, json=test_body)
            print(f"Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Connection SUCCESS: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ Connection failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
    
    print("\n" + "=" * 80)
    print("PIT INTEGRATION TEST COMPLETE")
    print("=" * 80)
    
    return []

if __name__ == "__main__":
    asyncio.run(test_pit_with_integration_endpoint())