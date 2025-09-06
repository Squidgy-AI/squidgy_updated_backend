#!/usr/bin/env python3
"""
Test what n8n actually returns
"""

import asyncio
import httpx
import json

async def test_n8n_response():
    """Test what n8n webhook actually returns"""
    
    n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    
    payload = {
        "user_id": "test_user",
        "user_mssg": "Hello, I need help",
        "session_id": "test_session", 
        "agent_name": "socialmediakb"
    }
    
    print("🧪 Testing n8n webhook response format")
    print("=" * 50)
    print(f"URL: {n8n_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(n8n_url, json=payload)
            
            print(f"\n📊 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            print(f"📄 Response Length: {len(response.content)} bytes")
            
            print(f"\n📝 Raw Response Content:")
            print(f"'{response.text}'")
            
            if response.text.strip():
                try:
                    parsed = response.json()
                    print(f"\n✅ Parsed JSON:")
                    print(json.dumps(parsed, indent=2))
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON Parse Error: {e}")
                    print("The n8n webhook is not returning valid JSON!")
            else:
                print(f"\n⚠️ ISSUE FOUND: n8n webhook returns empty response!")
                print("Your n8n workflow needs a 'Respond to Webhook' node")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_n8n_response())