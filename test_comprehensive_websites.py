#!/usr/bin/env python3
"""
Comprehensive test for website screenshot and favicon capture
Tests Big 4, FAANG, Solar companies, and other major websites
Saves results locally to Website_screenshots_favicons folder
"""

import asyncio
import os
import sys
import aiohttp
import requests
from datetime import datetime
import json

sys.path.append('.')

# Import our functions
from Tools.Website.web_scrape import capture_website_screenshot, get_website_favicon_async

# Test website categories
TEST_WEBSITES = {
    "Big 4 Consulting": [
        "deloitte.com",
        "pwc.com", 
        "ey.com",
        "kpmg.com"
    ],
    "FAANG": [
        "facebook.com",
        "amazon.com",
        "apple.com", 
        "netflix.com",
        "google.com"
    ],
    "Solar Panel Companies USA": [
        "sunpower.com",
        "tesla.com",
        "lg.com",
        "panasonic.com",
        "canadiansolar.com",
        "jinkopower.com",
        "firstsolar.com",
        "qcells.com",
        "solaredge.com",
        "enphase.com"
    ],
    "Previous Test Sites": [
        "msi.com",
        "lenovo.com",
        "dell.com",
        "hp.com",
        "asus.com",
        "acer.com",
        "microsoft.com",
        "nvidia.com",
        "amd.com"
    ]
}

# Create output directory
OUTPUT_DIR = "Website_screenshots_favicons"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/screenshots", exist_ok=True) 
os.makedirs(f"{OUTPUT_DIR}/favicons", exist_ok=True)

def download_image_local(url: str, filename: str) -> bool:
    """Download image from URL to local file"""
    try:
        print(f"  📥 Downloading: {filename}")
        response = requests.get(url, timeout=30, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size = os.path.getsize(filename)
            print(f"  ✅ Downloaded: {filename} ({file_size} bytes)")
            return True
        else:
            print(f"  ❌ HTTP {response.status_code} for {filename}")
            return False
    except Exception as e:
        print(f"  ❌ Download failed for {filename}: {e}")
        return False

async def test_website_comprehensive(website: str, category: str) -> dict:
    """Test both screenshot and favicon for a website"""
    print(f"\n🌐 Testing: {website} ({category})")
    print("-" * 60)
    
    results = {
        "website": website,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "screenshot": {"status": "failed", "url": None, "local_file": None, "error": None},
        "favicon": {"status": "failed", "url": None, "local_file": None, "error": None}
    }
    
    # Test Screenshot
    print("📸 Testing screenshot...")
    try:
        screenshot_result = await capture_website_screenshot(
            website, 
            f"test_{website.replace('.', '_')}"
        )
        
        if screenshot_result.get('status') == 'success':
            public_url = screenshot_result.get('public_url')
            if public_url:
                # Download to local file
                local_filename = f"{OUTPUT_DIR}/screenshots/{website.replace('.', '_')}_screenshot.jpg"
                if download_image_local(public_url, local_filename):
                    results["screenshot"] = {
                        "status": "success",
                        "url": public_url,
                        "local_file": local_filename,
                        "error": None
                    }
                    print(f"  ✅ Screenshot captured: {website}")
                else:
                    results["screenshot"]["error"] = "Failed to download locally"
            else:
                results["screenshot"]["error"] = "No public URL returned"
        else:
            error_msg = screenshot_result.get('message', 'Unknown error')
            results["screenshot"]["error"] = error_msg
            print(f"  ❌ Screenshot failed: {error_msg}")
            
    except Exception as e:
        results["screenshot"]["error"] = str(e)
        print(f"  ❌ Screenshot exception: {e}")
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test Favicon
    print("🎨 Testing favicon...")
    try:
        favicon_result = await get_website_favicon_async(
            website,
            f"test_{website.replace('.', '_')}"
        )
        
        if favicon_result.get('status') == 'success':
            public_url = favicon_result.get('public_url')
            if public_url:
                # Download to local file
                local_filename = f"{OUTPUT_DIR}/favicons/{website.replace('.', '_')}_favicon.jpg"
                if download_image_local(public_url, local_filename):
                    results["favicon"] = {
                        "status": "success", 
                        "url": public_url,
                        "local_file": local_filename,
                        "error": None
                    }
                    print(f"  ✅ Favicon captured: {website}")
                else:
                    results["favicon"]["error"] = "Failed to download locally"
            else:
                results["favicon"]["error"] = "No public URL returned"
        else:
            error_msg = favicon_result.get('message', 'Unknown error')
            results["favicon"]["error"] = error_msg
            print(f"  ❌ Favicon failed: {error_msg}")
            
    except Exception as e:
        results["favicon"]["error"] = str(e)
        print(f"  ❌ Favicon exception: {e}")
    
    return results

async def run_comprehensive_test():
    """Run comprehensive test on all website categories"""
    print("🚀 COMPREHENSIVE WEBSITE TESTING")
    print("Testing Big 4, FAANG, Solar Companies, and more...")
    print("="*80)
    
    all_results = []
    summary = {
        "total_websites": 0,
        "screenshots": {"success": 0, "failed": 0},
        "favicons": {"success": 0, "failed": 0},
        "by_category": {}
    }
    
    # Test each category
    for category, websites in TEST_WEBSITES.items():
        print(f"\n🏢 CATEGORY: {category}")
        print("="*50)
        
        category_results = []
        category_summary = {
            "screenshots": {"success": 0, "failed": 0},
            "favicons": {"success": 0, "failed": 0}
        }
        
        for website in websites:
            summary["total_websites"] += 1
            
            # Test the website
            result = await test_website_comprehensive(website, category)
            all_results.append(result)
            category_results.append(result)
            
            # Update counters
            if result["screenshot"]["status"] == "success":
                summary["screenshots"]["success"] += 1
                category_summary["screenshots"]["success"] += 1
            else:
                summary["screenshots"]["failed"] += 1
                category_summary["screenshots"]["failed"] += 1
                
            if result["favicon"]["status"] == "success":
                summary["favicons"]["success"] += 1
                category_summary["favicons"]["success"] += 1
            else:
                summary["favicons"]["failed"] += 1
                category_summary["favicons"]["failed"] += 1
            
            # Delay between websites to be respectful
            await asyncio.sleep(3)
        
        summary["by_category"][category] = category_summary
        
        # Category summary
        total_in_category = len(websites)
        print(f"\n📊 {category} Results:")
        print(f"   📸 Screenshots: {category_summary['screenshots']['success']}/{total_in_category} successful")
        print(f"   🎨 Favicons: {category_summary['favicons']['success']}/{total_in_category} successful")
    
    # Overall summary
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("="*80)
    
    total_tests = summary["total_websites"]
    screenshot_rate = (summary["screenshots"]["success"] / total_tests) * 100
    favicon_rate = (summary["favicons"]["success"] / total_tests) * 100
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total websites tested: {total_tests}")
    print(f"   📸 Screenshots: {summary['screenshots']['success']}/{total_tests} ({screenshot_rate:.1f}% success)")
    print(f"   🎨 Favicons: {summary['favicons']['success']}/{total_tests} ({favicon_rate:.1f}% success)")
    
    print(f"\n📁 CATEGORY BREAKDOWN:")
    for category, stats in summary["by_category"].items():
        category_total = len(TEST_WEBSITES[category])
        cat_screenshot_rate = (stats['screenshots']['success'] / category_total) * 100
        cat_favicon_rate = (stats['favicons']['success'] / category_total) * 100
        print(f"   {category}:")
        print(f"     📸 Screenshots: {stats['screenshots']['success']}/{category_total} ({cat_screenshot_rate:.1f}%)")
        print(f"     🎨 Favicons: {stats['favicons']['success']}/{category_total} ({cat_favicon_rate:.1f}%)")
    
    # Save comprehensive results
    results_data = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "total_websites": total_tests,
            "categories": list(TEST_WEBSITES.keys())
        },
        "summary": summary,
        "detailed_results": all_results
    }
    
    results_file = f"{OUTPUT_DIR}/comprehensive_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n💾 RESULTS SAVED:")
    print(f"   📊 Detailed results: {results_file}")
    print(f"   📸 Screenshots folder: {OUTPUT_DIR}/screenshots/")
    print(f"   🎨 Favicons folder: {OUTPUT_DIR}/favicons/")
    
    # List downloaded files
    screenshot_files = os.listdir(f"{OUTPUT_DIR}/screenshots/")
    favicon_files = os.listdir(f"{OUTPUT_DIR}/favicons/")
    
    print(f"\n📁 FILES DOWNLOADED:")
    print(f"   📸 {len(screenshot_files)} screenshot files")
    print(f"   🎨 {len(favicon_files)} favicon files")
    
    if screenshot_files:
        print(f"\n📸 Screenshot samples:")
        for i, filename in enumerate(screenshot_files[:5]):
            file_size = os.path.getsize(f"{OUTPUT_DIR}/screenshots/{filename}")
            print(f"   • {filename} ({file_size} bytes)")
        if len(screenshot_files) > 5:
            print(f"   ... and {len(screenshot_files) - 5} more")
    
    if favicon_files:
        print(f"\n🎨 Favicon samples:")
        for i, filename in enumerate(favicon_files[:5]):
            file_size = os.path.getsize(f"{OUTPUT_DIR}/favicons/{filename}")
            print(f"   • {filename} ({file_size} bytes)")
        if len(favicon_files) > 5:
            print(f"   ... and {len(favicon_files) - 5} more")
    
    return results_data

if __name__ == "__main__":
    print("🧪 COMPREHENSIVE WEBSITE ENDPOINT TESTER")
    print("Testing major companies across multiple categories")
    print("Results will be saved locally for examination\n")
    
    # Make sure we're not trying to use Heroku paths locally
    if 'DYNO' in os.environ:
        del os.environ['DYNO']
    
    # Run the comprehensive test
    results = asyncio.run(run_comprehensive_test())
    
    # Final success message
    total_success = results["summary"]["screenshots"]["success"] + results["summary"]["favicons"]["success"]
    total_possible = results["summary"]["total_websites"] * 2
    overall_rate = (total_success / total_possible) * 100
    
    print(f"\n🎉 TEST COMPLETE!")
    print(f"Overall success rate: {overall_rate:.1f}%")
    print(f"Check the '{OUTPUT_DIR}' folder to examine all captured images!")