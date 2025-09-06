#!/usr/bin/env python3
"""
Test script for Facebook Simple API endpoints
Tests the /api/facebook/get-pages-simple endpoint
"""

import httpx
import asyncio
import json
from datetime import datetime

# Configuration
API_URL = "https://squidgy-back-919bc0659e35.herokuapp.com/api/facebook/get-pages-simple"
USER_ID = "8f1b1cea-094d-439a-a575-feaffb7f6faf"

async def test_get_pages_simple():
    """Test the get-pages-simple endpoint"""
    print("=" * 60)
    print("Testing Facebook Simple API - Get Pages")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Endpoint: {API_URL}")
    print(f"User ID: {USER_ID}")
    print("-" * 60)
    
    # Prepare request
    request_body = {
        "user_id": USER_ID
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print("\n📤 Request:")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Body: {json.dumps(request_body, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("\n⏳ Sending request...")
            response = await client.post(API_URL, json=request_body, headers=headers)
            
            print(f"\n📥 Response:")
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            # Parse response
            try:
                response_data = response.json()
                print(f"\n📊 Response Data:")
                print(json.dumps(response_data, indent=2))
                
                # Analyze response
                if response_data.get("success"):
                    pages = response_data.get("pages", [])
                    print(f"\n✅ Success! Found {len(pages)} pages")
                    
                    if pages:
                        print("\n📄 Pages:")
                        for i, page in enumerate(pages, 1):
                            print(f"  {i}. {page.get('page_name', 'Unknown')} (ID: {page.get('page_id', 'unknown')})")
                else:
                    print(f"\n❌ Error: {response_data.get('message', 'Unknown error')}")
                    
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON response: {e}")
                print(f"Raw response: {response.text}")
                
    except httpx.TimeoutException:
        print("\n❌ Request timed out after 30 seconds")
    except Exception as e:
        print(f"\n❌ Request failed: {type(e).__name__}: {e}")

async def main():
    """Run all tests"""
    await test_get_pages_simple()
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())