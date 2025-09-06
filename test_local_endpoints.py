#!/usr/bin/env python3
"""
Local test for the website screenshot and favicon functions
Tests the actual functions directly without HTTP calls
"""

import asyncio
import os
import sys
sys.path.append('.')

# Import our functions
from Tools.Website.web_scrape import capture_website_screenshot, get_website_favicon_async

async def test_local_functions():
    """Test the functions directly"""
    print("🧪 Testing website functions locally")
    print("="*60)
    
    # Test websites
    test_sites = ["msi.com", "lenovo.com", "google.com"]
    
    for site in test_sites:
        print(f"\n🌐 Testing: {site}")
        print("-" * 40)
        
        # Test screenshot
        print(f"📸 Testing screenshot...")
        try:
            result = await capture_website_screenshot(site, f"test_{site}")
            print(f"Screenshot result: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"✅ Success: {result.get('public_url')}")
            else:
                print(f"❌ Error: {result.get('message')}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        # Test favicon
        print(f"🎨 Testing favicon...")
        try:
            result = await get_website_favicon_async(site, f"test_{site}")
            print(f"Favicon result: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"✅ Success: {result.get('public_url')}")
            else:
                print(f"❌ Error: {result.get('message')}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()

if __name__ == "__main__":
    # Make sure we're not trying to use Heroku paths locally
    if 'DYNO' in os.environ:
        del os.environ['DYNO']
    
    asyncio.run(test_local_functions())