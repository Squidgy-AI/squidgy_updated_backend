#!/usr/bin/env python3
"""
Test script for website screenshot and favicon endpoints
Tests with big websites like msi.com, lenovo.com to verify fixes for 509 errors
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import requests

# Test endpoints
SCREENSHOT_ENDPOINT = "https://squidgy-back-919bc0659e35.herokuapp.com/api/website/screenshot"
FAVICON_ENDPOINT = "https://squidgy-back-919bc0659e35.herokuapp.com/api/website/favicon"

# Test websites that commonly block bots
TEST_WEBSITES = [
    "msi.com",
    "lenovo.com", 
    "dell.com",
    "hp.com",
    "asus.com",
    "acer.com",
    "microsoft.com",
    "apple.com",
    "nvidia.com",
    "amd.com"
]

async def test_screenshot_endpoint(url: str):
    """Test screenshot endpoint"""
    print(f"\n🔍 Testing screenshot for: {url}")
    
    try:
        # Test with GET method
        async with aiohttp.ClientSession() as session:
            params = {"url": url, "session_id": f"test_{int(datetime.now().timestamp())}"}
            async with session.get(SCREENSHOT_ENDPOINT, params=params, timeout=120) as response:
                result = await response.json()
                print(f"📊 Screenshot result: {result.get('status', 'unknown')}")
                
                if result.get('status') == 'success':
                    public_url = result.get('public_url')
                    if public_url:
                        print(f"✅ Screenshot URL: {public_url}")
                        return True, public_url
                    else:
                        print("❌ No public URL returned")
                        return False, None
                else:
                    print(f"❌ Error: {result.get('message', 'Unknown error')}")
                    return False, result.get('message')
                    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False, str(e)

async def test_favicon_endpoint(url: str):
    """Test favicon endpoint"""
    print(f"\n🎨 Testing favicon for: {url}")
    
    try:
        # Test with GET method
        async with aiohttp.ClientSession() as session:
            params = {"url": url, "session_id": f"test_{int(datetime.now().timestamp())}"}
            async with session.get(FAVICON_ENDPOINT, params=params, timeout=60) as response:
                result = await response.json()
                print(f"📊 Favicon result: {result.get('status', 'unknown')}")
                
                if result.get('status') == 'success':
                    public_url = result.get('public_url')
                    if public_url:
                        print(f"✅ Favicon URL: {public_url}")
                        return True, public_url
                    else:
                        print("❌ No public URL returned")
                        return False, None
                else:
                    print(f"❌ Error: {result.get('message', 'Unknown error')}")
                    return False, result.get('message')
                    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False, str(e)

def download_image(url: str, filename: str):
    """Download image to local file for examination"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"💾 Downloaded: {filename}")
            return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
    return False

async def run_comprehensive_test():
    """Run comprehensive test on all websites"""
    print("🚀 Starting comprehensive website endpoint test")
    print("="*80)
    
    results = {
        'screenshots': {'success': 0, 'failed': 0, 'errors': []},
        'favicons': {'success': 0, 'failed': 0, 'errors': []}
    }
    
    # Create local directory for downloads
    os.makedirs('test_downloads', exist_ok=True)
    
    for i, website in enumerate(TEST_WEBSITES):
        print(f"\n🌐 Testing website {i+1}/{len(TEST_WEBSITES)}: {website}")
        print("-" * 60)
        
        # Test screenshot
        screenshot_success, screenshot_result = await test_screenshot_endpoint(website)
        if screenshot_success:
            results['screenshots']['success'] += 1
            # Download screenshot for examination
            if screenshot_result:
                filename = f"test_downloads/{website.replace('.', '_')}_screenshot.jpg"
                download_image(screenshot_result, filename)
        else:
            results['screenshots']['failed'] += 1
            results['screenshots']['errors'].append(f"{website}: {screenshot_result}")
        
        # Small delay between tests
        await asyncio.sleep(2)
        
        # Test favicon
        favicon_success, favicon_result = await test_favicon_endpoint(website)
        if favicon_success:
            results['favicons']['success'] += 1
            # Download favicon for examination
            if favicon_result:
                filename = f"test_downloads/{website.replace('.', '_')}_favicon.jpg"
                download_image(favicon_result, filename)
        else:
            results['favicons']['failed'] += 1
            results['favicons']['errors'].append(f"{website}: {favicon_result}")
        
        # Delay between websites to avoid rate limiting
        await asyncio.sleep(3)
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n📸 SCREENSHOTS:")
    print(f"   ✅ Successful: {results['screenshots']['success']}/{len(TEST_WEBSITES)}")
    print(f"   ❌ Failed: {results['screenshots']['failed']}/{len(TEST_WEBSITES)}")
    
    print(f"\n🎨 FAVICONS:")
    print(f"   ✅ Successful: {results['favicons']['success']}/{len(TEST_WEBSITES)}")
    print(f"   ❌ Failed: {results['favicons']['failed']}/{len(TEST_WEBSITES)}")
    
    # Show errors
    if results['screenshots']['errors']:
        print(f"\n❌ Screenshot errors:")
        for error in results['screenshots']['errors'][:5]:  # Show first 5
            print(f"   • {error}")
    
    if results['favicons']['errors']:
        print(f"\n❌ Favicon errors:")
        for error in results['favicons']['errors'][:5]:  # Show first 5
            print(f"   • {error}")
    
    # Save detailed results
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Detailed results saved to: test_results.json")
    print(f"🖼️  Downloaded images saved to: test_downloads/")
    
    return results

if __name__ == "__main__":
    print("🧪 Website Endpoints Tester")
    print("Testing big websites that commonly block bots")
    print("This will verify the fixes for 509 errors and blank screenshots\n")
    
    # Run the test
    results = asyncio.run(run_comprehensive_test())
    
    # Exit with appropriate code
    total_tests = len(TEST_WEBSITES) * 2
    total_success = results['screenshots']['success'] + results['favicons']['success']
    success_rate = (total_success / total_tests) * 100
    
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 70:
        print("🎉 Test PASSED - Good success rate!")
        exit(0)
    else:
        print("⚠️  Test needs improvement - Low success rate")
        exit(1)