#!/usr/bin/env python3
"""
Test after n8n workflow is fixed
"""

import asyncio
import requests
import json

def test_n8n_fixed():
    """Test if n8n now returns proper response"""
    print("🔧 Testing n8n After Adding 'Respond to Webhook' Node")
    print("=" * 60)
    
    n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    
    payload = {
        "user_id": "test_user_123",
        "user_mssg": "Hello, I need help with social media marketing",
        "session_id": "test_session",
        "agent_name": "socialmediakb"
    }
    
    try:
        print(f"📤 Calling n8n: {n8n_url}")
        print(f"📋 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(n8n_url, json=payload, timeout=15)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Content Length: {len(response.content)} bytes")
        print(f"📝 Raw Content: '{response.text}'")
        
        if response.status_code == 200:
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"\n✅ SUCCESS! n8n returns valid JSON:")
                    print(json.dumps(data, indent=2))
                    
                    # Check required fields
                    required_fields = ['status', 'agent_response']
                    missing = [f for f in required_fields if f not in data]
                    
                    if missing:
                        print(f"\n⚠️ Missing fields: {missing}")
                        print("Add these fields to your 'Respond to Webhook' node")
                    else:
                        print(f"\n🎉 PERFECT! All required fields present")
                        print("Your backend will now work correctly!")
                        
                    return True
                    
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON Error: {e}")
                    print("n8n is returning data but not valid JSON")
                    return False
            else:
                print(f"\n❌ STILL EMPTY: n8n workflow still not returning data")
                print("Make sure you added the 'Respond to Webhook' node")
                return False
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_n8n_fixed()
    
    print(f"\n💡 INSTRUCTIONS:")
    print("1. Go to your n8n workflow")
    print("2. Add 'Respond to Webhook' node at the end")
    print("3. Set response body to JSON with 'status' and 'agent_response' fields")
    print("4. Run this test again to verify the fix")
    print("\nOnce n8n returns proper JSON, your entire system will work! 🚀")