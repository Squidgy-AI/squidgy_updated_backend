#!/usr/bin/env python3
"""
Simple test to verify GHL endpoints exist in the backend
"""

import subprocess
import json

# First check if the endpoints are available
print("🔍 Checking available endpoints...")
try:
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8000/openapi.json"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        api_spec = json.loads(result.stdout)
        paths = api_spec.get("paths", {})
        
        ghl_endpoints = [path for path in paths if "ghl" in path]
        
        if ghl_endpoints:
            print("✅ Found GHL endpoints:")
            for endpoint in ghl_endpoints:
                print(f"   • {endpoint}")
        else:
            print("❌ No GHL endpoints found in the API")
            print("\n⚠️  The backend server needs to be restarted with the new code!")
            print("   Please restart the backend server to load the new endpoints.")
    else:
        print("❌ Could not connect to backend")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")

print("\n📝 To test the endpoints after restarting:")
print("   1. Stop the current backend server")
print("   2. Start it again with the updated main.py")
print("   3. Run: python test_ghl_endpoints.py")