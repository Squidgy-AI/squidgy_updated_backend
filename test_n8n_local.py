#!/usr/bin/env python3
"""
Test n8n local webhook that uses localhost:8000 backend
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_n8n_local_webhook():
    """Test the local n8n webhook that points to localhost:8000"""
    print("🔧 Testing n8n Local Test Webhook")
    print("=" * 50)
    print("This webhook should already point to localhost:8000")
    print()
    
    # Use local test webhook from .env
    n8n_url = os.getenv("N8N_MAIN", "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d")
    backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    
    print(f"🌐 n8n URL: {n8n_url}")
    print(f"🖥️  Backend URL: {backend_url}")
    print()
    
    payload = {
        "user_id": "local_test_123",
        "user_mssg": "Test message for local n8n workflow",
        "session_id": "local_test_session",
        "agent_name": "presaleskb",
        "timestamp_of_call_made": "2025-06-20T12:00:00.000Z"
    }
    
    try:
        print(f"📤 Calling n8n local test webhook...")
        print(f"📋 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(n8n_url, json=payload, timeout=20)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Content Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"\n🎉 SUCCESS! n8n local webhook returns JSON:")
                    print(json.dumps(data, indent=2))
                    
                    # Check expected fields
                    if 'agent_response' in data:
                        print(f"\n✅ Perfect! Local workflow is working correctly")
                        print("🚀 You can now use this webhook for local testing")
                        return True
                    else:
                        print(f"\n⚠️ Got response but check response format")
                        
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON Parse Error: {e}")
                    print(f"Raw response: '{response.text[:200]}...'")
            else:
                print(f"\n❌ Empty response - webhook might need configuration")
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def test_backend_health():
    """Check if local backend is running"""
    print("\n🏥 Testing Local Backend Health")
    print("=" * 35)
    
    backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    
    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is running at {backend_url}")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Backend error: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend not reachable: {e}")
        print("💡 Make sure to start backend with: uvicorn main:app --reload")
    
    return False

if __name__ == "__main__":
    # Check backend first
    backend_ok = test_backend_health()
    
    if backend_ok:
        # Test n8n local webhook
        webhook_ok = test_n8n_local_webhook()
        
        print(f"\n🎯 LOCAL TEST SUMMARY")
        print("=" * 25)
        print(f"Backend Health: {'✅' if backend_ok else '❌'}")
        print(f"n8n Local Webhook: {'✅' if webhook_ok else '❌'}")
        
        if webhook_ok:
            print("\n🚀 SUCCESS! You can now update your backend to use N8N_LOCAL_TEST")
        else:
            print("\n🔧 Next: Configure the local test webhook in n8n to return responses")
    else:
        print("\n⚠️ Start your backend first: uvicorn main:app --reload")