"""
Quick verification script to ensure all endpoints work in demo mode
"""

import os
import requests
import json

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

# API Configuration
SOLAR_API_KEY = os.getenv('SOLAR_API_KEY', 'paIpD0y6+aZt7+nFjXBL7EQdtcXTswIF8zDjyUPTmnU=')

def test_endpoint(endpoint_name, url, params):
    """Test a single endpoint"""
    headers = {
        "Authorization": f"Bearer {SOLAR_API_KEY}",
        "Accept": "application/json"
    }
    
    print(f"\nTesting {endpoint_name}...")
    print(f"URL: {url}")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "rwResult" in data:
                print("✅ Success! Response contains rwResult")
                # Show a sample of the response
                if endpoint_name == "Data Layers" and "compositedMarkedRGBURL" in data.get("rwResult", {}):
                    print(f"   Sample image URL: {data['rwResult']['compositedMarkedRGBURL'][:50]}...")
                elif endpoint_name == "Insights" and "summary" in data.get("rwResult", {}):
                    summary = data["rwResult"]["summary"]
                    print(f"   Max panels: {summary.get('maxPossiblePanelCount', 'N/A')}")
                elif endpoint_name == "Report" and "reportURL" in data.get("rwResult", {}):
                    print(f"   Report URL: {data['rwResult']['reportURL'][:50]}...")
            else:
                print("⚠️  Response missing rwResult")
                print(f"   Keys: {list(data.keys())}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Test all endpoints in demo mode"""
    print("=== SOLAR API DEMO MODE VERIFICATION ===")
    print(f"API Key: {SOLAR_API_KEY[:10]}...{SOLAR_API_KEY[-10:]}")
    
    base_url = "https://api.realwave.com/googleSolar"
    test_address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    
    # Test Data Layers
    test_endpoint(
        "Data Layers",
        f"{base_url}/dataLayers",
        {
            "address": test_address,
            "renderPanels": "true",
            "fileFormat": "jpeg",
            "demo": "true"
        }
    )
    
    # Test Insights
    test_endpoint(
        "Insights",
        f"{base_url}/insights",
        {
            "address": test_address,
            "mode": "full",
            "demo": "true"
        }
    )
    
    # Test Report
    test_endpoint(
        "Report",
        f"{base_url}/report",
        {
            "address": test_address,
            "organizationName": "Squidgy Solar",
            "leadName": "Potential Client",
            "demo": "true"
        }
    )
    
    print("\n=== VERIFICATION COMPLETE ===")
    print("\nNote: All requests should use:")
    print('- Authorization: "Bearer YOUR_API_KEY"')
    print('- demo: "true" (as a string, not boolean)')

if __name__ == "__main__":
    # Set API key
    os.environ["SOLAR_API_KEY"] = ""
    
    main()


{
"agent_name": 
"presaleskb",
"selected_agent": 
"presaleskb",
"strategy_used": 
"error_fallback",
"confidence_score": 
0.1,
"error": 
"name 'supabase' is not defined",
"success": 
false
}
]