#!/usr/bin/env python3
"""
Test the complete message flow: Frontend → Backend → n8n → Response
"""

import asyncio
import websockets
import json
import time

async def test_websocket_to_n8n():
    """Test WebSocket message that should trigger n8n call"""
    
    print("🚀 Testing Complete Message Flow")
    print("Frontend → Backend WebSocket → n8n → Response")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/test_user_123/test_session_001"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Wait for connection status
            response = await websocket.recv()
            connection_data = json.loads(response)
            print(f"📡 Connection: {connection_data.get('message', 'Connected')}")
            
            # Send a test message that should trigger n8n
            test_message = {
                "message": "I need help with social media marketing for my business website",
                "agent": "socialmediakb",
                "requestId": f"test_{int(time.time())}"
            }
            
            print(f"\n📤 Sending message: '{test_message['message']}'")
            print(f"🤖 Agent: {test_message['agent']}")
            
            await websocket.send(json.dumps(test_message))
            
            print("\n📥 Waiting for responses...")
            
            # Listen for responses
            timeout_count = 0
            max_timeout = 10  # 10 seconds max wait
            
            while timeout_count < max_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    
                    response_type = data.get('type', 'unknown')
                    print(f"📨 Response type: {response_type}")
                    
                    if response_type == 'ack':
                        print("   ✅ Message acknowledged, processing...")
                    elif response_type == 'response':
                        print("   🎉 Got n8n response!")
                        print(f"   Response: {data.get('response', {})}")
                        break
                    elif response_type == 'error':
                        print(f"   ❌ Error: {data.get('error', 'Unknown error')}")
                        break
                    elif response_type == 'ping':
                        # Respond to ping
                        await websocket.send(json.dumps({"type": "pong", "timestamp": int(time.time() * 1000)}))
                        continue
                    else:
                        print(f"   📋 Other response: {data}")
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"   ⏳ Waiting... ({timeout_count}/{max_timeout})")
                    continue
            
            if timeout_count >= max_timeout:
                print("   ⚠️ Timeout waiting for response")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_direct_n8n():
    """Test direct n8n webhook call"""
    print("\n🔗 Testing Direct n8n Webhook Call")
    print("-" * 40)
    
    import aiohttp
    
    n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    
    payload = {
        "user_id": "test_user_123",
        "user_mssg": "I need help with social media marketing",
        "agent": "socialmediakb",
        "session_id": "test_session_001"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(n8n_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ n8n responded: {response.status}")
                    print(f"📄 Data received: {len(str(data))} chars")
                else:
                    print(f"❌ n8n error: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error calling n8n: {e}")

if __name__ == "__main__":
    print("🧪 Complete Integration Test")
    print("Make sure your backend is running on localhost:8000")
    print()
    
    asyncio.run(test_websocket_to_n8n())
    asyncio.run(test_direct_n8n())