#!/usr/bin/env python3
"""
Debug what n8n is actually returning
"""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_n8n_response():
    """Test what n8n actually returns"""
    
    print("🔍 Testing n8n Response Content")
    print("=" * 40)
    
    n8n_url = os.getenv('N8N_MAIN', 'https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d')
    
    payload = {
        'user_id': 'debug_user',
        'user_mssg': 'Hello, I need help with social media marketing',
        'session_id': 'debug_session',
        'agent_name': 'socialmediakb',
        '_original_message': 'Hello, I need help with social media marketing'
    }
    
    print(f"N8N URL: {n8n_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\n🚀 Calling n8n...")
    
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(n8n_url, json=payload)
            
            print(f"✅ HTTP Status: {response.status_code}")
            print(f"📄 Headers: {dict(response.headers)}")
            print(f"📋 Raw Content: '{response.text}'")
            print(f"📊 Content Length: {len(response.text)}")
            
            if response.text.strip():
                try:
                    json_data = response.json()
                    print(f"✅ Valid JSON: {json.dumps(json_data, indent=2)}")
                except Exception as e:
                    print(f"❌ JSON Parse Error: {e}")
            else:
                print("⚠️ Empty response body!")
                
    except Exception as e:
        print(f"❌ Request Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_n8n_response())