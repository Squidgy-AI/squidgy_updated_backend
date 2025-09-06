#!/usr/bin/env python3
"""
Test after fixing n8n workflow connections
"""

import requests
import json

def test_n8n_after_fixes():
    """Test n8n after connecting Respond to Webhook node"""
    
    print("🔧 Testing n8n After Workflow Fixes")
    print("=" * 50)
    print("Expected fixes:")
    print("1. ✅ Connected 'Respond to Webhook' node")
    print("2. ✅ Updated backend URLs to localhost:8000")
    print("3. ✅ Enabled disabled nodes")
    print()
    
    # Use main n8n webhook endpoint
    n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    
    payload = {
        "user_id": "test_user_123",
        "user_mssg": "Hello, I need help with social media marketing",
        "session_id": "test_session",
        "agent_name": "presaleskb"  # This should trigger the presales workflow
    }
    
    try:
        print(f"📤 Calling n8n with presales agent...")
        print(f"   URL: {n8n_url}")
        print(f"   Agent: {payload['agent_name']}")
        
        response = requests.post(n8n_url, json=payload, timeout=20)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Content Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"\n🎉 SUCCESS! n8n returns JSON:")
                    print(json.dumps(data, indent=2))
                    
                    # Check if it's the expected response format
                    if 'agent_response' in data:
                        print(f"\n✅ Perfect! Workflow is working correctly")
                        return True
                    else:
                        print(f"\n⚠️ Got response but missing 'agent_response' field")
                        
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON Parse Error: {e}")
                    print(f"Raw response: '{response.text[:200]}...'")
            else:
                print(f"\n❌ Still empty response - workflow not connected properly")
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    success = test_n8n_after_fixes()
    
    print(f"\n🎯 NEXT STEPS:")
    if not success:
        print("1. In n8n, connect 'Execute Pre-Sales Workflow' → 'Respond to Webhook'")
        print("2. Update all backend URLs from Heroku to localhost:8000")
        print("3. Enable disabled nodes in Main Workflow")
        print("4. Test again")
    else:
        print("✅ n8n workflow is working! Now test the full UI → Backend → n8n flow")