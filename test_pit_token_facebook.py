#!/usr/bin/env python3
"""
Test PIT token with various GHL Facebook endpoints
"""

import httpx
import asyncio
import json
from datetime import datetime

# Real test data from database
PIT_TOKEN = "pit-242184f6-b9df-45dc-9e21-08c680f40bb3"
LOCATION_ID = "gDf0mj9zKyFBDzhaJfj2"

async def test_facebook_endpoints():
    """Test various Facebook endpoints with PIT token"""
    print("=" * 80)
    print("PIT TOKEN FACEBOOK API TESTS")
    print("=" * 80)
    print(f"PIT Token: {PIT_TOKEN}")
    print(f"Location ID: {LOCATION_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    headers = {
        "Authorization": f"Bearer {PIT_TOKEN}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Try to get location info
        print("\n📍 TEST 1: Get Location Info")
        print("-" * 60)
        
        try:
            url = f"https://services.leadconnectorhq.com/locations/{LOCATION_ID}"
            response = await client.get(url, headers=headers)
            print(f"URL: {url}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Location found: {data.get('name', 'Unknown')}")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Try social media accounts endpoint
        print("\n📱 TEST 2: Social Media Accounts")
        print("-" * 60)
        
        endpoints_to_try = [
            f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/accounts",
            f"https://services.leadconnectorhq.com/social-media-posting/{LOCATION_ID}/accounts",
            f"https://services.leadconnectorhq.com/locations/{LOCATION_ID}/social-accounts",
            f"https://services.leadconnectorhq.com/locations/{LOCATION_ID}/integrations/facebook"
        ]
        
        for url in endpoints_to_try:
            try:
                print(f"\n🔍 Trying: {url}")
                response = await client.get(url, headers=headers)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success! Response: {json.dumps(data, indent=2)}")
                    break
                elif response.status_code == 404:
                    print("❌ Not Found (wrong endpoint)")
                else:
                    print(f"❌ Failed: {response.text}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Test 3: Try to create a Facebook connection first
        print("\n📤 TEST 3: Create Facebook OAuth Connection")
        print("-" * 60)
        
        # This might be the step we're missing - we need to create the Facebook account first
        oauth_endpoints = [
            f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/facebook",
            f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/facebook/connect"
        ]
        
        for url in oauth_endpoints:
            try:
                print(f"\n🔍 Trying OAuth: {url}")
                
                # First try GET to see what's available
                response = await client.get(url, headers=headers)
                print(f"GET Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ GET Success: {json.dumps(data, indent=2)}")
                elif response.status_code == 405:
                    print("🔄 Method not allowed, trying POST...")
                    
                    # Try POST with minimal data
                    post_response = await client.post(url, headers={**headers, "Content-Type": "application/json"}, json={})
                    print(f"POST Status: {post_response.status_code}")
                    
                    if post_response.status_code in [200, 201]:
                        post_data = post_response.json()
                        print(f"✅ POST Success: {json.dumps(post_data, indent=2)}")
                    else:
                        print(f"❌ POST Failed: {post_response.text}")
                else:
                    print(f"❌ Failed: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Test 4: Try to directly attach a test page (this will likely fail but shows the expected format)
        print("\n📄 TEST 4: Test Page Attachment (Expected to Fail)")
        print("-" * 60)
        
        # Use a fake account ID for testing
        test_account_id = "test_fb_account_123"
        attach_url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/facebook/accounts/{test_account_id}"
        
        test_page_body = {
            "type": "page",
            "originId": "test_page_12345",
            "name": "Test Page",
            "avatar": "https://example.com/avatar.jpg",
            "companyId": "lp2p1q27DrdGta1qGDJd"
        }
        
        try:
            print(f"URL: {attach_url}")
            print(f"Body: {json.dumps(test_page_body, indent=2)}")
            
            response = await client.post(
                attach_url,
                headers={**headers, "Content-Type": "application/json"},
                json=test_page_body
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Unexpected success: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ Expected failure: {response.text}")
                
                # This will help us understand the expected format
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_facebook_endpoints())