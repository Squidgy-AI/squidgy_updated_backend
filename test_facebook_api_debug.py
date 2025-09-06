#!/usr/bin/env python3
"""
Debug script for Facebook API access using tokens from the automation
Location ID: AXLmV9jdWwgyDv4uoRho
"""

import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# From the logs - extracted tokens
LOCATION_ID = "AXLmV9jdWwgyDv4uoRho"
USER_ID = "8f1b1cea-094d-439a-a575-feaffb7f6faf"

def get_tokens_from_database():
    """Get the latest tokens from database"""
    try:
        result = supabase.table('squidgy_agent_business_setup').select(
            'highlevel_tokens, ghl_location_id, setup_json, created_at, updated_at'
        ).eq('firm_user_id', USER_ID).eq('agent_id', 'SOLAgent').eq('setup_type', 'GHLSetup').single().execute()
        
        if not result.data:
            print("❌ No GHL setup found for this user")
            return None, None
        
        setup_data = result.data
        tokens = setup_data.get('highlevel_tokens', {})
        
        if 'tokens' in tokens:
            token_data = tokens['tokens']
            pit_token = token_data.get('private_integration_token')
            firebase_token = token_data.get('firebase_token')
            
            print(f"📍 Location ID: {setup_data.get('ghl_location_id')}")
            print(f"🎯 PIT Token: {pit_token}")
            print(f"🔥 Firebase Token: {firebase_token[:50] if firebase_token else 'None'}...")
            
            return pit_token, firebase_token
        
        return None, None
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None, None

def test_facebook_pages_endpoint():
    """Simple test for Facebook pages endpoint"""
    
    print("="*60)
    print(f"🧪 SIMPLE FACEBOOK PAGES TEST")
    print(f"📍 Location ID: {LOCATION_ID}")
    print("="*60)
    
    # Get tokens from database
    pit_token, firebase_token = get_tokens_from_database()
    
    if not firebase_token:
        print("❌ Could not retrieve Firebase token from database")
        return
    
    # Test: Integration API with Firebase token - CORRECT ENDPOINT
    print(f"\n📱 Testing Facebook Pages Endpoint:")
    url = f"https://backend.leadconnectorhq.com/integrations/facebook/{LOCATION_ID}/allPages?limit=20"
    headers = {
        "token-id": firebase_token,
        "accept": "application/json, text/plain, */*",
        "channel": "APP",
        "source": "WEB_USER",
        "origin": "https://app.onetoo.com",
        "referer": "https://app.onetoo.com/",
        "Version": "2021-07-28"
    }
    
    try:
        print(f"📤 URL: {url}")
        print(f"📤 Headers: token-id: {firebase_token[:20]}...")
        
        response = requests.get(url, headers=headers)
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get('pages', [])
            print(f"✅ SUCCESS: Found {len(pages)} Facebook pages")
            if pages:
                for i, page in enumerate(pages, 1):
                    name = page.get('facebookPageName', 'Unknown')
                    page_id = page.get('facebookPageId', 'N/A')
                    url = page.get('facebookUrl', 'N/A')
                    print(f"   {i}. {name} (ID: {page_id})")
                    print(f"      URL: {url}")
            else:
                print("   No pages found - need to connect Facebook account first")
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print(f"\n" + "="*60)

if __name__ == "__main__":
    test_facebook_pages_endpoint()