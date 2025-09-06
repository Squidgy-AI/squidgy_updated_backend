#!/usr/bin/env python3
"""
Test script to debug Facebook page attachment using PIT token
Tests the social-media-posting API endpoint with stored PIT token
"""

import httpx
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not url or not key:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY in environment")
    exit(1)

supabase: Client = create_client(url, key)

# Test configuration
USER_ID = "8f1b1cea-094d-439a-a575-feaffb7f6faf"
TEST_ACCOUNT_ID = "test_account_123"  # We'll need to find the real one

async def get_stored_tokens():
    """Get stored tokens from database"""
    print("📦 Fetching stored tokens from database...")
    
    result = supabase.table('squidgy_agent_business_setup').select(
        'highlevel_tokens, ghl_location_id, setup_json'
    ).eq('firm_user_id', USER_ID).eq('agent_id', 'SOLAgent').eq('setup_type', 'GHLSetup').single().execute()
    
    if not result.data:
        print("❌ No GHL setup found for user")
        return None, None, None
    
    setup_data = result.data
    tokens = setup_data.get('highlevel_tokens', {})
    location_id = setup_data.get('ghl_location_id')
    
    # Extract tokens
    pit_token = None
    firebase_token = None
    
    if isinstance(tokens, dict) and 'tokens' in tokens:
        token_data = tokens['tokens']
        pit_token = token_data.get('private_integration_token')
        firebase_token = token_data.get('firebase_token')
    
    print(f"📍 Location ID: {location_id}")
    print(f"🔑 PIT Token: {pit_token[:20]}..." if pit_token else "❌ No PIT token found")
    print(f"🔥 Firebase Token: {firebase_token[:20]}..." if firebase_token else "❌ No Firebase token found")
    
    return pit_token, firebase_token, location_id

async def test_get_facebook_accounts(pit_token, location_id):
    """First, try to get Facebook accounts to find the account ID"""
    print("\n" + "=" * 60)
    print("TEST 1: Get Facebook Accounts")
    print("=" * 60)
    
    # Try to find Facebook accounts using the social-media-posting endpoint
    headers = {
        "Authorization": f"Bearer {pit_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    
    # First, let's try to list all social accounts
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try a general accounts endpoint
        accounts_url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{location_id}/accounts"
        
        print(f"\n🔍 Trying to list all social accounts...")
        print(f"URL: {accounts_url}")
        
        try:
            response = await client.get(accounts_url, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Look for Facebook accounts
                if 'results' in data:
                    fb_accounts = [acc for acc in data.get('results', []) if acc.get('platform') == 'facebook']
                    if fb_accounts:
                        print(f"\n✅ Found {len(fb_accounts)} Facebook accounts")
                        return fb_accounts[0].get('_id') or fb_accounts[0].get('id')
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return None

async def test_attach_facebook_page(pit_token, location_id, account_id, page_data):
    """Test attaching a Facebook page"""
    print("\n" + "=" * 60)
    print("TEST 2: Attach Facebook Page")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {pit_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Prepare the request body according to API docs
    body = {
        "type": "page",
        "originId": page_data.get("page_id", "test_page_123"),
        "name": page_data.get("page_name", "Test Page"),
        "avatar": page_data.get("avatar", ""),
        "companyId": "lp2p1q27DrdGta1qGDJd"  # Your company ID
    }
    
    url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{location_id}/facebook/accounts/{account_id}"
    
    print(f"\n📤 Request:")
    print(f"URL: {url}")
    print(f"Headers: {json.dumps({k: v[:50] + '...' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}")
    print(f"Body: {json.dumps(body, indent=2)}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=body)
            
            print(f"\n📥 Response:")
            print(f"Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"Success! Response: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"Failed: {response.text}")
                
                # Try to decode error
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Exception: {type(e).__name__}: {e}")
    
    return False

async def test_integration_endpoint(firebase_token, location_id):
    """Test the integration endpoint to get pages"""
    print("\n" + "=" * 60)
    print("TEST 3: Integration Endpoint (for comparison)")
    print("=" * 60)
    
    headers = {
        "token-id": firebase_token,
        "channel": "APP",
        "source": "WEB_USER",
        "version": "2021-07-28",
        "accept": "application/json, text/plain, */*"
    }
    
    url = f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/pages?getAll=true"
    
    print(f"URL: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get('pages', [])
                print(f"\n✅ Found {len(pages)} pages via integration endpoint")
                
                if pages:
                    print("\nFirst 3 pages:")
                    for i, page in enumerate(pages[:3], 1):
                        print(f"  {i}. {page.get('facebookPageName')} (ID: {page.get('facebookPageId')})")
                
                return pages
            else:
                print(f"❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    return []

async def main():
    """Run all tests"""
    print("=" * 80)
    print("FACEBOOK PAGE ATTACHMENT TEST")
    print("=" * 80)
    print(f"User ID: {USER_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Get stored tokens
    pit_token, firebase_token, location_id = await get_stored_tokens()
    
    if not pit_token:
        print("\n❌ No PIT token found. Cannot proceed with tests.")
        return
    
    if not location_id:
        print("\n❌ No location ID found. Cannot proceed with tests.")
        return
    
    # Test 1: Try to get Facebook account ID
    account_id = await test_get_facebook_accounts(pit_token, location_id)
    
    if not account_id:
        print("\n⚠️ Could not find Facebook account ID. Using test value.")
        account_id = "test_account_123"
    
    # Test 2: Get pages via integration endpoint to have real data
    pages = await test_integration_endpoint(firebase_token, location_id)
    
    if pages:
        # Test 3: Try to attach the first page
        first_page = pages[0]
        page_data = {
            "page_id": first_page.get("facebookPageId"),
            "page_name": first_page.get("facebookPageName"),
            "avatar": ""
        }
        
        await test_attach_facebook_page(pit_token, location_id, account_id, page_data)
    else:
        print("\n⚠️ No pages found to test attachment")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())