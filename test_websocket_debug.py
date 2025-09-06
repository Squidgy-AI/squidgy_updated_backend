#!/usr/bin/env python3
"""
Debug WebSocket n8n integration
"""

import asyncio
import websockets
import json
import time

async def test_with_debug():
    """Test WebSocket with detailed debugging"""
    
    print("🔍 Debug WebSocket → n8n Integration")
    print("=" * 50)
    
    uri = "ws://localhost:8000/ws/debug_user/debug_session"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Receive connection status
            response = await websocket.recv()
            connection_data = json.loads(response)
            print(f"📡 {connection_data.get('message', 'Connected')}")
            
            # Send test message
            test_message = {
                "message": "Hello, I need help with social media marketing",
                "agent": "socialmediakb",
                "requestId": "debug_test_001"
            }
            
            print(f"\n📤 Sending: '{test_message['message']}'")
            await websocket.send(json.dumps(test_message))
            
            # Listen for all responses with detailed logging
            response_count = 0
            max_responses = 5
            
            while response_count < max_responses:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(response)
                    response_count += 1
                    
                    print(f"\n📨 Response #{response_count}:")
                    print(f"   Type: {data.get('type', 'unknown')}")
                    print(f"   Request ID: {data.get('requestId', 'none')}")
                    
                    if data.get('type') == 'response':
                        print("   🎉 N8N RESPONSE RECEIVED!")
                        n8n_data = data.get('response', {})
                        print(f"   Status: {n8n_data.get('status', 'unknown')}")
                        print(f"   Agent: {n8n_data.get('agent_name', 'unknown')}")
                        if n8n_data.get('agent_response'):
                            print(f"   Response: {n8n_data['agent_response'][:100]}...")
                        break
                    elif data.get('type') == 'error':
                        print(f"   ❌ Error: {data.get('error', 'Unknown')}")
                        break
                    elif data.get('type') == 'ack':
                        print("   ✅ Processing started...")
                    elif data.get('type') == 'ping':
                        print("   🏓 Ping received, sending pong...")
                        await websocket.send(json.dumps({"type": "pong", "timestamp": int(time.time() * 1000)}))
                    else:
                        print(f"   📋 Data: {data}")
                        
                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout {response_count}/3")
                    if response_count == 0:
                        print("   ⚠️ No response after sending message")
                    break
                except Exception as e:
                    print(f"   ❌ Error receiving: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_debug())