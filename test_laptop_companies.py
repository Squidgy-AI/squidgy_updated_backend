#!/usr/bin/env python3
"""
Test laptop and computer companies specifically
Including MSI, Lenovo, and all major laptop manufacturers
"""

import asyncio
import os
import sys
import requests
from datetime import datetime
import json

sys.path.append('.')

# Import our functions
from Tools.Website.web_scrape import capture_website_screenshot, get_website_favicon_async

# Laptop and Computer Companies
LAPTOP_COMPANIES = {
    "Premium Gaming Laptops": [
        "msi.com",
        "alienware.com", 
        "razer.com",
        "originpc.com",
        "maingear.com"
    ],
    "Business Laptops": [
        "lenovo.com",
        "dell.com", 
        "hp.com",
        "microsoft.com",  # Surface
        "panasonic.com"   # Toughbook
    ],
    "Consumer Laptops": [
        "asus.com",
        "acer.com",
        "samsung.com",
        "lg.com",
        "huawei.com"
    ],
    "Premium/Apple": [
        "apple.com",
        "microsoft.com"  # Also in business but testing again
    ],
    "Gaming Components": [
        "nvidia.com",
        "amd.com",
        "intel.com",
        "corsair.com",
        "logitech.com"
    ],
    "System Integrators": [
        "cyberpowerpc.com",
        "ibuypower.com",
        "newegg.com",
        "bestbuy.com",
        "microcenter.com"
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
        print(f"  📥 Downloading: {os.path.basename(filename)}")
        response = requests.get(url, timeout=30, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size = os.path.getsize(filename)
            print(f"  ✅ Downloaded: {os.path.basename(filename)} ({file_size:,} bytes)")
            return True
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return False

async def test_laptop_website(website: str, category: str) -> dict:
    """Test both screenshot and favicon for a laptop company website"""
    print(f"\n💻 Testing: {website} ({category})")
    print("-" * 70)
    
    results = {
        "website": website,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "screenshot": {"status": "failed", "url": None, "local_file": None, "error": None, "size_bytes": 0},
        "favicon": {"status": "failed", "url": None, "local_file": None, "error": None, "size_bytes": 0}
    }
    
    # Test Screenshot
    print("📸 Capturing screenshot...")
    try:
        screenshot_result = await capture_website_screenshot(
            website, 
            f"laptop_{website.replace('.', '_')}"
        )
        
        if screenshot_result.get('status') == 'success':
            public_url = screenshot_result.get('public_url')
            if public_url:
                # Download to local file
                local_filename = f"{OUTPUT_DIR}/screenshots/{website.replace('.', '_')}_screenshot.jpg"
                if download_image_local(public_url, local_filename):
                    file_size = os.path.getsize(local_filename)
                    results["screenshot"] = {
                        "status": "success",
                        "url": public_url,
                        "local_file": local_filename,
                        "error": None,
                        "size_bytes": file_size
                    }
                    print(f"  ✅ Screenshot SUCCESS: {website} ({file_size:,} bytes)")
                else:
                    results["screenshot"]["error"] = "Failed to download locally"
            else:
                results["screenshot"]["error"] = "No public URL returned"
        else:
            error_msg = screenshot_result.get('message', 'Unknown error')
            results["screenshot"]["error"] = error_msg
            print(f"  ❌ Screenshot FAILED: {error_msg}")
            
    except Exception as e:
        results["screenshot"]["error"] = str(e)
        print(f"  ❌ Screenshot EXCEPTION: {e}")
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test Favicon
    print("🎨 Capturing favicon...")
    try:
        favicon_result = await get_website_favicon_async(
            website,
            f"laptop_{website.replace('.', '_')}"
        )
        
        if favicon_result.get('status') == 'success':
            public_url = favicon_result.get('public_url')
            if public_url:
                # Download to local file
                local_filename = f"{OUTPUT_DIR}/favicons/{website.replace('.', '_')}_favicon.jpg"
                if download_image_local(public_url, local_filename):
                    file_size = os.path.getsize(local_filename)
                    results["favicon"] = {
                        "status": "success", 
                        "url": public_url,
                        "local_file": local_filename,
                        "error": None,
                        "size_bytes": file_size
                    }
                    print(f"  ✅ Favicon SUCCESS: {website} ({file_size:,} bytes)")
                else:
                    results["favicon"]["error"] = "Failed to download locally"
            else:
                results["favicon"]["error"] = "No public URL returned"
        else:
            error_msg = favicon_result.get('message', 'Unknown error')
            results["favicon"]["error"] = error_msg
            print(f"  ❌ Favicon FAILED: {error_msg}")
            
    except Exception as e:
        results["favicon"]["error"] = str(e)
        print(f"  ❌ Favicon EXCEPTION: {e}")
    
    return results

async def run_laptop_test():
    """Run comprehensive test on all laptop companies"""
    print("💻 LAPTOP & COMPUTER COMPANIES TEST")
    print("Testing MSI, Lenovo, and all major laptop manufacturers...")
    print("="*80)
    
    all_results = []
    summary = {
        "total_websites": 0,
        "screenshots": {"success": 0, "failed": 0, "total_size": 0},
        "favicons": {"success": 0, "failed": 0, "total_size": 0},
        "by_category": {}
    }
    
    # Test each category
    for category, websites in LAPTOP_COMPANIES.items():
        print(f"\n🏷️  CATEGORY: {category}")
        print("="*60)
        
        category_results = []
        category_summary = {
            "screenshots": {"success": 0, "failed": 0, "total_size": 0},
            "favicons": {"success": 0, "failed": 0, "total_size": 0}
        }
        
        for website in websites:
            summary["total_websites"] += 1
            
            # Test the website
            result = await test_laptop_website(website, category)
            all_results.append(result)
            category_results.append(result)
            
            # Update counters
            if result["screenshot"]["status"] == "success":
                summary["screenshots"]["success"] += 1
                category_summary["screenshots"]["success"] += 1
                summary["screenshots"]["total_size"] += result["screenshot"]["size_bytes"]
                category_summary["screenshots"]["total_size"] += result["screenshot"]["size_bytes"]
            else:
                summary["screenshots"]["failed"] += 1
                category_summary["screenshots"]["failed"] += 1
                
            if result["favicon"]["status"] == "success":
                summary["favicons"]["success"] += 1
                category_summary["favicons"]["success"] += 1
                summary["favicons"]["total_size"] += result["favicon"]["size_bytes"]
                category_summary["favicons"]["total_size"] += result["favicon"]["size_bytes"]
            else:
                summary["favicons"]["failed"] += 1
                category_summary["favicons"]["failed"] += 1
            
            # Delay between websites to be respectful
            await asyncio.sleep(3)
        
        summary["by_category"][category] = category_summary
        
        # Category summary
        total_in_category = len(websites)
        screenshot_rate = (category_summary['screenshots']['success'] / total_in_category) * 100
        favicon_rate = (category_summary['favicons']['success'] / total_in_category) * 100
        
        print(f"\n📊 {category} Results:")
        print(f"   📸 Screenshots: {category_summary['screenshots']['success']}/{total_in_category} ({screenshot_rate:.1f}%) - {category_summary['screenshots']['total_size']:,} bytes")
        print(f"   🎨 Favicons: {category_summary['favicons']['success']}/{total_in_category} ({favicon_rate:.1f}%) - {category_summary['favicons']['total_size']:,} bytes")
    
    # Overall summary
    print("\n" + "="*80)
    print("📊 LAPTOP COMPANIES TEST RESULTS")
    print("="*80)
    
    total_tests = summary["total_websites"]
    screenshot_rate = (summary["screenshots"]["success"] / total_tests) * 100
    favicon_rate = (summary["favicons"]["success"] / total_tests) * 100
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total laptop companies tested: {total_tests}")
    print(f"   📸 Screenshots: {summary['screenshots']['success']}/{total_tests} ({screenshot_rate:.1f}% success)")
    print(f"   🎨 Favicons: {summary['favicons']['success']}/{total_tests} ({favicon_rate:.1f}% success)")
    print(f"   📊 Total data captured: {(summary['screenshots']['total_size'] + summary['favicons']['total_size']):,} bytes")
    
    # Highlight specific companies
    print(f"\n🔍 KEY COMPANIES STATUS:")
    key_companies = ['msi.com', 'lenovo.com', 'dell.com', 'hp.com', 'asus.com', 'acer.com']
    for result in all_results:
        if result['website'] in key_companies:
            screenshot_status = "✅" if result['screenshot']['status'] == 'success' else "❌"
            favicon_status = "✅" if result['favicon']['status'] == 'success' else "❌"
            print(f"   {result['website']}: Screenshot {screenshot_status} | Favicon {favicon_status}")
    
    print(f"\n📁 CATEGORY BREAKDOWN:")
    for category, stats in summary["by_category"].items():
        category_total = len(LAPTOP_COMPANIES[category])
        cat_screenshot_rate = (stats['screenshots']['success'] / category_total) * 100
        cat_favicon_rate = (stats['favicons']['success'] / category_total) * 100
        print(f"   {category}:")
        print(f"     📸 Screenshots: {stats['screenshots']['success']}/{category_total} ({cat_screenshot_rate:.1f}%)")
        print(f"     🎨 Favicons: {stats['favicons']['success']}/{category_total} ({cat_favicon_rate:.1f}%)")
    
    # Save results
    results_data = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "test_type": "laptop_companies",
            "total_websites": total_tests,
            "categories": list(LAPTOP_COMPANIES.keys())
        },
        "summary": summary,
        "detailed_results": all_results
    }
    
    results_file = f"{OUTPUT_DIR}/laptop_companies_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n💾 RESULTS SAVED:")
    print(f"   📊 Detailed results: {results_file}")
    print(f"   📸 Screenshots folder: {OUTPUT_DIR}/screenshots/")
    print(f"   🎨 Favicons folder: {OUTPUT_DIR}/favicons/")
    
    # List downloaded files
    screenshot_files = [f for f in os.listdir(f"{OUTPUT_DIR}/screenshots/") if f.endswith('.jpg')]
    favicon_files = [f for f in os.listdir(f"{OUTPUT_DIR}/favicons/") if f.endswith('.jpg')]
    
    print(f"\n📁 NEW FILES DOWNLOADED:")
    print(f"   📸 {len([f for f in screenshot_files if 'laptop_' in f or any(comp.replace('.', '_') in f for comp in [item for sublist in LAPTOP_COMPANIES.values() for item in sublist])])} new screenshot files")
    print(f"   🎨 {len([f for f in favicon_files if 'laptop_' in f or any(comp.replace('.', '_') in f for comp in [item for sublist in LAPTOP_COMPANIES.values() for item in sublist])])} new favicon files")
    
    return results_data

if __name__ == "__main__":
    print("💻 LAPTOP & COMPUTER COMPANIES TESTER")
    print("Specifically testing MSI, Lenovo, and all laptop manufacturers")
    print("Building on previous success with Big 4 and FAANG companies\n")
    
    # Make sure we're not trying to use Heroku paths locally
    if 'DYNO' in os.environ:
        del os.environ['DYNO']
    
    # Run the laptop companies test
    results = asyncio.run(run_laptop_test())
    
    # Final success message
    total_success = results["summary"]["screenshots"]["success"] + results["summary"]["favicons"]["success"]
    total_possible = results["summary"]["total_websites"] * 2
    overall_rate = (total_success / total_possible) * 100
    
    print(f"\n🎉 LAPTOP COMPANIES TEST COMPLETE!")
    print(f"Overall success rate: {overall_rate:.1f}%")
    print(f"Check the '{OUTPUT_DIR}' folder to examine all captured images!")
    print(f"Focus on MSI and Lenovo results to see if the 509 errors are fixed!")