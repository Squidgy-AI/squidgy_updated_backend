#!/usr/bin/env python3
"""
Test the proper Facebook integration flow:
1. Connect to Facebook OAuth (get accountId)
2. Store the accountId 
3. Use accountId to get pages
4. Use accountId to attach pages
"""

import httpx
import asyncio
import json

# Test data
PIT_TOKEN = "pit-242184f6-b9df-45dc-9e21-08c680f40bb3"
LOCATION_ID = "gDf0mj9zKyFBDzhaJfj2"

async def test_facebook_flow():
    """Test the complete Facebook integration flow"""
    
    print("🎯 FACEBOOK INTEGRATION PROPER FLOW TEST")
    print("=" * 60)
    print(f"PIT Token: {PIT_TOKEN}")
    print(f"Location ID: {LOCATION_ID}")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {PIT_TOKEN}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # STEP 1: Connect to Facebook OAuth to get accountId
        print("\n📱 STEP 1: Connect to Facebook OAuth")
        print("-" * 40)
        
        # Try different OAuth connection endpoints
        oauth_endpoints = [
            f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/facebook",
            f"https://services.leadconnectorhq.com/social-media-posting/{LOCATION_ID}/facebook/oauth",
            f"https://services.leadconnectorhq.com/social-media-posting/{LOCATION_ID}/facebook/connect"
        ]
        
        facebook_account_id = None
        
        for endpoint in oauth_endpoints:
            print(f"\n🔍 Trying OAuth endpoint: {endpoint}")
            
            try:
                # Try GET first to see what's available
                response = await client.get(endpoint, headers=headers)
                print(f"   GET Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ GET Success: {json.dumps(data, indent=6)}")
                    
                    # Look for account ID in response
                    if 'accountId' in data:
                        facebook_account_id = data['accountId']
                        print(f"   🎯 Found Account ID: {facebook_account_id}")
                        break
                    
                elif response.status_code == 405:
                    print("   🔄 Method not allowed, trying POST...")
                    
                    # Try POST to initiate OAuth
                    post_data = {
                        "redirect_uri": f"https://app.gohighlevel.com/location/{LOCATION_ID}/integrations/facebook",
                        "location_id": LOCATION_ID
                    }
                    
                    post_response = await client.post(endpoint, headers=headers, json=post_data)
                    print(f"   POST Status: {post_response.status_code}")
                    
                    if post_response.status_code in [200, 201]:
                        post_result = post_response.json()
                        print(f"   ✅ POST Success: {json.dumps(post_result, indent=6)}")
                        
                        # Look for OAuth URL or account ID
                        if 'oauth_url' in post_result:
                            print(f"   🔗 OAuth URL: {post_result['oauth_url']}")
                        if 'accountId' in post_result:
                            facebook_account_id = post_result['accountId']
                            print(f"   🎯 Found Account ID: {facebook_account_id}")
                            break
                    else:
                        print(f"   ❌ POST Failed: {post_response.text}")
                        
                else:
                    print(f"   ❌ Failed: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # If we didn't get an account ID from OAuth, try to find existing ones
        if not facebook_account_id:
            print(f"\n📋 STEP 1B: Look for existing Facebook accounts")
            print("-" * 40)
            
            # Try to list existing social accounts
            list_endpoints = [
                f"https://services.leadconnectorhq.com/social-media-posting/{LOCATION_ID}/accounts",
                f"https://services.leadconnectorhq.com/social-media-posting/accounts?locationId={LOCATION_ID}",
                f"https://services.leadconnectorhq.com/locations/{LOCATION_ID}/integrations"
            ]
            
            for endpoint in list_endpoints:
                try:
                    print(f"\n🔍 Checking: {endpoint}")
                    response = await client.get(endpoint, headers=headers)
                    print(f"   Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"   Response: {json.dumps(data, indent=6)}")
                        
                        # Look for Facebook accounts
                        accounts = []
                        if isinstance(data, dict):
                            if 'accounts' in data:
                                accounts = data['accounts']
                            elif 'results' in data:
                                accounts = data['results']
                            elif 'data' in data:
                                accounts = data['data']
                        elif isinstance(data, list):
                            accounts = data
                        
                        for account in accounts:
                            if isinstance(account, dict) and account.get('platform') == 'facebook':
                                facebook_account_id = account.get('_id') or account.get('id') or account.get('accountId')
                                print(f"   🎯 Found Facebook Account ID: {facebook_account_id}")
                                break
                        
                        if facebook_account_id:
                            break
                            
                    elif response.status_code != 404:
                        print(f"   Response: {response.text}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        # STEP 2: Use the account ID to get pages
        if facebook_account_id:
            print(f"\n📄 STEP 2: Get Facebook Pages using Account ID")
            print("-" * 40)
            print(f"Using Account ID: {facebook_account_id}")
            
            pages_url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{LOCATION_ID}/facebook/accounts/{facebook_account_id}"
            
            try:
                print(f"URL: {pages_url}")
                response = await client.get(pages_url, headers=headers)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ SUCCESS! Pages data: {json.dumps(data, indent=6)}")
                    
                    # Extract pages
                    pages = []
                    if 'results' in data and 'pages' in data['results']:
                        pages = data['results']['pages']
                    elif 'pages' in data:
                        pages = data['pages']
                    
                    print(f"\nFound {len(pages)} pages")
                    
                    # STEP 3: Attach a page
                    if pages:
                        print(f"\n🔗 STEP 3: Attach first page")
                        print("-" * 40)
                        
                        first_page = pages[0]
                        attach_body = {
                            "type": "page",
                            "originId": first_page.get('id', 'test123'),
                            "name": first_page.get('name', 'Test Page'),
                            "avatar": first_page.get('avatar', ''),
                            "companyId": "lp2p1q27DrdGta1qGDJd"
                        }
                        
                        print(f"Attaching page: {json.dumps(attach_body, indent=6)}")
                        
                        attach_response = await client.post(pages_url, headers=headers, json=attach_body)
                        print(f"Attach Status: {attach_response.status_code}")
                        
                        if attach_response.status_code in [200, 201]:
                            attach_data = attach_response.json()
                            print(f"✅ Page attached successfully: {json.dumps(attach_data, indent=6)}")
                        else:
                            print(f"❌ Attach failed: {attach_response.text}")
                    
                else:
                    print(f"❌ Failed to get pages: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error getting pages: {e}")
        
        else:
            print(f"\n❌ STEP 2 SKIPPED: No Facebook Account ID found")
            print("   Need to complete OAuth flow first to get account ID")
    
    print("\n" + "=" * 60)
    print("FACEBOOK FLOW TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_facebook_flow())