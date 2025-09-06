#!/usr/bin/env python3
"""
Final test to check if WebSocket is actually receiving the error response
"""

import asyncio
import websockets
import json
import time

async def test_websocket_with_longer_wait():
    """Test WebSocket with extended wait time to see error response"""
    
    print("🔍 Final WebSocket Test - Extended Wait")
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
                "requestId": "debug_test_final"
            }
            
            print(f"\n📤 Sending: '{test_message['message']}'")
            await websocket.send(json.dumps(test_message))
            
            # Listen for responses with longer timeout
            response_count = 0
            max_wait_time = 15  # 15 seconds
            start_time = time.time()
            
            while (time.time() - start_time) < max_wait_time:
                try:
                    # Longer timeout per message
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    response_count += 1
                    
                    print(f"\n📨 Response #{response_count}:")
                    print(f"   Type: {data.get('type', 'unknown')}")
                    print(f"   Request ID: {data.get('requestId', 'none')}")
                    
                    if data.get('type') == 'response':
                        print("   🎉 RESPONSE RECEIVED!")
                        response_data = data.get('response', {})
                        print(f"   Status: {response_data.get('status', 'unknown')}")
                        if response_data.get('message'):
                            print(f"   Message: {response_data['message']}")
                        if response_data.get('agent_response'):
                            print(f"   Agent Response: {response_data['agent_response'][:100]}...")
                        return True
                    elif data.get('type') == 'error':
                        print(f"   ❌ Error: {data.get('error', 'Unknown')}")
                        return True
                    elif data.get('type') == 'ack':
                        print("   ✅ Processing started...")
                    elif data.get('type') == 'ping':
                        print("   🏓 Ping received, sending pong...")
                        await websocket.send(json.dumps({"type": "pong", "timestamp": int(time.time() * 1000)}))
                    else:
                        print(f"   📋 Other: {data}")
                        
                except asyncio.TimeoutError:
                    elapsed = time.time() - start_time
                    print(f"   ⏰ Waiting... ({elapsed:.1f}s/{max_wait_time}s)")
                    continue
                except Exception as e:
                    print(f"   ❌ Error receiving: {e}")
                    break
                    
            print(f"\n⚠️ No response received in {max_wait_time} seconds")
            return False
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_with_longer_wait())
    if success:
        print("\n✅ Test completed - Response received")
    else:
        print("\n❌ Test failed - No response received")