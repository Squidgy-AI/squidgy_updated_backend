#!/usr/bin/env python3
"""
Test the complete Facebook simple API flow
Simulates what happens when the frontend calls our API
"""

import httpx
import asyncio
import json
from datetime import datetime

# Test data
USER_ID = "8f1b1cea-094d-439a-a575-feaffb7f6faf"
API_BASE = "https://squidgy-back-919bc0659e35.herokuapp.com"

async def test_facebook_flow():
    """Test the complete Facebook flow"""
    print("=" * 80)
    print("FACEBOOK SIMPLE API TEST")
    print("=" * 80)
    print(f"User ID: {USER_ID}")
    print(f"API Base: {API_BASE}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Test get-pages-simple endpoint
        print("\n📱 STEP 1: Testing get-pages-simple endpoint")
        print("-" * 60)
        
        request_body = {"user_id": USER_ID}
        print(f"Request: POST {API_BASE}/api/facebook/get-pages-simple")
        print(f"Body: {json.dumps(request_body, indent=2)}")
        
        try:
            response = await client.post(
                f"{API_BASE}/api/facebook/get-pages-simple",
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get('success'):
                    pages = data.get('pages', [])
                    if pages:
                        print(f"\n✅ Found {len(pages)} pages!")
                        for i, page in enumerate(pages, 1):
                            print(f"   {i}. {page.get('page_name')} (ID: {page.get('page_id')})")
                        
                        # Step 2: Test connect-pages-simple endpoint
                        print("\n📱 STEP 2: Testing connect-pages-simple endpoint")
                        print("-" * 60)
                        
                        # Select first page for testing
                        selected_ids = [pages[0]['page_id']]
                        connect_body = {
                            "user_id": USER_ID,
                            "selected_page_ids": selected_ids
                        }
                        
                        print(f"Request: POST {API_BASE}/api/facebook/connect-pages-simple")
                        print(f"Body: {json.dumps(connect_body, indent=2)}")
                        
                        connect_response = await client.post(
                            f"{API_BASE}/api/facebook/connect-pages-simple",
                            json=connect_body,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        print(f"\nResponse Status: {connect_response.status_code}")
                        if connect_response.status_code == 200:
                            connect_data = connect_response.json()
                            print(f"Response: {json.dumps(connect_data, indent=2)}")
                            
                            if connect_data.get('success'):
                                print("\n✅ Pages connected successfully!")
                            else:
                                print(f"\n❌ Failed to connect: {connect_data.get('message')}")
                        else:
                            print(f"❌ Connect request failed: {connect_response.text}")
                    else:
                        print("\n⚠️ No pages found. Possible reasons:")
                        print("   1. No PIT token stored in database")
                        print("   2. PIT token is expired")
                        print("   3. No Facebook account ID found")
                        print("   4. GHL API returned empty response")
                else:
                    print(f"\n❌ API returned error: {data.get('message')}")
            else:
                print(f"❌ Request failed: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Exception: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_facebook_flow())