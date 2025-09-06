#!/usr/bin/env python3
"""
Test the get-pages-simple endpoint to see what data is actually returned
"""

import requests
import json

def test_get_pages_simple():
    """Test the get-pages-simple endpoint"""
    
    print("🔍 TESTING GET-PAGES-SIMPLE ENDPOINT")
    print("=" * 60)
    
    # Your API endpoint
    url = "https://squidgy-back-919bc0659e35.herokuapp.com/api/facebook/get-pages-simple"
    
    # Request data
    data = {
        "user_id": "80b957fc-de1d-4f28-920c-41e0e2e28e5e"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"📡 Calling: {url}")
    print(f"📋 Request: {json.dumps(data, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        print(f"📊 Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            print("📄 FULL RESPONSE:")
            print(json.dumps(result, indent=2))
            print()
            
            if result.get('success') and 'pages' in result:
                pages = result['pages']
                print(f"🎯 PAGES ANALYSIS:")
                print(f"   Total pages: {len(pages)}")
                print()
                
                for i, page in enumerate(pages, 1):
                    print(f"   📄 PAGE {i}:")
                    print(f"      page_id: {page.get('page_id', 'N/A')}")
                    print(f"      page_name: {page.get('page_name', 'N/A')}")
                    print(f"      is_connected: {page.get('is_connected', False)}")
                    print(f"      All keys: {list(page.keys())}")
                    print()
            
            # Check if we're getting real page names or generic ones
            if pages and pages[0].get('page_name') == 'Page 1':
                print("❌ ISSUE FOUND: Getting generic 'Page 1' instead of real Facebook page name!")
                print("   The API should return actual page names like 'Testing Test Business'")
            
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_get_pages_simple()