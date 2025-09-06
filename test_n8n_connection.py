#!/usr/bin/env python3
"""
Test n8n connection issue
"""

import requests
import json

def test_different_addresses():
    """Test different localhost addresses"""
    print("🔍 Testing Backend Connection from n8n Perspective")
    print("=" * 60)
    
    addresses = [
        "http://localhost:8000",
        "http://127.0.0.1:8000", 
        "http://0.0.0.0:8000"
    ]
    
    payload = {
        "agent_name": "presaleskb",
        "user_query": "Hi this is Soma test connection",
        "threshold": "0.3"
    }
    
    for addr in addresses:
        url = f"{addr}/n8n/check_agent_match"
        print(f"\n📡 Testing: {url}")
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            print(f"✅ SUCCESS: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {data.get('status', 'unknown')}")
        except requests.exceptions.ConnectRefused:
            print(f"❌ ECONNREFUSED (same error as n8n)")
        except requests.exceptions.ConnectTimeout:
            print(f"❌ TIMEOUT")
        except Exception as e:
            print(f"❌ ERROR: {e}")

def test_uvicorn_host():
    """Check how uvicorn is running"""
    print(f"\n\n🖥️  Backend Host Configuration")
    print("=" * 40)
    print("Current backend responds to:")
    print("✅ http://127.0.0.1:8000/health")
    print("\nFor n8n to connect, your backend should listen on:")
    print("🎯 Host: 0.0.0.0 (all interfaces)")
    print("🎯 Port: 8000")
    print("\nRestart backend with:")
    print("uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    test_different_addresses()
    test_uvicorn_host()
    
    print(f"\n\n🔧 SOLUTION:")
    print("=" * 20)
    print("1. Stop your current backend")
    print("2. Restart with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print("3. Update n8n URLs to use: http://127.0.0.1:8000")
    print("4. Test again")